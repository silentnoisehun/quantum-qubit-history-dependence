#!/usr/bin/env python3
"""
confirmatory_runner.py — Strict Fail-Closed Runner for Confirmatory Campaign
Implements Section 8, 10, 11, and 14:
- Verifies code and manifest hashes against FROZEN_SPEC.json
- Verifies all transpiled circuits match frozen manifest
- Manages block-level submission (default: 8 blocks x 2500 shots)
- Commits each block submission metadata immediately BEFORE downloading results
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
TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (2) (1).json")

def normalize_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")

def verify_frozen_hashes():
    frozen_spec_path = PREREG_DIR / "FROZEN_SPEC.json"
    if not frozen_spec_path.exists():
        raise RuntimeError("FROZEN_SPEC.json missing!")

    with open(frozen_spec_path, "rb") as f:
        spec = json.loads(normalize_bytes(f.read()).decode("utf-8"))

    for name, data in spec["files"].items():
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

def run_confirmatory(num_blocks: int = 8, shots_per_circ: int = 2500, dry_run: bool = True):
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
        t_decay=220.0e-6  # Calibrated from pilot T1
    )

    builder = CircuitBuilder(q_primary=q_primary, q_spectator=q_spectator, timing=timing)
    campaign_suite = builder.generate_full_circuit_suite()
    campaign_circuits = [c[1] for c in campaign_suite]
    campaign_meta = [c[2] for c in campaign_suite]

    print(f"Prepared {len(campaign_circuits)} campaign circuits per block.")

    service = get_service()
    backend = service.backend("ibm_marrakesh")
    print(f"Connected to backend: {backend.name}")

    print("Transpiling with optimization_level=0...")
    isa_circuits = transpile(
        campaign_circuits,
        target=backend.target,
        initial_layout=[q_primary, q_spectator],
        optimization_level=0
    )

    # Gate Guard 2: Verify against frozen manifest
    print("Gate Guard 2: Comparing compiled circuits against manifest...")
    for idx, isa_qc in enumerate(isa_circuits):
        qasm_repr = isa_qc.qasm() if hasattr(isa_qc, "qasm") else str(isa_qc.data)
        circuit_hash = hashlib.sha256(qasm_repr.encode("utf-8")).hexdigest()
        expected_hash = manifest_entries[idx]["circuit_sha256"]
        if circuit_hash != expected_hash:
            raise RuntimeError(f"Circuit mismatch at index {idx} ({isa_qc.name})!\nExpected: {expected_hash}\nActual:   {circuit_hash}")
    print("Gate Guard 2: All campaign circuits strictly match frozen manifest.")

    options = SamplerOptions()
    options.default_shots = shots_per_circ
    options.execution.init_qubits = True
    options.execution.rep_delay = 0.00025  # 250 us
    options.dynamical_decoupling.enable = False
    options.twirling.enable_gates = False
    options.twirling.enable_measure = False

    sampler = SamplerV2(mode=backend, options=options)

    if dry_run:
        print("\n[DRY RUN COMPLETED] All guards passed.")
        print(f"Configuration: {num_blocks} blocks x {shots_per_circ} shots per circuit.")
        print("To submit live, run with --submit.")
        return

    submitted_jobs = []
    print(f"\nEXECUTING CONFIRMATORY CAMPAIGN: Submitting {num_blocks} blocks...")

    for b in range(num_blocks):
        print(f"\n--- Submitting Block {b+1}/{num_blocks} ---")
        job = sampler.run(isa_circuits)
        job_id = job.job_id()
        sub_time = datetime.now(timezone.utc).isoformat()
        print(f"Block {b+1} SUBMITTED! Job ID: {job_id}")

        record = {
            "block_index": b,
            "job_id": job_id,
            "submission_time_utc": sub_time,
            "backend": backend.name,
            "shots_per_circuit": shots_per_circ,
            "total_circuits": len(isa_circuits),
            "primary_qubit": q_primary,
            "spectator_qubit": q_spectator,
            "manifest_sha256": manifest_doc["manifest_sha256"],
            "circuit_metadata": campaign_meta,
            "status": "SUBMITTED"
        }

        out_file = DATA_DIR / f"confirmatory_block_{b}_{job_id}.json"
        with open(out_file, "wb") as f:
            f.write(json.dumps(record, sort_keys=True, indent=2).replace("\r\n", "\n").encode("utf-8"))

        # Commit record immediately
        try:
            subprocess.run(["git", "add", str(out_file)], cwd=str(REPO_ROOT), check=True)
            subprocess.run(["git", "commit", "-m", f"record(confirmatory): block {b+1}/{num_blocks} submission {job_id}"], cwd=str(REPO_ROOT), check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=True)
            print(f"Block {b+1} submission record committed and pushed.")
        except Exception as e:
            raise RuntimeError(f"CRITICAL: Failed to commit block {b+1} record to git: {e}")

        submitted_jobs.append((b, job_id))

    print(f"\nALL {num_blocks} BLOCKS SUBMITTED SUCCESSFULLY!")
    for b, jid in submitted_jobs:
        print(f"  Block {b}: {jid}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Confirmatory Campaign Submission")
    parser.add_argument("--blocks", type=int, default=8, help="Number of blocks (default: 8)")
    parser.add_argument("--shots", type=int, default=2500, help="Shots per circuit (default: 2500)")
    parser.add_argument("--submit", action="store_true", help="Submit live jobs to QPU")
    args = parser.parse_args()
    run_confirmatory(num_blocks=args.blocks, shots_per_circ=args.shots, dry_run=not args.submit)
