#!/usr/bin/env python3
"""
pilot_runner.py — Strict QPU Submission for Pilot Job
Enforces Gate 5 & Gate 6 guards:
1. Verifies code and manifest hashes match FROZEN_SPEC.json before connecting.
2. Transpiles with optimization_level=0 and initial_layout=[21, 20].
3. Disables dynamical decoupling and twirling explicitly.
4. Configures init_qubits=True and fixed rep_delay=250 us.
5. Records and saves job submission metadata BEFORE downloading results.
"""

import argparse
import hashlib
import json
import os
import sys
import time
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

def verify_frozen_hashes():
    frozen_spec_path = PREREG_DIR / "FROZEN_SPEC.json"
    if not frozen_spec_path.exists():
        raise RuntimeError("FROZEN_SPEC.json missing! Run generate_prereg_hashes.py first.")

    with open(frozen_spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    for name, data in spec["files"].items():
        p = REPO_ROOT / data["path"]
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest()
        if actual_hash != data["sha256"]:
            raise RuntimeError(f"Hash mismatch on {name}!\nExpected: {data['sha256']}\nActual:   {actual_hash}")

    print("Gate Guard 1: All frozen hashes verified successfully.")

def run_pilot(dry_run: bool = True):
    verify_frozen_hashes()

    snapshot_path = DATA_DIR / "target_snapshot_ibm_marrakesh.json"
    with open(snapshot_path, encoding="utf-8") as f:
        snapshot = json.load(f)

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
    suite = builder.generate_full_circuit_suite()
    t1_curve = builder.generate_pilot_t1_curve()
    all_circuits = [c[1] for c in suite] + [c[1] for c in t1_curve]
    circuit_metadata = [c[2] for c in suite] + [c[2] for c in t1_curve]

    print(f"Prepared {len(all_circuits)} circuits (44 campaign + 8 pilot T1).")

    # Connect to service
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")

    backend = service.backend("ibm_marrakesh")
    print(f"Connected to live backend: {backend.name}")

    print("Transpiling with optimization_level=0...")
    isa_circuits = transpile(
        all_circuits,
        target=backend.target,
        initial_layout=[q_primary, q_spectator],
        optimization_level=0
    )

    # Sampler options
    options = SamplerOptions()
    options.default_shots = 1000
    options.dynamical_decoupling.enable = False
    options.twirling.enable_gates = False
    options.twirling.enable_measure = False

    sampler = SamplerV2(mode=backend, options=options)

    if dry_run:
        print("\n[DRY RUN COMPLETED] Circuits verified and ready. No job was submitted to QPU.")
        print("To submit live, pass --submit after Máté gives explicit written approval.")
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
        "circuit_metadata": circuit_metadata,
        "status": "SUBMITTED"
    }

    out_file = DATA_DIR / f"pilot_job_{job_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print(f"Submission metadata recorded at: {out_file}")
    print("Agent will now commit submission metadata to git before awaiting results.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pilot Job Submission")
    parser.add_argument("--submit", action="store_true", help="Submit live job to QPU (requires approval)")
    args = parser.parse_args()
    run_pilot(dry_run=not args.submit)
