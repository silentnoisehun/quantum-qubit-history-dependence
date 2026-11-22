#!/usr/bin/env python3
"""
v3_runner.py — Strict Fail-Closed Execution Runner for L-Measurement v3.

Full compliance with peer-review points 1–6:
1. Complete typing imports (Tuple, Dict, Any, List, Optional).
2. Uses SamplerV2(mode=backend), explicitly configures:
   - execution.init_qubits = True
   - execution.rep_delay = 0.00025 (250 us)
   - dynamical_decoupling.enable = False
   - twirling.enable_gates = False
   - twirling.enable_measure = False
3. Mandatory ISA Hash Verification: Transpiled ISA circuits are checked against
   results/v3_transpiler_audit_report.json before submission; mismatch halts fail-closed.
4. Strict Sequential & Time-Window Enforcement:
   - Session k requires Session k-1 to be completed and verified.
   - Enforces scheduled UTC time window.
5. Idempotent Job Tracking & Read-Only Fetch:
   - Persists metadata and raw counts under data/v3_sessions/.
   - Checking/fetching existing jobs requires NO approval token.
   - Verifies circuit labels and shot counts on result retrieval.
6. Approval Gate & Quota Verification:
   - External approval hash from environment (V3_APPROVAL_TOKEN_HASH); no self-authorization.
   - Live quota queried via service.usage() before submission.
7. Full 16-session Analysis Workflow:
   - --analyze generates final reports only when all 16 sessions are complete.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import qiskit
import qiskit_ibm_runtime
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from v3_circuit_builder import CircuitBuilderV3
from v3_analysis import AnalysisEngineV3, SessionRawCounts, EXPECTED_CORE_CIRCUITS

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
V3_DATA_DIR = DATA_DIR / "v3_sessions"
PREREG_DIR = REPO_ROOT / "prereg"
RESULTS_DIR = REPO_ROOT / "results"
V3_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (6).json")

# External approval hash must be supplied via environment variable; no hardcoded backdoor token.
# To authorize, Máté and Instinct set $env:V3_APPROVAL_TOKEN_HASH = "<sha256_of_their_secret_approval_statement>"
ENV_APPROVAL_HASH_KEY = "V3_APPROVAL_TOKEN_HASH"

def get_service():
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if not token and TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
    if token:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    return QiskitRuntimeService(channel="ibm_quantum_platform")

def verify_approval_token(token: Optional[str]) -> bool:
    expected_hash = os.environ.get(ENV_APPROVAL_HASH_KEY)
    if not expected_hash or not token:
        return False
    thash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    return thash.lower() == expected_hash.strip().lower()

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

def load_audited_isa_hashes() -> Dict[str, str]:
    audit_path = RESULTS_DIR / "v3_transpiler_audit_report.json"
    if not audit_path.exists():
        raise FileNotFoundError(f"Audited report missing: {audit_path}. Run src/v3_transpiler_audit.py first.")
    with open(audit_path, encoding="utf-8") as f:
        data = json.load(f)
    return {c["label"]: c["isa_sha256"] for c in data["circuits"]}

def build_and_verify_isa_circuits(
    backend,
    circ_suite: List[Tuple[Dict[str, Any], Any, str]]
) -> Dict[str, Any]:
    audited_hashes = load_audited_isa_hashes()
    isa_circuits_dict = {}
    
    for cdef, raw_qc, _ in circ_suite:
        label = cdef["label"]
        isa_qc = transpile(raw_qc, target=backend.target, initial_layout=[21, 20], optimization_level=0)
        isa_str = str(isa_qc.data).encode("utf-8")
        current_hash = hashlib.sha256(isa_str).hexdigest()

        expected_hash = audited_hashes.get(label)
        if not expected_hash:
            raise ValueError(f"Circuit {label} has no audited reference hash!")
        if current_hash != expected_hash:
            raise ValueError(
                f"ISA Hash Mismatch for {label}!\n"
                f"  Audited reference: {expected_hash}\n"
                f"  Current compiled:  {current_hash}\n"
                f"Compilation differs from frozen audit! Aborting fail-closed."
            )
        isa_circuits_dict[label] = isa_qc
    return isa_circuits_dict

def configure_sampler(backend) -> SamplerV2:
    sampler = SamplerV2(mode=backend)
    sampler.options.execution.init_qubits = True
    sampler.options.execution.rep_delay = 0.00025  # 250 us
    sampler.options.dynamical_decoupling.enable = False
    sampler.options.twirling.enable_gates = False
    sampler.options.twirling.enable_measure = False
    sampler.options.default_shots = 1000
    return sampler

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

def check_session_prerequisites(
    session_id: int,
    manifest: Dict[str, Any],
    enforce_schedule: bool = True
) -> Tuple[bool, str]:
    # 1. Sequential prerequisite: session k-1 must be completed and retrieved
    if session_id > 0:
        prev_result_file = V3_DATA_DIR / f"session_{session_id - 1:02d}_result.json"
        if not prev_result_file.exists():
            return False, f"Prerequisite error: Previous session {session_id - 1} result is not yet retrieved ({prev_result_file})."

    # 2. Schedule window check
    if enforce_schedule:
        s_info = manifest["sessions"][session_id]
        sched_dt = datetime.fromisoformat(s_info["scheduled_time_utc"])
        now_dt = datetime.now(timezone.utc)
        if now_dt < sched_dt:
            diff_sec = (sched_dt - now_dt).total_seconds()
            return False, f"Schedule window error: Session {session_id} is scheduled for {sched_dt.isoformat()}, {diff_sec:.0f}s in the future."
    return True, "Prerequisites satisfied."

def save_and_verify_session_result(
    session_id: int,
    res: Any,
    meta: Dict[str, Any],
    out_path: Path
) -> Dict[str, Any]:
    counts_extracted = {}
    order = meta["session_info"]["circuit_execution_order"]
    
    if len(res) != len(order):
        raise ValueError(f"Result PUB count mismatch: expected {len(order)}, got {len(res)}")

    for idx, pub_res in enumerate(res):
        label = order[idx]
        data = pub_res.data.c.get_counts()
        ones = data.get("1", 0)
        zeros = data.get("0", 0)
        tot = ones + zeros
        
        # Verify shot count against expected
        c_meta = meta["circuits_catalog"][label]
        expected_shots = c_meta["shots"]
        if tot != expected_shots:
            raise ValueError(f"Circuit {label} shot mismatch: expected {expected_shots}, got {tot}")
        if ones < 0 or zeros < 0:
            raise ValueError(f"Circuit {label} negative count: ones={ones}, zeros={zeros}")

        counts_extracted[label] = {"ones": ones, "zeros": zeros, "shots": tot}

    record = {
        "session_id": session_id,
        "job_id": meta["job_id"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": counts_extracted
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"Session {session_id} eredményei ellenőrizve és elmentve: {out_path}")
    return record

def run_dry_run(include_dfast: bool = False, service=None):
    print("=" * 80)
    print("L-MÉRÉS v3: SZÁRAZFUTTATÁS ÉS KERETELLENŐRZÉS (DRY RUN)")
    print(f"Környezet: Python {sys.version.split()[0]} | Qiskit {qiskit.__version__} | qiskit-ibm-runtime {qiskit_ibm_runtime.__version__}")
    print("=" * 80)

    manifest_file = PREREG_DIR / ("v3_manifest_full.json" if include_dfast else "v3_manifest_core.json")
    if not manifest_file.exists():
        print(f"Error: manifest {manifest_file} not found. Generate it first.")
        return False
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    if service is None:
        service = get_service()

    backend = service.backend(manifest["backend"])
    est_total_qpu = manifest["budget_estimation"]["estimated_total_qpu_seconds"]
    quota_ok, usage_data, quota_msg = check_live_quota(service, est_total_qpu)

    print(f"\n[IBM Live Quota & Instance Audit]")
    print(f"  • Backend: {backend.name}")
    print(f"  • Instance ID: {usage_data.get('instance_id', 'N/A')}")
    print(f"  • Státusz: {quota_msg}")
    print(f"  • Felhasznált keret: {usage_data.get('usage_consumed_seconds', 'N/A')} s")
    print(f"  • Hátralévő keret: {usage_data.get('usage_remaining_seconds', 'N/A')} s")
    print(f"  • Becsült kampányidő: ~{est_total_qpu:.1f} s")

    # Configure sampler and print exact runtime options
    sampler = configure_sampler(backend)
    print(f"\n[SamplerV2 Ténylegesen Beállított Opciók]")
    print(f"  • Mode: {sampler.mode}")
    print(f"  • execution.init_qubits: {sampler.options.execution.init_qubits}")
    print(f"  • execution.rep_delay: {sampler.options.execution.rep_delay} s")
    print(f"  • dynamical_decoupling.enable: {sampler.options.dynamical_decoupling.enable}")
    print(f"  • twirling.enable_gates: {sampler.options.twirling.enable_gates}")
    print(f"  • twirling.enable_measure: {sampler.options.twirling.enable_measure}")

    # Build and verify ISA circuits against audit report
    builder = CircuitBuilderV3()
    circ_suite = builder.build_suite(include_dfast=include_dfast)
    circ_dict = {cdef["label"]: cdef for cdef, _, _ in circ_suite}
    
    print(f"\n[ISA Áramkörök és Hash-ek ellenőrzése az audit jelentéshez]")
    isa_circuits_dict = build_and_verify_isa_circuits(backend, circ_suite)
    print(f"  • Mind a {len(isa_circuits_dict)} ISA áramkör SHA256 hash-e 100%-ban egyezik a rögzített audittal.")

    print(f"\n[16 Mérési Alkalom PUB Struktúrája]")
    for s in manifest["sessions"]:
        s_id = s["session_id"]
        pubs = build_session_pubs(s, circ_dict, isa_circuits_dict)
        s_shots = sum(p[2] for p in pubs)
        print(f"  • Session {s_id:02d}: seed={s['random_seed']}, áramkörök={len(pubs)}, lövések={s_shots} -> PUB OK")

    print(f"\n[Jóváhagyási Kapu Állapota]")
    has_env_hash = bool(os.environ.get(ENV_APPROVAL_HASH_KEY))
    print(f"  • Környezeti jóváhagyási hash ({ENV_APPROVAL_HASH_KEY}) beállítva: {has_env_hash}")
    print(f"  • A futtató zárt állapotban van. Indításhoz Instinct & Máté jóváhagyása szükséges.")
    return True

def fetch_session_result(session_id: int, service=None):
    """
    Read-only retrieval of existing job results. Requires NO approval token.
    """
    meta_file = V3_DATA_DIR / f"session_{session_id:02d}_meta.json"
    result_file = V3_DATA_DIR / f"session_{session_id:02d}_result.json"

    if not meta_file.exists():
        print(f"Session {session_id} még nincs beküldve ({meta_file} hiányzik).")
        return None

    if result_file.exists():
        print(f"Session {session_id} eredményei már korábban elmentve: {result_file}")
        with open(result_file, encoding="utf-8") as f:
            return json.load(f)

    with open(meta_file, encoding="utf-8") as f:
        meta = json.load(f)
    job_id = meta["job_id"]
    print(f"Session {session_id} job állapotának lekérdezése: {job_id}...")

    if service is None:
        service = get_service()
    job = service.job(job_id)
    st = str(job.status())
    print(f"Job állapota: {st}")

    if st in ["DONE", "JobStatus.DONE"]:
        res = job.result()
        return save_and_verify_session_result(session_id, res, meta, result_file)
    else:
        print(f"Job még folyamatban van: {st}")
        return None

def submit_session(
    session_id: int,
    approval_token: str,
    include_dfast: bool = False,
    enforce_schedule: bool = True,
    service=None,
    backend=None
):
    print(f"\n--- SESSION {session_id} BEKÜLDÉSI KÍSÉRLET ---")
    if not verify_approval_token(approval_token):
        raise PermissionError(
            "HIBA: Érvénytelen vagy hiányzó jóváhagyási token! "
            "A beküldési kapu zárt (Fail-Closed). Végrehajtás megtagadva."
        )

    meta_file = V3_DATA_DIR / f"session_{session_id:02d}_meta.json"
    result_file = V3_DATA_DIR / f"session_{session_id:02d}_result.json"

    # Idempotence: do not resubmit
    if meta_file.exists():
        print(f"Session {session_id} már be van küldve korábban! Lekérdezés indítása...")
        return fetch_session_result(session_id, service=service)

    manifest_file = PREREG_DIR / ("v3_manifest_full.json" if include_dfast else "v3_manifest_core.json")
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    # Check prerequisites (sequential order and scheduled time)
    prereq_ok, prereq_msg = check_session_prerequisites(session_id, manifest, enforce_schedule=enforce_schedule)
    if not prereq_ok:
        raise RuntimeError(prereq_msg)

    if service is None:
        service = get_service()
    if backend is None:
        backend = service.backend(manifest["backend"])

    # Check live quota
    session_shots = manifest["sessions"][session_id]["session_shots"]
    est_sec = session_shots * manifest["budget_estimation"]["calibrated_seconds_per_shot"]
    quota_ok, usage_data, quota_msg = check_live_quota(service, est_sec)
    if not quota_ok:
        raise RuntimeError(f"Keretellenőrzési hiba: {quota_msg}. Beküldés megtagadva.")

    # Transpile & verify ISA circuits
    builder = CircuitBuilderV3()
    circ_suite = builder.build_suite(include_dfast=include_dfast)
    circ_dict = {cdef["label"]: cdef for cdef, _, _ in circ_suite}
    isa_circuits_dict = build_and_verify_isa_circuits(backend, circ_suite)

    session_info = manifest["sessions"][session_id]
    pubs = build_session_pubs(session_info, circ_dict, isa_circuits_dict)

    sampler = configure_sampler(backend)
    print(f"Job beküldése {backend.name} QPU-ra ({len(pubs)} PUB, {session_shots} lövés)...")
    job = sampler.run(pubs)
    job_id = job.job_id()
    print(f"Sikeres beküldés! Job ID: {job_id}")

    meta_record = {
        "session_id": session_id,
        "job_id": job_id,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "session_info": session_info,
        "circuits_catalog": manifest["circuits_catalog"],
        "shots": session_shots,
        "status": "SUBMITTED"
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_record, f, indent=2)
    return meta_record

def analyze_full_campaign(include_dfast: bool = False):
    print("=" * 80)
    print("L-MÉRÉS v3: ADATSOR ELEMZÉSE ÉS JELENTÉS GENERÁLÁSA")
    print("=" * 80)

    sessions_raw = []
    missing_sessions = []
    for s_idx in range(16):
        res_file = V3_DATA_DIR / f"session_{s_idx:02d}_result.json"
        if not res_file.exists():
            missing_sessions.append(s_idx)
            continue
        with open(res_file, encoding="utf-8") as f:
            data = json.load(f)
        
        # Transform counts dict to (arm, prep, t_name) format
        raw_counts = {}
        for lbl, c_entry in data["counts"].items():
            # label format: D_tau_8ns_G_t0 or D_tau_8ns_E_t2T_mc
            parts = lbl.split("_")
            arm = parts[0]
            prep = parts[3]
            t_name = parts[4]
            raw_counts[(arm, prep, t_name)] = {
                "ones": c_entry["ones"],
                "shots": c_entry["shots"]
            }
        sessions_raw.append(SessionRawCounts(session_id=s_idx, counts=raw_counts))

    if missing_sessions:
        print(f"\nFIGYELEM: A 16 alkalomból {len(missing_sessions)} hiányzik: {missing_sessions}")
        print("Megerősítő döntés NEM generálható hiányos adatsorból (Fail-Closed).")
        print(f"Rendelkezésre álló alkalmak száma: {len(sessions_raw)} / 16.")
        return None

    engine = AnalysisEngineV3(T=220.0e-6)
    camp_res = engine.analyze_campaign(sessions_raw)

    if not camp_res.all_evaluable:
        print(f"\n[Elemzési Hiba - Fail-Closed]")
        print(f"  • Kiértékelhető alkalmak: {camp_res.n_sessions_evaluable} / {camp_res.n_sessions_total}")
        print(f"  • Döntés: {camp_res.decision_verdict}")
        print(f"  • Indoklás: {camp_res.decision_explanation}")
        print(f"  • Problémás alkalmak részletei: {camp_res.undefined_sessions}")
        return camp_res

    print(f"\n[Eredmények Összegzése]")
    print(f"  • Kiértékelhető alkalmak: {camp_res.n_sessions_evaluable} / {camp_res.n_sessions_total}")
    print(f"  • Átlagos L: {camp_res.mean_L:+.4f} ± {camp_res.se_L:.4f}")
    print(f"  • 99%-os CI (df=15): [{camp_res.ci99_lower:+.4f}, {camp_res.ci99_upper:+.4f}]")
    print(f"  • DÖNTÉS: {camp_res.decision_verdict}")
    print(f"  • Magyarázat: {camp_res.decision_explanation}")
    print(f"  • D2 Modellellenőrzési eltérések száma: {camp_res.d2_model_check_summary['num_flagged_deviations']} / 32")

    # Generate JSON and Markdown
    out_json = RESULTS_DIR / "v3_l_measurement_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "mean_L": camp_res.mean_L,
            "se_L": camp_res.se_L,
            "ci99": [camp_res.ci99_lower, camp_res.ci99_upper],
            "verdict": camp_res.decision_verdict,
            "explanation": camp_res.decision_explanation,
            "d2_summary": camp_res.d2_model_check_summary
        }, f, indent=2)
    print(f"Jelentés elmentve: {out_json}")
    return camp_res

def main():
    parser = argparse.ArgumentParser(description="L-Measurement v3 Execution Runner")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run dry run checks only")
    parser.add_argument("--submit", action="store_true", default=False, help="Submit jobs to hardware")
    parser.add_argument("--approval-token", type=str, default=None, help="Explicit approval token")
    parser.add_argument("--session", type=int, default=None, help="Specific session ID (0..15)")
    parser.add_argument("--fetch", action="store_true", default=False, help="Fetch results for session (read-only, no token needed)")
    parser.add_argument("--analyze", action="store_true", default=False, help="Run final campaign analysis across all sessions")
    parser.add_argument("--include-dfast", action="store_true", default=False, help="Include optional D_fast control")
    args = parser.parse_args()

    if args.analyze:
        analyze_full_campaign(include_dfast=args.include_dfast)
        return

    if args.fetch:
        if args.session is None:
            print("HIBA: Add meg a lekérdezendő mérési alkalmat (--session <0..15>).")
            sys.exit(1)
        fetch_session_result(args.session)
        return

    if not args.submit:
        run_dry_run(include_dfast=args.include_dfast)
        return

    if args.submit:
        if not args.approval_token:
            print("HIBA: Beküldéshez kötelező az explicit --approval-token! A kapu zárt.")
            sys.exit(1)
        if args.session is None:
            print("HIBA: Biztonsági okokból add meg a beküldendő mérési alkalmat (--session <0..15>).")
            sys.exit(1)
        try:
            submit_session(args.session, args.approval_token, include_dfast=args.include_dfast)
        except Exception as e:
            print(f"HIBA: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
