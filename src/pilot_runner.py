#!/usr/bin/env python3
"""
pilot_runner.py — Strict Fail-Closed QPU Submission for Pilot Job
Enforces Gate guards:
1. Verifies code and manifest hashes match FROZEN_SPEC.json before connecting.
2. Transpiles with optimization_level=0 and initial_layout=[21, 20].
3. Compares all 52 transpiled circuits against the frozen manifest (fail-closed abort on mismatch).
4. Explicitly configures init_qubits=True and rep_delay=250 us via SamplerExecutionOptions.
5. Explicitly disables dynamical decoupling and twirling.
6. Records and saves job submission metadata BEFORE downloading results.
7. Works cross-platform (Linux & Windows) with POSIX path resolution.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.options import SamplerOptions

from circuit_builder import CircuitBuilder, TimingSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PREREG_DIR = REPO_ROOT / "prereg"
TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (1) (1).json")

def normalize_bytes(data: bytes) -> bytes:
    # Normalize CRLF to LF for deterministic hashing across OSes
    return data.replace(b"\r\n", b"\n")

def verify_frozen_hashes():
    frozen_spec_path = PREREG_DIR / "FROZEN_SPEC.json"
    if not frozen_spec_path.exists():
        raise RuntimeError("FROZEN_SPEC.json missing! Run generate_prereg_hashes.py first.")

    with open(frozen_spec_path, "rb") as f:
        spec = json.loads(normalize_bytes(f.read()).decode("utf-8"))

    for name, data in spec["files"].items():
        # Posix path normalization
        rel_path = Path(data["path"].replace("\\", "/"))
        p = REPO_ROOT / rel_path
        if not p.exists():
            raise FileNotFoundError(f"Missing file specified in FROZEN_SPEC: {rel_path}")

        with open(p, "rb") as f:
            file_bytes = normalize_bytes(f.read())
            actual_hash = hashlib.sha256(file_bytes).hexdigest()

        if actual_hash != data["sha256"]:
            raise RuntimeError(f"Hash mismatch on {name}!\nExpected: {data['sha256']}\nActual:   {actual_hash}")

    print("Gate Guard 1: All frozen code and manifest hashes verified bit-identical.")

def get_service():
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if not token and TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
    if token:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    return QiskitRuntimeService(channel="ibm_quantum_platform")

def run_pilot(dry_run: bool = True):
    verify_frozen_hashes()

    snapshot_path = DATA_DIR / "target_snapshot_ibm_marrakesh.json"
    with open(snapshot_path, encoding="utf-8") as f:
        snapshot = json.load(f)

    manifest_path = PREREG_DIR / "manifest_audit.json"
    with open(manifest_path, "rb") as f:
        manifest_doc = json.loads(normalize_bytes(f.read()).decode("utf-8"))
    manifest_entries = manifest_doc["manifest"]

    q_primary = snapshot["selected_q_primary"]["index"]
    q_spectator = snapshot["selected_q_spectator"]["index"]
    dt = snapshot["dt_seconds"]

    timing = TimingSpec(
        dt=dt,
        t_x=snapshot["selected_q_primary"]["x_duration_seconds"] or 36e-9,
        t_c=16.128e-6,
        n_pulses=64,
        tau_max=64.0e-6,
        tau_0=8e-9,
        t_decay=168.0e-6
    )

    builder = CircuitBuilder(q_primary=q_primary, q_spectator=q_spectator, timing=timing)
    campaign_suite = builder.generate_full_circuit_suite()
    pilot_t1 = builder.generate_pilot_t1_curve()
    full_suite = campaign_suite + pilot_t1
    all_circuits = [c[1] for c in full_suite]
    circuit_metadata = [c[2] for c in full_suite]

    print(f"Prepared {len(all_circuits)} circuits (44 campaign + 8 pilot T1).")

    service = get_service()
    backend = service.backend("ibm_marrakesh")
    print(f"Connected to live backend: {backend.name}")

    print("Transpiling with optimization_level=0...")
    isa_circuits = transpile(
        all_circuits,
        target=backend.target,
        initial_layout=[q_primary, q_spectator],
        optimization_level=0
    )

    # Gate Guard 2: Compare each transpiled circuit hash against the frozen manifest
    print("Gate Guard 2: Comparing compiled circuits against manifest...")
    for idx, isa_qc in enumerate(isa_circuits):
        qasm_repr = isa_qc.qasm() if hasattr(isa_qc, "qasm") else str(isa_qc.data)
        circuit_hash = hashlib.sha256(qasm_repr.encode("utf-8")).hexdigest()
        expected_hash = manifest_entries[idx]["circuit_sha256"]
        if circuit_hash != expected_hash:
            raise RuntimeError(f"Circuit mismatch at index {idx} ({isa_qc.name})!\nExpected: {expected_hash}\nActual:   {circuit_hash}")
    print("Gate Guard 2: All 52 circuits strictly match frozen manifest.")

    # Sampler options configuration
    options = SamplerOptions()
    options.default_shots = 1000
    options.execution.init_qubits = True
    options.execution.rep_delay = 0.00025  # 250 us fixed rep_delay
    options.dynamical_decoupling.enable = False
    options.twirling.enable_gates = False
    options.twirling.enable_measure = False

    print("Execution Options Verified:")
    print(f"  default_shots: {options.default_shots}")
    print(f"  init_qubits:   {options.execution.init_qubits}")
    print(f"  rep_delay:     {options.execution.rep_delay} s")
    print(f"  DD enabled:    {options.dynamical_decoupling.enable}")
    print(f"  Twirling:      {options.twirling.enable_gates}")

    sampler = SamplerV2(mode=backend, options=options)

    if dry_run:
        print("\n[DRY RUN COMPLETED] All guards passed. No job was submitted to QPU.")
        print("To submit live, run with --submit after explicit approval.")
        return

    print("\nSUBMITTING LIVE PILOT JOB TO QPU...")
    job = sampler.run(isa_circuits)
    job_id = job.job_id()
    submission_time = datetime.now(timezone.utc).isoformat()
    print(f"JOB SUBMITTED! Job ID: {job_id}")

    record = {
        "job_id": job_id,
        "submission_time_utc": submission_time,
        "backend": backend.name,
        "shots_per_circuit": 1000,
        "total_circuits": len(isa_circuits),
        "primary_qubit": q_primary,
        "spectator_qubit": q_spectator,
        "manifest_sha256": manifest_doc["manifest_sha256"],
        "circuit_metadata": circuit_metadata,
        "status": "SUBMITTED"
    }

    out_file = DATA_DIR / f"pilot_job_{job_id}.json"
    with open(out_file, "wb") as f:
        f.write(json.dumps(record, sort_keys=True, indent=2).replace("\r\n", "\n").encode("utf-8"))

    print(f"Submission record written to: {out_file}")

    # Immediate git commit BEFORE downloading results (LOUD FAIL IF IT FAILS)
    try:
        subprocess.run(["git", "add", str(out_file)], cwd=str(REPO_ROOT), check=True)
        subprocess.run(["git", "commit", "-m", f"record(pilot): job submission {job_id} on {backend.name}"], cwd=str(REPO_ROOT), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=True)
        print("Git commit and push of submission metadata succeeded.")
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Failed to commit/push submission record to git: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pilot Job Submission")
    parser.add_argument("--submit", action="store_true", help="Submit live job to QPU")
    args = parser.parse_args()
    run_pilot(dry_run=not args.submit)
