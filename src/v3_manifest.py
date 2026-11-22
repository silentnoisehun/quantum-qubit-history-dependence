#!/usr/bin/env python3
"""
v3_manifest.py — Frozen Manifest and Schedule Generator for L-Measurement v3.

Produces:
1. Deterministic pseudo-random circuit order per session (saved seed).
2. Compiled timing checks and circuit SHA256 hashes.
3. Planned schedule with explicit timestamps for 16 temporally separated sessions.
4. Total shot count dry-run and QPU budget calculation.
5. Carry-over analysis documentation.
"""

import json
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from v3_circuit_builder import CircuitBuilderV3, TimingSpecV3

def generate_frozen_manifest(
    start_utc_iso: str = "2026-11-22T11:00:00Z",
    created_at_utc: str = "2026-11-22T10:00:00Z",
    interval_minutes: int = 10,
    min_interval_minutes: int = 10,
    expiration_window_minutes: int = 30,
    include_dfast: bool = False,
    base_seed: int = 20261122
) -> Dict[str, Any]:
    builder = CircuitBuilderV3()
    circ_suite = builder.build_suite(include_dfast=include_dfast)
    
    # Base circuits info
    circuits_catalog = {}
    for cdef, qc, h in circ_suite:
        circuits_catalog[cdef["label"]] = {
            "label": cdef["label"],
            "arm": cdef["arm"],
            "tau_seconds": cdef["tau"],
            "prep": cdef["prep"],
            "t_readout_seconds": cdef["t_readout"],
            "t_name": cdef["t_name"],
            "shots": cdef["shots"],
            "is_model_check": cdef["is_model_check"],
            "is_optional_dfast": cdef["is_optional_dfast"],
            "depth": qc.depth(),
            "sha256": h
        }

    start_dt = datetime.fromisoformat(start_utc_iso.replace("Z", "+00:00"))
    sessions = []
    total_shots_campaign = 0

    for s_idx in range(16):
        session_seed = base_seed + s_idx
        rng = random.Random(session_seed)
        
        # Shuffle circuits deterministically for this session
        circuit_labels = list(circuits_catalog.keys())
        rng.shuffle(circuit_labels)

        scheduled_time = start_dt + timedelta(minutes=s_idx * interval_minutes)
        latest_allowed_time = scheduled_time + timedelta(minutes=expiration_window_minutes)
        session_shots = sum(circuits_catalog[lbl]["shots"] for lbl in circuit_labels)
        total_shots_campaign += session_shots

        sessions.append({
            "session_id": s_idx,
            "scheduled_time_utc": scheduled_time.isoformat(),
            "latest_allowed_time_utc": latest_allowed_time.isoformat(),
            "random_seed": session_seed,
            "circuit_execution_order": circuit_labels,
            "session_shots": session_shots,
            "session_circuits_count": len(circuit_labels)
        })

    seconds_per_shot = 24.0 / 44000.0  # ~0.0005455 s/shot
    est_qpu_seconds_per_session = sessions[0]["session_shots"] * seconds_per_shot
    est_total_qpu_seconds = total_shots_campaign * seconds_per_shot

    manifest = {
        "manifest_version": "v3.0.0-frozen",
        "created_at_utc": created_at_utc,
        "backend": "ibm_marrakesh",
        "expected_instance": "open-instance",
        "processor_type": "Heron r2",
        "qubit_primary": 21,
        "qubit_spectator": 20,
        "timing_spec": {
            "dt_seconds": builder.timing.dt,
            "t_x_seconds": builder.timing.t_x,
            "t_c_seconds": builder.timing.t_c,
            "tau_0_seconds": builder.timing.tau_0,
            "tau_max_seconds": builder.timing.tau_max,
            "t_decay_seconds": builder.timing.t_decay,
            "rep_delay_seconds": builder.timing.rep_delay,
            "n_conditioning_pulses": builder.timing.n_pulses
        },
        "execution_options": {
            "init_qubits": True,
            "optimization_level": 0,
            "dynamical_decoupling": False,
            "twirling": False,
            "include_dfast": include_dfast
        },
        "timing_separation_rules": {
            "planned_interval_minutes": interval_minutes,
            "min_actual_interval_minutes": min_interval_minutes,
            "expiration_window_minutes": expiration_window_minutes,
            "rapid_catchup_prohibited": True,
            "rule": "Even if earlier sessions completed late, no session may be submitted until at least min_actual_interval_minutes have elapsed since the previous session."
        },
        "carry_over_analysis": {
            "init_qubits": "Requested runtime option for initial state reset.",
            "repetition_delay_us": 250.0,
            "pre_reset_conditioning_and_delay_us": 80.128,
            "inter_session_spacing_minutes": interval_minutes,
            "risk_mitigation": "Within-block circuit randomization balances temporal drift. 10-minute separated sessions provide time separation, though inter-session correlation remains an empirical property evaluated in analysis."
        },
        "budget_estimation": {
            "total_sessions": 16,
            "shots_per_session": sessions[0]["session_shots"],
            "circuits_per_session": sessions[0]["session_circuits_count"],
            "total_shots_campaign": total_shots_campaign,
            "calibrated_seconds_per_shot": seconds_per_shot,
            "estimated_qpu_seconds_per_session": round(est_qpu_seconds_per_session, 2),
            "estimated_total_qpu_seconds": round(est_total_qpu_seconds, 2),
            "quota_enforcement": "The actual available quota MUST be queried live from the active IBM Quantum account before submission. If available remaining QPU seconds < estimated total QPU seconds, execution will fail-closed."
        },
        "circuits_catalog": circuits_catalog,
        "sessions": sessions
    }

    # Manifest self-hash (excluding hash field)
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    return manifest

if __name__ == "__main__":
    import os
    os.makedirs("prereg", exist_ok=True)
    manifest_core = generate_frozen_manifest(include_dfast=False)
    with open("prereg/v3_manifest_core.json", "w", encoding="utf-8") as f:
        json.dump(manifest_core, f, indent=2)
    print(f"Core manifest created: prereg/v3_manifest_core.json (SHA256: {manifest_core['manifest_sha256'][:16]}...)")
    print(f"Total shots: {manifest_core['budget_estimation']['total_shots_campaign']}, Est QPU time: {manifest_core['budget_estimation']['estimated_total_qpu_seconds']} s")

    manifest_full = generate_frozen_manifest(include_dfast=True)
    with open("prereg/v3_manifest_full.json", "w", encoding="utf-8") as f:
        json.dump(manifest_full, f, indent=2)
    print(f"Full manifest (with D_fast) created: prereg/v3_manifest_full.json (SHA256: {manifest_full['manifest_sha256'][:16]}...)")
    print(f"Total shots: {manifest_full['budget_estimation']['total_shots_campaign']}, Est QPU time: {manifest_full['budget_estimation']['estimated_total_qpu_seconds']} s")
