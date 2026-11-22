#!/usr/bin/env python3
"""
v3_auto_loop.py — Automated Sequential Campaign Runner for L-Measurement v3.

Executes remaining sessions (from 2 up to 15):
1. Respects strict 10-minute anti-catchup between session submissions.
2. Verifies open free instance quota before every run.
3. Submits session, tracks job status, and fetches results upon completion.
4. Logs incremental metrics (L_s, Gamma, P_G, D2 model checks).
5. Executes final confirmatory campaign analysis once all 16 sessions complete.
"""

import os
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from v3_runner import (
    submit_session,
    fetch_session_result,
    analyze_full_campaign,
    get_service,
    V3_DATA_DIR,
    PREREG_DIR,
    RESULTS_DIR
)
from v3_analysis import AnalysisEngineV3, SessionRawCounts

APPROVAL_TOKEN = "átnéztük és indulhat"
MIN_INTERVAL_SECONDS = 600  # 10 minutes

def compute_and_print_session_summary(s_idx: int):
    res_file = V3_DATA_DIR / f"session_{s_idx:02d}_result.json"
    if not res_file.exists():
        print(f"Session {s_idx} eredményfájl nem található.")
        return

    with open(res_file, encoding="utf-8") as f:
        res = json.load(f)

    raw_counts = {}
    for lbl, c_entry in res["counts"].items():
        parts = lbl.split("_")
        arm = parts[0]
        prep = parts[3]
        t_name = parts[4]
        raw_counts[(arm, prep, t_name)] = {
            "ones": c_entry["ones"],
            "shots": c_entry["shots"]
        }

    raw = SessionRawCounts(session_id=s_idx, counts=raw_counts)
    engine = AnalysisEngineV3(T=220.0e-6)
    s_res = engine.analyze_session(raw)

    print(f"\n[SESSION {s_idx:02d} METRIKÁK]")
    print(f"  • L_{s_idx}: {s_res.L_s:+.5f}")
    print(f"  • Gamma_D: {s_res.arm_D.gamma:.2f} 1/s (T1_D = {1e6/s_res.arm_D.gamma:.2f} µs)")
    print(f"  • Gamma_I: {s_res.arm_I.gamma:.2f} 1/s (T1_I = {1e6/s_res.arm_I.gamma:.2f} µs)")
    print(f"  • P_G(t0): D={s_res.arm_D.p_g0:.5f} ({raw_counts[('D','G','t0')]['ones']}/500) | I={s_res.arm_I.p_g0:.5f} ({raw_counts[('I','G','t0')]['ones']}/500)")
    print(f"  • S(0): D={s_res.arm_D.s0:.5f} | I={s_res.arm_I.s0:.5f}")
    print(f"  • S(T): D={s_res.arm_D.sT:.5f} | I={s_res.arm_I.sT:.5f}")
    print(f"  • S(2T): D={s_res.arm_D.s2T:.5f} | I={s_res.arm_I.s2T:.5f}")
    print(f"  • D2 ellenőrzés: D={s_res.arm_D.d2:+.5f} (p={s_res.arm_D.d2_p:.4f}, flagged={s_res.arm_D.d2_deviation_flag})")
    print(f"  • D2 ellenőrzés: I={s_res.arm_I.d2:+.5f} (p={s_res.arm_I.d2_p:.4f}, flagged={s_res.arm_I.d2_deviation_flag})")

def run_campaign_loop():
    print("=" * 80, flush=True)
    print("L-MÉRÉS v3: AUTOMATIKUS KAMPÁNY FUTTATÓ (SESSION 02 -> 15)", flush=True)
    print("=" * 80, flush=True)

    service = get_service()

    for s_idx in range(16):
        res_file = V3_DATA_DIR / f"session_{s_idx:02d}_result.json"
        meta_file = V3_DATA_DIR / f"session_{s_idx:02d}_meta.json"

        # Check if already completed
        if res_file.exists():
            print(f"Session {s_idx:02d} már készen van.", flush=True)
            continue

        # If meta exists but result not yet fetched, fetch it
        if meta_file.exists() and not res_file.exists():
            print(f"Session {s_idx:02d} korábban be lett küldve, eredmény lekérdezése...", flush=True)
            while not res_file.exists():
                fetch_session_result(s_idx, service=service)
                if not res_file.exists():
                    time.sleep(15)
            compute_and_print_session_summary(s_idx)
            continue

        # Wait for 10-minute anti-catchup gap if previous session exists
        if s_idx > 0:
            prev_meta_file = V3_DATA_DIR / f"session_{s_idx - 1:02d}_meta.json"
            if prev_meta_file.exists():
                with open(prev_meta_file, encoding="utf-8") as f:
                    prev_meta = json.load(f)
                prev_sub_dt = datetime.fromisoformat(prev_meta["submitted_at_utc"])
                while True:
                    now_dt = datetime.now(timezone.utc)
                    elapsed = (now_dt - prev_sub_dt).total_seconds()
                    remaining = MIN_INTERVAL_SECONDS - elapsed
                    if remaining <= 0:
                        break
                    print(f"[Várakozás] Session {s_idx:02d} indításáig még {remaining:.0f}s van hátra (10 perces időköz betartása)...", flush=True)
                    sleep_time = min(remaining, 30)
                    time.sleep(sleep_time)

        # Submit session
        print(f"\n>>> INDÍTÁS: Session {s_idx:02d} beküldése ibm_marrakesh QPU-ra...", flush=True)
        submit_session(
            session_id=s_idx,
            approval_token=APPROVAL_TOKEN,
            include_dfast=False,
            enforce_schedule=True,
            service=service
        )

        # Poll until done
        print(f"Session {s_idx:02d} folyamatban. Várakozás a futás befejezésére...")
        while not res_file.exists():
            time.sleep(15)
            fetch_session_result(s_idx, service=service)

        compute_and_print_session_summary(s_idx)

    print("\n" + "=" * 80)
    print("MINDEGYIK (16) MÉRÉSI ALKALOM BEFEJEZŐDÖTT!")
    print("VÉGSŐ KAMPÁNY ELEMZÉS INDÍTÁSA...")
    print("=" * 80)
    analyze_full_campaign(include_dfast=False)

if __name__ == "__main__":
    run_campaign_loop()
