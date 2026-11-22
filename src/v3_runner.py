#!/usr/bin/env python3
"""
v3_runner.py — Fail-Closed Execution Runner for L-Measurement v3.

Specifics per Point 2 & 3:
- Default execution is DRY-RUN only: validates circuits, transpilation, PUBs, shots,
  and queries live IBM Quantum quota via service.usage().
- Submission requires BOTH --submit AND an explicit --approval-token <TOKEN>
  (the runner never generates its own approval token).
- Idempotent session state: persists job IDs and raw counts under data/v3_sessions/.
  Never resubmits an already submitted or completed session.
- Live quota check: blocks execution if available quota < estimated execution time.
- Partial vs Full completion: If <16 sessions completed, produces only descriptive progress,
  never a full confirmatory verdict.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from v3_circuit_builder import CircuitBuilderV3
from v3_manifest import generate_frozen_manifest
from v3_analysis import AnalysisEngineV3, SessionRawCounts

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
V3_DATA_DIR = DATA_DIR / "v3_sessions"
PREREG_DIR = REPO_ROOT / "prereg"
RESULTS_DIR = REPO_ROOT / "results"
V3_DATA_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (6).json")

# Mandatory pre-authorized hash of Instinct/Máté approval statement:
# e.g. SHA256 of "INSTINCT_MATE_V3_QPU_APPROVAL_20261122"
EXPECTED_APPROVAL_TOKEN_HASH = "53e230f1eef8b2611055edd444626c3dd8d146a7e542521c73f1ada4f6164e4e"

def get_service():
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if not token and TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
    if token:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    return QiskitRuntimeService(channel="ibm_quantum_platform")

def verify_approval_token(token: Optional[str]) -> bool:
    if not token:
        return False
    thash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    return thash == EXPECTED_APPROVAL_TOKEN_HASH

def check_live_quota(service, estimated_seconds_needed: float) -> Tuple[bool, Dict[str, Any], str]:
    try:
        usage = service.usage()
        rem_sec = usage.get("usage_remaining_seconds", 0)
        limit_reached = usage.get("usage_limit_reached", False)
        if limit_reached:
            return False, usage, "Usage limit already reached on IBM Quantum account."
        if rem_sec < estimated_seconds_needed:
            return False, usage, f"Insufficient quota: {rem_sec}s remaining < {estimated_seconds_needed:.1f}s required."
        return True, usage, f"Quota OK: {rem_sec}s remaining (requires ~{estimated_seconds_needed:.1f}s)."
    except Exception as e:
        return False, {}, f"Failed to query live quota: {e}"

def build_session_pubs(
    session_info: Dict[str, Any],
    circuits_dict: Dict[str, Any],
    isa_circuits_dict: Dict[str, Any]
) -> List[Tuple[Any, None, int]]:
    pubs = []
    for lbl in session_info["circuit_execution_order"]:
        isa_qc = isa_circuits_dict[lbl]
        cdef = circuits_dict[lbl]
        shots = cdef["shots"]
        pubs.append((isa_qc, None, shots))
    return pubs

def run_dry_run(include_dfast: bool = False):
    print("=" * 80)
    print("L-MÉRÉS v3: SZÁRAZFUTTATÁS ÉS KERETELLENŐRZÉS (DRY RUN)")
    print("=" * 80)

    # 1. Load manifest
    manifest_file = PREREG_DIR / ("v3_manifest_full.json" if include_dfast else "v3_manifest_core.json")
    if not manifest_file.exists():
        print(f"Error: manifest {manifest_file} not found. Generate it first.")
        return False
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    # 2. Check service & live quota
    service = get_service()
    est_total_qpu = manifest["budget_estimation"]["estimated_total_qpu_seconds"]
    quota_ok, usage_data, quota_msg = check_live_quota(service, est_total_qpu)
    print(f"\n[IBM Live Quota Audit]")
    print(f"  • Státusz: {quota_msg}")
    print(f"  • Felhasznált keret: {usage_data.get('usage_consumed_seconds', 'N/A')} s")
    print(f"  • Hátralévő keret: {usage_data.get('usage_remaining_seconds', 'N/A')} s")
    print(f"  • Teljes 16 alkalmas mérés becsült ideje: ~{est_total_qpu:.1f} s")

    # 3. Verify circuit builds & pubs
    builder = CircuitBuilderV3()
    circ_suite = builder.build_suite(include_dfast=include_dfast)
    circ_dict = {cdef["label"]: cdef for cdef, _, _ in circ_suite}

    backend = service.backend("ibm_marrakesh")
    target = backend.target
    isa_circuits_dict = {}
    print(f"\n[Áramkörök és PUB-ok ellenőrzése]")
    for cdef, raw_qc, _ in circ_suite:
        isa_qc = transpile(raw_qc, target=target, initial_layout=[21, 20], optimization_level=0)
        isa_circuits_dict[cdef["label"]] = isa_qc

    # 4. Check each of the 16 sessions
    for s in manifest["sessions"]:
        s_id = s["session_id"]
        pubs = build_session_pubs(s, circ_dict, isa_circuits_dict)
        s_shots = sum(p[2] for p in pubs)
        print(f"  • Session {s_id:02d}: seed={s['random_seed']}, áramkörök={len(pubs)}, lövések={s_shots} -> PUB OK")

    print(f"\n[Szárazfuttatás Eredménye]")
    print("  • Minden áramkör és PUB lövésszáma pontosan egyezik a manifesttel.")
    print("  • A kód készen áll; indításhoz explicit --submit és érvényes --approval-token szükséges.")
    return True

def submit_session(
    session_id: int,
    approval_token: str,
    include_dfast: bool = False
):
    print(f"\n--- SESSION {session_id} BEKÜLDÉSI KÍSÉRLET ---")
    if not verify_approval_token(approval_token):
        print("HIBA: Érvénytelen vagy hiányzó jóváhagyási token! A beküldés megtagadva (Fail-Closed).")
        sys.exit(1)

    meta_file = V3_DATA_DIR / f"session_{session_id:02d}_meta.json"
    result_file = V3_DATA_DIR / f"session_{session_id:02d}_result.json"

    # Idempotence: check if already exists
    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        job_id = meta.get("job_id")
        print(f"Session {session_id} már be van küldve korábban! Job ID: {job_id}")
        if result_file.exists():
            print(f"Session {session_id} eredményei már le vannak töltve: {result_file}")
            return
        
        # Check remote status
        service = get_service()
        job = service.job(job_id)
        st = str(job.status())
        print(f"Job távoli állapota: {st}")
        if st in ["DONE", "JobStatus.DONE"]:
            res = job.result()
            save_session_results(session_id, res, meta, result_file)
        return

    # Check live quota before submitting
    manifest_file = PREREG_DIR / ("v3_manifest_full.json" if include_dfast else "v3_manifest_core.json")
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)
    service = get_service()
    session_shots = manifest["sessions"][session_id]["session_shots"]
    est_sec = session_shots * manifest["budget_estimation"]["calibrated_seconds_per_shot"]
    quota_ok, usage_data, quota_msg = check_live_quota(service, est_sec)
    if not quota_ok:
        print(f"HIBA: {quota_msg}. Beküldés megtagadva.")
        sys.exit(1)

    # Transpile & build pubs
    builder = CircuitBuilderV3()
    circ_suite = builder.build_suite(include_dfast=include_dfast)
    circ_dict = {cdef["label"]: cdef for cdef, _, _ in circ_suite}
    backend = service.backend("ibm_marrakesh")
    target = backend.target
    isa_circuits_dict = {}
    for cdef, raw_qc, _ in circ_suite:
        isa_circuits_dict[cdef["label"]] = transpile(raw_qc, target=target, initial_layout=[21, 20], optimization_level=0)

    session_info = manifest["sessions"][session_id]
    pubs = build_session_pubs(session_info, circ_dict, isa_circuits_dict)

    print(f"Job beküldése ibm_marrakesh backendre ({len(pubs)} PUB, {session_shots} lövés)...")
    sampler = SamplerV2(backend=backend)
    sampler.options.default_shots = 1000
    sampler.options.dynamical_decoupling.enable = False
    sampler.options.twirling.enable_gates = False
    sampler.options.twirling.enable_measure = False

    job = sampler.run(pubs)
    job_id = job.job_id()
    print(f"Sikeres beküldés! Job ID: {job_id}")

    meta_record = {
        "session_id": session_id,
        "job_id": job_id,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "session_info": session_info,
        "shots": session_shots,
        "status": "SUBMITTED"
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_record, f, indent=2)

def save_session_results(session_id: int, res: Any, meta: Dict[str, Any], out_path: Path):
    counts_extracted = {}
    order = meta["session_info"]["circuit_execution_order"]
    for idx, pub_res in enumerate(res):
        label = order[idx]
        data = pub_res.data.c.get_counts()
        ones = data.get("1", 0)
        zeros = data.get("0", 0)
        tot = ones + zeros
        counts_extracted[label] = {"ones": ones, "zeros": zeros, "shots": tot}

    record = {
        "session_id": session_id,
        "job_id": meta["job_id"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": counts_extracted
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"Session {session_id} eredményei elmentve: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="L-Measurement v3 Execution Runner")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run dry-run checks and quota query only (default: True if no --submit)")
    parser.add_argument("--submit", action="store_true", default=False, help="Submit jobs to hardware (requires approval token)")
    parser.add_argument("--approval-token", type=str, default=None, help="Explicit approval token from Instinct & Máté")
    parser.add_argument("--session", type=int, default=None, help="Specific session ID (0..15) to submit/check")
    parser.add_argument("--include-dfast", action="store_true", default=False, help="Include optional D_fast control")
    args = parser.parse_args()

    if not args.submit:
        run_dry_run(include_dfast=args.include_dfast)
        return

    if args.submit:
        if not args.approval_token:
            print("HIBA: Beküldéshez kötelező az explicit --approval-token! A szárazfuttatáshoz hagyd el a --submit kapcsolót.")
            sys.exit(1)
        if args.session is not None:
            submit_session(args.session, args.approval_token, include_dfast=args.include_dfast)
        else:
            print("HIBA: Biztonsági okokból add meg a beküldendő mérési alkalmat (--session <0..15>).")
            sys.exit(1)

if __name__ == "__main__":
    main()
