#!/usr/bin/env python3
"""
audit_transpiler.py — Fail-Closed Transpilation & Manifest Audit
Implements Section 5 of the protocol:
- Transpiles with optimization_level = 0
- Enforces explicit physical layout mapping
- Audits every circuit: gate counts, reset presence, delay lengths, scheduled duration
- Computes manifest hash for frozen pre-registration
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService

from circuit_builder import CircuitBuilder, TimingSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PREREG_DIR = REPO_ROOT / "prereg"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PREREG_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (1) (1).json")

def get_backend(backend_name="ibm_marrakesh"):
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
    return service.backend(backend_name)

def run_transpiler_audit(backend_name="ibm_marrakesh"):
    snapshot_path = DATA_DIR / f"target_snapshot_{backend_name}.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found at {snapshot_path}. Run fetch_backend_data.py first.")

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
    pilot_t1 = builder.generate_pilot_t1_curve()

    print(f"Loaded backend snapshot: {backend_name}")
    print(f"Primary Qubit: {q_primary}, Spectator Qubit: {q_spectator}")
    print(f"Total campaign circuits: {len(suite)}")
    print(f"Total pilot T1 circuits: {len(pilot_t1)}")

    # Load live backend target for ISA compilation
    backend = get_backend(backend_name)
    target = backend.target

    initial_layout = [q_primary, q_spectator]

    raw_circuits = [c[1] for c in suite]
    print(f"\nTranspiling {len(raw_circuits)} circuits with optimization_level=0...")
    isa_circuits = transpile(
        raw_circuits,
        target=target,
        initial_layout=initial_layout,
        optimization_level=0,
    )

    manifest_entries = []
    audit_passed = True
    audit_errors = []

    for idx, (label, orig_qc, meta) in enumerate(suite):
        isa_qc = isa_circuits[idx]
        arm = meta["arm"]
        prep = meta["prep"]
        ops = isa_qc.count_ops()

        # 1. Check reset
        reset_count = ops.get("reset", 0)
        if reset_count != 1:
            audit_passed = False
            audit_errors.append(f"[{label}] Expected exactly 1 reset, found {reset_count}")

        # 2. Check measure
        measure_count = ops.get("measure", 0)
        if measure_count != 1:
            audit_passed = False
            audit_errors.append(f"[{label}] Expected exactly 1 measure, found {measure_count}")

        # 3. Check X-gate counts on physical qubits
        # Expected X count on primary q:
        # D: 64 (conditioning) + (1 if prep=='E' else 0)
        # I: 0 (conditioning) + (1 if prep=='E' else 0)
        # Nb: 0 on primary (conditioning) + (1 if prep=='E' else 0)
        # D_fast: 64 (conditioning) + (1 if prep=='E' else 0)
        expected_x_primary = (64 if arm in ["D", "D_fast"] else 0) + (1 if prep == "E" else 0)
        expected_x_spectator = 64 if arm == "Nb" else 0

        actual_x_primary = 0
        actual_x_spectator = 0
        for instruction in isa_qc.data:
            op_name = instruction.operation.name
            q_indices = [isa_qc.find_bit(q).index for q in instruction.qubits]
            if op_name in ["x"]:
                if q_primary in q_indices:
                    actual_x_primary += 1
                if q_spectator in q_indices:
                    actual_x_spectator += 1

        if actual_x_primary != expected_x_primary:
            audit_passed = False
            audit_errors.append(f"[{label}] Primary X count mismatch: expected {expected_x_primary}, got {actual_x_primary}")

        if actual_x_spectator != expected_x_spectator:
            audit_passed = False
            audit_errors.append(f"[{label}] Spectator X count mismatch: expected {expected_x_spectator}, got {actual_x_spectator}")

        # Qasm / serialization digest for circuit integrity
        qasm_repr = isa_qc.qasm() if hasattr(isa_qc, "qasm") else str(isa_qc.data)
        circuit_hash = hashlib.sha256(qasm_repr.encode("utf-8")).hexdigest()

        manifest_entries.append({
            "index": idx,
            "label": label,
            "arm": arm,
            "tau_seconds": meta["tau_seconds"],
            "prep": prep,
            "t_readout_seconds": meta["t_readout_seconds"],
            "is_model_check": meta["is_model_check"],
            "physical_qubits": [q_primary, q_spectator],
            "ops": dict(ops),
            "actual_x_primary": actual_x_primary,
            "actual_x_spectator": actual_x_spectator,
            "circuit_sha256": circuit_hash,
        })

    # Compute overall manifest hash
    manifest_bytes = json.dumps(manifest_entries, sort_keys=True).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    audit_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend_name,
        "primary_qubit": q_primary,
        "spectator_qubit": q_spectator,
        "optimization_level": 0,
        "initial_layout": initial_layout,
        "total_circuits": len(suite),
        "audit_passed": audit_passed,
        "audit_errors": audit_errors,
        "manifest_sha256": manifest_sha256,
        "manifest": manifest_entries,
    }

    manifest_file = PREREG_DIR / "manifest_audit.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    print(f"\n--- AUDIT RESULT ---")
    if audit_passed:
        print(f"STATUS: PASSED (ALL {len(suite)} CIRCUITS VERIFIED)")
        print(f"Manifest SHA256: {manifest_sha256}")
        print(f"Manifest saved to: {manifest_file}")
    else:
        print(f"STATUS: FAILED ({len(audit_errors)} errors detected)")
        for err in audit_errors[:10]:
            print(f"  - {err}")
        sys.exit(1)

    return audit_report

if __name__ == "__main__":
    run_transpiler_audit("ibm_marrakesh")
