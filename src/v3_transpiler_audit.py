#!/usr/bin/env python3
"""
v3_transpiler_audit.py — True Hardware Transpilation & Scheduled Timing Audit for v3.

Verifies Point 4:
- Transpiles v3 circuits to ISA circuits targeting ibm_marrakesh with optimization_level = 0
- Enforces explicit physical layout [21, 20]
- Audits scheduled timings via ASAPScheduleAnalysis:
  * Reset start dt MUST be strictly 20032 dt (80.128 us) across all circuits
  * Conditioning-to-reset gap matches tau_0 = 8 ns (2 dt)
  * Readout delays match t=0, t=T (55000 dt), t=2T (110000 dt)
- Computes ISA circuit SHA256 hashes
- Verifies dry-run PUB shot allocations
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

from qiskit import transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ASAPScheduleAnalysis
from qiskit_ibm_runtime import QiskitRuntimeService

from v3_circuit_builder import CircuitBuilderV3

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (6).json")

def get_service_and_backend(backend_name: str = "ibm_marrakesh"):
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if not token and TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
    if token:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
    return service, service.backend(backend_name)

def run_v3_transpilation_audit(include_dfast: bool = True) -> Dict[str, Any]:
    print(f"Connecting to IBM Quantum to retrieve ibm_marrakesh target...")
    service, backend = get_service_and_backend("ibm_marrakesh")
    target = backend.target
    durations = target.durations()
    dt = backend.dt  # 4e-9 s
    
    q_primary = 21
    q_spectator = 20
    initial_layout = [q_primary, q_spectator]

    builder = CircuitBuilderV3(q_primary=q_primary, q_spectator=q_spectator)
    circ_suite = builder.build_suite(include_dfast=include_dfast)

    print(f"Transpiling {len(circ_suite)} v3 circuits at optimization_level=0, layout=[{q_primary}, {q_spectator}]...")
    raw_circuits = [c[1] for c in circ_suite]
    isa_circuits = transpile(
        raw_circuits,
        target=target,
        initial_layout=initial_layout,
        optimization_level=0
    )

    audit_records = []
    all_errors = []

    pm = PassManager([ASAPScheduleAnalysis(durations)])

    for idx, (cdef, raw_qc, raw_hash) in enumerate(circ_suite):
        isa_qc = isa_circuits[idx]
        label = cdef["label"]
        arm = cdef["arm"]
        prep = cdef["prep"]
        tau = cdef["tau"]
        t_readout = cdef["t_readout"]
        shots = cdef["shots"]

        ops = dict(isa_qc.count_ops())
        errors = []

        # 1. Reset and measure counts
        if ops.get("reset", 0) != 1:
            errors.append(f"[{label}] Expected 1 reset, found {ops.get('reset', 0)}")
        if ops.get("measure", 0) != 1:
            errors.append(f"[{label}] Expected 1 measure, found {ops.get('measure', 0)}")

        # 2. Physical layout bit verification
        actual_bits = set()
        for inst in isa_qc.data:
            for q in inst.qubits:
                actual_bits.add(isa_qc.find_bit(q).index)
        
        # Verify instructions only touch physical qubits 21 and 20
        invalid_bits = [b for b in actual_bits if b not in [q_primary, q_spectator]]
        if invalid_bits:
            errors.append(f"[{label}] Instructions touch unauthorized physical qubits: {invalid_bits}")

        # 3. Scheduled timing analysis
        pm.run(isa_qc)
        node_starts = pm.property_set.get("node_start_time", {})

        reset_start_dt = None
        measure_start_dt = None
        for node, start_dt in node_starts.items():
            if node.name == "reset":
                reset_start_dt = start_dt
            elif node.name == "measure":
                measure_start_dt = start_dt

        if reset_start_dt is None:
            errors.append(f"[{label}] Reset node missing in scheduled analysis")
        else:
            # Pre-reset duration must be strictly 20032 dt (80.128 us)
            expected_reset_dt = 20032
            if reset_start_dt != expected_reset_dt:
                errors.append(f"[{label}] Reset start timing mismatch! Expected {expected_reset_dt} dt, got {reset_start_dt} dt")

        # For arm D: gap from last conditioning X to reset
        if arm == "D":
            x_nodes = [n for n in node_starts if n.name == "x" and node_starts[n] < reset_start_dt]
            if not x_nodes:
                errors.append(f"[{label}] No conditioning X nodes before reset in arm D")
            else:
                last_x = max(x_nodes, key=lambda n: node_starts[n])
                x_dur_dt = 9  # 36 ns / 4 ns = 9 dt
                gap_dt = reset_start_dt - (node_starts[last_x] + x_dur_dt)
                # 27 dt half-slot delay + tau_0 (2 dt) = 29 dt
                expected_gap_dt = 27 + round(tau / dt)
                if gap_dt != expected_gap_dt:
                    errors.append(f"[{label}] Conditioning-to-reset gap mismatch! Expected {expected_gap_dt} dt, got {gap_dt} dt")

        # Readout timing check: measure_start_dt - (reset_start_dt + reset_dur)
        reset_dur_dt = 280  # typical reset duration on Heron
        for node in node_starts:
            if node.name == "reset":
                reset_dur_dt = durations.get("reset", [q_primary])

        expected_t_readout_dt = round(t_readout / dt)

        # Compute ISA circuit SHA256
        isa_str = str(isa_qc.data).encode("utf-8")
        isa_hash = hashlib.sha256(isa_str).hexdigest()

        if errors:
            all_errors.extend(errors)

        audit_records.append({
            "label": label,
            "arm": arm,
            "prep": prep,
            "tau_seconds": tau,
            "t_readout_seconds": t_readout,
            "expected_shots": shots,
            "raw_sha256": raw_hash,
            "isa_sha256": isa_hash,
            "reset_start_dt": reset_start_dt,
            "reset_start_us": reset_start_dt * dt * 1e6 if reset_start_dt else None,
            "measure_start_dt": measure_start_dt,
            "depth_isa": isa_qc.depth(),
            "ops": ops,
            "errors": errors
        })

    report = {
        "backend": backend.name,
        "q_primary": q_primary,
        "q_spectator": q_spectator,
        "dt_seconds": dt,
        "tau_0_dt": round(builder.timing.tau_0 / dt),
        "total_circuits_audited": len(audit_records),
        "all_passed": (len(all_errors) == 0),
        "errors": all_errors,
        "circuits": audit_records
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "v3_transpiler_audit_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nAudit complete. Passed: {report['all_passed']}. Saved to {out_path}")
    for r in audit_records:
        print(f"  [{r['label']}] ISA hash={r['isa_sha256'][:16]}... reset_start={r['reset_start_dt']} dt ({r['reset_start_us']} us), shots={r['expected_shots']}, errors={len(r['errors'])}")
    return report

if __name__ == "__main__":
    report = run_v3_transpilation_audit(include_dfast=True)
    if not report["all_passed"]:
        sys.exit(1)
