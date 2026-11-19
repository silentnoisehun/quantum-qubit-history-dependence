#!/usr/bin/env python3
"""
fetch_backend_data.py — Hardware Target Constraints & Calibration Snapshot
Extracts target timing, basis gates, and calibration data for ibm_marrakesh.
Implements the deterministic rule for selecting primary qubit q and spectator qubit q'.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

import qiskit
import qiskit_ibm_runtime
from qiskit_ibm_runtime import QiskitRuntimeService

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (1) (1).json")

def get_service():
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token = json.load(f)["apikey"]
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")
    return QiskitRuntimeService(channel="ibm_quantum_platform")

def fetch_and_record(backend_name="ibm_marrakesh"):
    print(f"Connecting to IBM Quantum Platform to query {backend_name}...")
    service = get_service()
    backend = service.backend(backend_name)
    target = backend.target
    props = backend.properties()

    dt = target.dt
    granularity = target.granularity
    min_length = target.min_length
    pulse_alignment = target.pulse_alignment
    acquire_alignment = target.acquire_alignment

    rep_delay_range = backend.configuration().rep_delay_range
    default_rep_delay = backend.configuration().default_rep_delay
    basis_gates = backend.configuration().basis_gates

    print(f"Backend: {backend_name}")
    print(f"dt: {dt} s")
    print(f"granularity: {granularity}")
    print(f"min_length: {min_length}")
    print(f"rep_delay_range: {rep_delay_range}")
    print(f"default_rep_delay: {default_rep_delay}")
    print(f"basis_gates: {basis_gates}")

    # Collect qubit properties
    qubits_data = []
    num_qubits = backend.num_qubits

    for i in range(num_qubits):
        try:
            t1 = props.t1(i)
            t2 = props.t2(i)
            ro_error = props.readout_error(i)
            x_error = props.gate_error("x", (i,))
            qubits_data.append({
                "qubit": i,
                "t1": t1,
                "t2": t2,
                "ro_error": ro_error,
                "x_error": x_error,
            })
        except Exception:
            continue

    # Deterministic selection rule:
    # 1. Readout error in best quartile (lowest 25%)
    # 2. Distance of T1 from median T1 is minimized
    # 3. Has at least one adjacent neighbor q' with ro_error in best half
    t1_values = [q["t1"] for q in qubits_data if q["t1"] is not None]
    median_t1 = float(np.median(t1_values))
    ro_values = [q["ro_error"] for q in qubits_data if q["ro_error"] is not None]
    q25_ro = float(np.percentile(ro_values, 25))
    q50_ro = float(np.percentile(ro_values, 50))

    coupling_map = backend.coupling_map
    adj = {i: set() for i in range(num_qubits)}
    for u, v in coupling_map:
        adj[u].add(v)
        adj[v].add(u)

    candidates = []
    for q in qubits_data:
        idx = q["qubit"]
        if q["t1"] is None or q["ro_error"] is None or q["x_error"] is None:
            continue
        if q["ro_error"] <= q25_ro:
            # check neighbors
            valid_neighbors = []
            for nbr in sorted(adj[idx]):
                nbr_data = next((item for item in qubits_data if item["qubit"] == nbr), None)
                if nbr_data and nbr_data["ro_error"] is not None and nbr_data["ro_error"] <= q50_ro:
                    valid_neighbors.append((nbr, nbr_data))
            if valid_neighbors:
                t1_dist = abs(q["t1"] - median_t1)
                candidates.append((t1_dist, q, valid_neighbors))

    candidates.sort(key=lambda x: x[0])
    selected_t1_dist, selected_q, selected_nbrs = candidates[0]
    q_primary = selected_q["qubit"]
    # choose neighbor with best ro_error
    selected_nbrs.sort(key=lambda x: x[1]["ro_error"])
    q_spectator = selected_nbrs[0][0]

    # Gate durations for selected qubit
    x_duration = target["x"][(q_primary,)].duration if "x" in target and (q_primary,) in target["x"] else None
    reset_duration = target["reset"][(q_primary,)].duration if "reset" in target and (q_primary,) in target["reset"] else None
    measure_duration = target["measure"][(q_primary,)].duration if "measure" in target and (q_primary,) in target["measure"] else None

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend_name,
        "qiskit_version": qiskit.__version__,
        "qiskit_ibm_runtime_version": qiskit_ibm_runtime.__version__,
        "dt_seconds": dt,
        "granularity_samples": granularity,
        "min_length_samples": min_length,
        "pulse_alignment_samples": pulse_alignment,
        "acquire_alignment_samples": acquire_alignment,
        "rep_delay_range_seconds": rep_delay_range,
        "default_rep_delay_seconds": default_rep_delay,
        "basis_gates": basis_gates,
        "median_t1_seconds": median_t1,
        "selected_q_primary": {
            "index": q_primary,
            "t1_seconds": selected_q["t1"],
            "t2_seconds": selected_q["t2"],
            "readout_error": selected_q["ro_error"],
            "x_error": selected_q["x_error"],
            "x_duration_seconds": x_duration,
            "reset_duration_seconds": reset_duration,
            "measure_duration_seconds": measure_duration,
        },
        "selected_q_spectator": {
            "index": q_spectator,
            "t1_seconds": selected_nbrs[0][1]["t1"],
            "t2_seconds": selected_nbrs[0][1]["t2"],
            "readout_error": selected_nbrs[0][1]["ro_error"],
            "x_error": selected_nbrs[0][1]["x_error"],
        },
        "all_qubits_calibration": qubits_data,
    }

    out_file = DATA_DIR / f"target_snapshot_{backend_name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSnapshot saved successfully to: {out_file}")
    print(f"Primary Qubit q: {q_primary} (T1 = {selected_q['t1']*1e6:.2f} us, RO err = {selected_q['ro_error']:.4f})")
    print(f"Spectator Qubit q': {q_spectator} (T1 = {selected_nbrs[0][1]['t1']*1e6:.2f} us, RO err = {selected_nbrs[0][1]['ro_error']:.4f})")
    if x_duration:
        print(f"X duration: {x_duration*1e9:.1f} ns")
    if reset_duration:
        print(f"Reset duration: {reset_duration*1e9:.1f} ns")
    if measure_duration:
        print(f"Measure duration: {measure_duration*1e9:.1f} ns")
    return summary

if __name__ == "__main__":
    fetch_and_record("ibm_marrakesh")
