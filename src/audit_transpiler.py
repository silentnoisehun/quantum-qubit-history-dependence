#!/usr/bin/env python3
"""
audit_transpiler.py — Fail-Closed Transpilation & Scheduled Timing Audit
Implements Section 5 of the protocol:
- Transpiles with optimization_level = 0
- Enforces explicit physical layout mapping [21, 20]
- Audits scheduled timing via ASAPScheduleAnalysis:
  * Reset start dt MUST be exactly 20032 dt (80.128 us) across all 44 campaign circuits
  * Last conditioning gate to reset delay is strictly tau (27 dt + tau/dt for arm D)
  * Pre-reset delay strictly equals meta['tau_seconds']
  * All 8 pilot T1 circuits audited
- Verifies fail-closed detection with an intentional corruption check
- Computes canonical manifest hash for frozen pre-registration
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ASAPScheduleAnalysis
from qiskit_ibm_runtime import QiskitRuntimeService

from circuit_builder import CircuitBuilder, TimingSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PREREG_DIR = REPO_ROOT / "prereg"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PREREG_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (1) (1).json")

def get_backend(backend_name="ibm_marrakesh"):
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if not token and TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
    if token:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
    return service.backend(backend_name)

def audit_single_circuit(isa_qc, meta, durations, q_primary, q_spectator, dt):
    """
    Audits a single ISA circuit for gate counts, physical layout, and scheduled timing.
    """
    ops = dict(isa_qc.count_ops())
    arm = meta["arm"]
    prep = meta["prep"]
    is_t1 = meta.get("type") == "t1_calibration"
    tau = meta.get("tau_seconds", 0.0)
    label = isa_qc.name

    errors = []

    # 1. Reset and measure counts
    if ops.get("reset", 0) != 1:
        errors.append(f"[{label}] Expected 1 reset, found {ops.get('reset', 0)}")
    if ops.get("measure", 0) != 1:
        errors.append(f"[{label}] Expected 1 measure, found {ops.get('measure', 0)}")

    # 2. X gate counts on physical qubits
    if is_t1:
        expected_x_primary = 1
        expected_x_spectator = 0
    else:
        expected_x_primary = (64 if arm in ["D", "D_fast"] else 0) + (1 if prep == "E" else 0)
        expected_x_spectator = 64 if arm == "Nb" else 0

    actual_x_primary = 0
    actual_x_spectator = 0
    for instruction in isa_qc.data:
        op_name = instruction.operation.name
        q_indices = [isa_qc.find_bit(q).index for q in instruction.qubits]
        if op_name == "x":
            if q_primary in q_indices:
                actual_x_primary += 1
            if q_spectator in q_indices:
                actual_x_spectator += 1

    if actual_x_primary != expected_x_primary:
        errors.append(f"[{label}] Primary X mismatch: expected {expected_x_primary}, got {actual_x_primary}")
    if actual_x_spectator != expected_x_spectator:
        errors.append(f"[{label}] Spectator X mismatch: expected {expected_x_spectator}, got {actual_x_spectator}")

    # 3. Scheduled timing analysis
    pm = PassManager([ASAPScheduleAnalysis(durations)])
    pm.run(isa_qc)
    node_starts = pm.property_set.get("node_start_time", {})

    reset_node = None
    reset_start_dt = None
    measure_start_dt = None
    for node, start_dt in node_starts.items():
        if node.name == "reset":
            reset_node = node
            reset_start_dt = start_dt
        elif node.name == "measure":
            measure_start_dt = start_dt

    if reset_start_dt is None:
        errors.append(f"[{label}] Reset node missing in scheduled analysis")

    if not is_t1:
        # Pre-reset duration must be EXACTLY 20032 dt (80.128 us)
        expected_reset_dt = 20032
        if reset_start_dt != expected_reset_dt:
            errors.append(f"[{label}] Reset start timing mismatch! Expected {expected_reset_dt} dt (80.128 us), got {reset_start_dt} dt ({reset_start_dt*dt*1e6:.3f} us)")

        # For arm D: gap between last conditioning X and reset
        if arm == "D":
            x_nodes = [n for n in node_starts if n.name == "x" and node_starts[n] < reset_start_dt]
            if not x_nodes:
                errors.append(f"[{label}] No conditioning X nodes found before reset in arm D")
            else:
                last_x = max(x_nodes, key=lambda n: node_starts[n])
                x_dur_dt = 9  # 36 ns / 4 ns
                gap_dt = reset_start_dt - (node_starts[last_x] + x_dur_dt)
                expected_gap_dt = 27 + round(tau / dt)  # 27 dt half-slot delay + tau
                if gap_dt != expected_gap_dt:
                    errors.append(f"[{label}] Conditioning-to-reset gap mismatch! Expected {expected_gap_dt} dt ({expected_gap_dt*dt*1e6:.3f} us), got {gap_dt} dt ({gap_dt*dt*1e6:.3f} us)")

    return {
        "label": label,
        "arm": arm,
        "prep": prep,
        "tau_seconds": tau,
        "t_readout_seconds": meta.get("t_readout_seconds", 0.0),
        "is_model_check": meta.get("is_model_check", False),
        "is_t1_calibration": is_t1,
        "ops": ops,
        "actual_x_primary": actual_x_primary,
        "actual_x_spectator": actual_x_spectator,
        "reset_start_dt": reset_start_dt,
        "measure_start_dt": measure_start_dt,
        "errors": errors,
    }

def run_transpiler_audit(backend_name="ibm_marrakesh"):
    snapshot_path = DATA_DIR / f"target_snapshot_{backend_name}.json"
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
    campaign_suite = builder.generate_full_circuit_suite()
    pilot_t1 = builder.generate_pilot_t1_curve()
    full_suite = campaign_suite + pilot_t1

    backend = get_backend(backend_name)
    target = backend.target
    durations = target.durations()
    initial_layout = [q_primary, q_spectator]

    print(f"Auditing {len(full_suite)} total circuits (44 campaign + 8 pilot T1)...")
    raw_circuits = [c[1] for c in full_suite]
    isa_circuits = transpile(
        raw_circuits,
        target=target,
        initial_layout=initial_layout,
        optimization_level=0
    )

    manifest_entries = []
    all_errors = []

    for idx, (label, orig_qc, meta) in enumerate(full_suite):
        isa_qc = isa_circuits[idx]
        res = audit_single_circuit(isa_qc, meta, durations, q_primary, q_spectator, dt)
        if res["errors"]:
            all_errors.extend(res["errors"])

        qasm_repr = isa_qc.qasm() if hasattr(isa_qc, "qasm") else str(isa_qc.data)
        circuit_hash = hashlib.sha256(qasm_repr.encode("utf-8")).hexdigest()

        manifest_entries.append({
            "index": idx,
            "label": label,
            "arm": res["arm"],
            "prep": res["prep"],
            "tau_seconds": res["tau_seconds"],
            "t_readout_seconds": res["t_readout_seconds"],
            "is_model_check": res["is_model_check"],
            "is_t1_calibration": res["is_t1_calibration"],
            "reset_start_dt": res["reset_start_dt"],
            "actual_x_primary": res["actual_x_primary"],
            "actual_x_spectator": res["actual_x_spectator"],
            "circuit_sha256": circuit_hash,
        })

    # Intentional corruption verification tests:
    # Test 1: +50 us timing perturbation on tau
    print("Testing intentional corruption detection: +50 us tau perturbation...")
    corrupt_qc = builder.build_circuit("D", 8e-9 + 50e-6, "G", 0.0, "corrupt_tau_test")
    corrupt_isa = transpile(corrupt_qc, target=target, initial_layout=initial_layout, optimization_level=0)
    # Check with meta claiming tau=8 ns
    corrupt_res = audit_single_circuit(corrupt_isa, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, durations, q_primary, q_spectator, dt)
    if not corrupt_res["errors"]:
        raise RuntimeError("FAIL-CLOSED CHECK FAILED: Audit did NOT catch intentional +50 us timing perturbation!")
    print(f"Intentional timing corruption correctly caught: {corrupt_res['errors'][0]}")

    # Test 2: Deleted X gate
    print("Testing intentional corruption detection: deleted X gate...")
    corrupt_x_qc = builder.build_circuit("D", 8e-9, "G", 0.0, "corrupt_x_test")
    # Delete first X gate
    for i, inst in enumerate(corrupt_x_qc.data):
        if inst.operation.name == "x":
            del corrupt_x_qc.data[i]
            break
    corrupt_x_isa = transpile(corrupt_x_qc, target=target, initial_layout=initial_layout, optimization_level=0)
    corrupt_x_res = audit_single_circuit(corrupt_x_isa, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, durations, q_primary, q_spectator, dt)
    if not corrupt_x_res["errors"]:
        raise RuntimeError("FAIL-CLOSED CHECK FAILED: Audit did NOT catch intentional deleted X gate!")
    print(f"Intentional X gate deletion correctly caught: {corrupt_x_res['errors'][0]}")

    # Canonical manifest serialization (POSIX LF newlines)
    manifest_json_str = json.dumps(manifest_entries, sort_keys=True, indent=2)
    manifest_bytes = manifest_json_str.replace("\r\n", "\n").encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    audit_passed = len(all_errors) == 0
    audit_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend_name,
        "primary_qubit": q_primary,
        "spectator_qubit": q_spectator,
        "optimization_level": 0,
        "initial_layout": initial_layout,
        "total_circuits": len(full_suite),
        "audit_passed": audit_passed,
        "audit_errors": all_errors,
        "manifest_sha256": manifest_sha256,
        "manifest": manifest_entries,
    }

    manifest_file = PREREG_DIR / "manifest_audit.json"
    with open(manifest_file, "wb") as f:
        report_str = json.dumps(audit_report, sort_keys=True, indent=2).replace("\r\n", "\n")
        f.write(report_str.encode("utf-8"))

    print(f"\n--- TIMING & TRANSPILER AUDIT RESULT ---")
    if audit_passed:
        print(f"STATUS: PASSED (ALL {len(full_suite)} CIRCUITS VERIFIED)")
        print(f"Reset start time verified: exactly 20032 dt (80.128 us) across all 44 campaign circuits")
        print(f"Manifest SHA256: {manifest_sha256}")
        print(f"Saved to: {manifest_file}")
    else:
        print(f"STATUS: FAILED ({len(all_errors)} errors detected)")
        for err in all_errors[:10]:
            print(f"  - {err}")
        sys.exit(1)

    return audit_report

if __name__ == "__main__":
    run_transpiler_audit("ibm_marrakesh")
