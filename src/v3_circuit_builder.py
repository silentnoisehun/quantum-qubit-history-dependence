#!/usr/bin/env python3
"""
v3_circuit_builder.py — Circuit construction for L-Measurement v3 (0 vs +0.08).

Protocol v3 specifics:
- Backend: ibm_marrakesh (Heron r2), primary q=21, spectator q'=20
- Fixed decay time: T = 220.0 us (calibrated from pilot characterization)
- Conditioning min delay: tau_0 = 8 ns
- Repetition delay: rep_delay = 250 us
- init_qubits = True
- Optimization level = 0, Dynamical Decoupling = OFF, Twirling = OFF
- Arms:
  * D: 64 X pulses on q21, slot-matched delays on q20, duration T_c = 16.128 us
  * I: Idle for T_c on both qubits
  * Optional D_fast: 32 pairs of X pulses (total 64) at half interval
- Circuits per core block (12 circuits, 10,000 shots):
  * D: G0 (500), E0 (500), GT (500), ET (1500), G2T (1000), E2T (1000) -> 5000 shots
  * I: G0 (500), E0 (500), GT (500), ET (1500), G2T (1000), E2T (1000) -> 5000 shots
- Optional D_fast (4 circuits, 3000 shots):
  * D_fast: G0 (500), E0 (500), GT (500), ET (1500)
"""

import hashlib
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

@dataclass(frozen=True)
class TimingSpecV3:
    dt: float = 4e-9                 # 4 ns sample rate on ibm_marrakesh
    t_x: float = 36e-9               # 9 dt = 36 ns
    t_c: float = 16.128e-6           # 4032 dt = 16128 ns
    n_pulses: int = 64               # N = 64 X pulses
    tau_max: float = 64.0e-6         # 16000 dt = 64000 ns
    tau_0: float = 8e-9              # 2 dt min delay
    t_decay: float = 220.0e-6        # T = 220 us (55000 dt)
    rep_delay: float = 250.0e-6      # 250 us

class CircuitBuilderV3:
    def __init__(self, q_primary: int = 21, q_spectator: int = 20, timing: TimingSpecV3 = None):
        self.q = q_primary
        self.q_prime = q_spectator
        self.timing = timing or TimingSpecV3()

    def build_circuit(self, arm: str, tau: float, prep_state: str, t_readout: float, label: str) -> QuantumCircuit:
        """
        Builds a single v3 circuit with exact timing alignment.
        """
        qr = QuantumRegister(2, "q")
        cr = ClassicalRegister(1, "c")
        qc = QuantumCircuit(qr, cr, name=label)

        q_idx = 0
        qp_idx = 1

        # 1. Padding wait: tau_max - tau (concurrent on both qubits)
        pad_time = self.timing.tau_max - tau
        if pad_time > 1e-12:
            qc.delay(pad_time, qr[q_idx], unit="s")
            qc.delay(pad_time, qr[qp_idx], unit="s")
        qc.barrier(qr)

        # 2. Conditioning block (duration T_c) - strictly concurrent
        if arm == "D":
            slot_delay = (self.timing.t_c - self.timing.n_pulses * self.timing.t_x) / self.timing.n_pulses
            half_delay = slot_delay / 2.0
            slot_total = self.timing.t_x + slot_delay
            for _ in range(self.timing.n_pulses):
                qc.barrier([qr[q_idx]])
                qc.delay(half_delay, qr[q_idx], unit="s")
                qc.barrier([qr[q_idx]])
                qc.x(qr[q_idx])
                qc.barrier([qr[q_idx]])
                qc.delay(half_delay, qr[q_idx], unit="s")
                qc.barrier([qr[q_idx]])
                qc.delay(slot_total, qr[qp_idx], unit="s")

        elif arm == "I":
            qc.delay(self.timing.t_c, qr[q_idx], unit="s")
            qc.delay(self.timing.t_c, qr[qp_idx], unit="s")

        elif arm == "D_fast":
            n_pairs = self.timing.n_pulses // 2
            pair_delay = (self.timing.t_c - self.timing.n_pulses * self.timing.t_x) / n_pairs
            slot_total = 2 * self.timing.t_x + pair_delay
            for _ in range(n_pairs):
                qc.barrier([qr[q_idx]])
                qc.x(qr[q_idx])
                qc.barrier([qr[q_idx]])
                qc.x(qr[q_idx])
                qc.barrier([qr[q_idx]])
                qc.delay(pair_delay, qr[q_idx], unit="s")
                qc.barrier([qr[q_idx]])
                qc.delay(slot_total, qr[qp_idx], unit="s")
        else:
            raise ValueError(f"Unknown conditioning arm: {arm}")

        # Block boundary synchronization
        qc.barrier(qr)

        # 3. Post-conditioning delay: tau
        if tau > 1e-12:
            qc.delay(tau, qr[q_idx], unit="s")
            qc.delay(tau, qr[qp_idx], unit="s")
        qc.barrier(qr)

        # 4. Single reset on primary qubit q
        qc.reset(qr[q_idx])
        qc.barrier(qr)

        # 5. Preparation: X (E-circuits) or delay matched (G-circuits)
        if prep_state == "E":
            qc.x(qr[q_idx])
        elif prep_state == "G":
            qc.delay(self.timing.t_x, qr[q_idx], unit="s")
        else:
            raise ValueError(f"Unknown prep state: {prep_state}")
        qc.barrier(qr)

        # 6. Readout delay t
        if t_readout > 1e-12:
            qc.delay(t_readout, qr[q_idx], unit="s")
        qc.barrier(qr)

        # 7. Measurement on primary qubit q
        qc.measure(qr[q_idx], cr[0])
        return qc

    def get_core_circuit_definitions(self) -> List[Dict[str, Any]]:
        """
        Defines the 12 core circuits per block (10,000 shots total):
        - Arms D and I:
          * G0:  500 shots
          * E0:  500 shots
          * GT:  500 shots
          * ET:  1500 shots
          * G2T: 1000 shots
          * E2T: 1000 shots
        """
        T = self.timing.t_decay
        tau_0 = self.timing.tau_0
        defs = []

        for arm in ["D", "I"]:
            arm_specs = [
                ("G", 0.0, "t0", 500, False),
                ("E", 0.0, "t0", 500, False),
                ("G", T,   "tT", 500, False),
                ("E", T,   "tT", 1500, False),
                ("G", 2*T, "t2T", 1000, True),
                ("E", 2*T, "t2T", 1000, True),
            ]
            for prep, t_val, t_name, shots, is_mc in arm_specs:
                label = f"{arm}_tau_{int(tau_0*1e9)}ns_{prep}_{t_name}"
                if is_mc:
                    label += "_mc"
                defs.append({
                    "arm": arm,
                    "tau": tau_0,
                    "prep": prep,
                    "t_readout": t_val,
                    "t_name": t_name,
                    "shots": shots,
                    "is_model_check": is_mc,
                    "label": label,
                    "is_optional_dfast": False
                })
        return defs

    def get_dfast_circuit_definitions(self) -> List[Dict[str, Any]]:
        """
        Defines the 4 optional D_fast control circuits (3000 shots total):
        - G0: 500 shots, E0: 500 shots, GT: 500 shots, ET: 1500 shots
        """
        T = self.timing.t_decay
        tau_0 = self.timing.tau_0
        defs = []
        arm_specs = [
            ("G", 0.0, "t0", 500, False),
            ("E", 0.0, "t0", 500, False),
            ("G", T,   "tT", 500, False),
            ("E", T,   "tT", 1500, False),
        ]
        for prep, t_val, t_name, shots, is_mc in arm_specs:
            label = f"Dfast_tau_{int(tau_0*1e9)}ns_{prep}_{t_name}"
            defs.append({
                "arm": "D_fast",
                "tau": tau_0,
                "prep": prep,
                "t_readout": t_val,
                "t_name": t_name,
                "shots": shots,
                "is_model_check": is_mc,
                "label": label,
                "is_optional_dfast": True
            })
        return defs

    def build_suite(self, include_dfast: bool = False) -> List[Tuple[Dict[str, Any], QuantumCircuit, str]]:
        """
        Builds circuit objects, computes QASM / Qiskit instruction hashes.
        Returns list of (metadata, qc, sha256_hash).
        """
        circ_defs = self.get_core_circuit_definitions()
        if include_dfast:
            circ_defs += self.get_dfast_circuit_definitions()

        results = []
        for cdef in circ_defs:
            qc = self.build_circuit(
                arm=cdef["arm"],
                tau=cdef["tau"],
                prep_state=cdef["prep"],
                t_readout=cdef["t_readout"],
                label=cdef["label"]
            )
            # Compute canonical hash from circuit representation
            repr_bytes = str(qc.data).encode("utf-8")
            h = hashlib.sha256(repr_bytes).hexdigest()
            results.append((cdef, qc, h))
        return results

if __name__ == "__main__":
    builder = CircuitBuilderV3()
    core_suite = builder.build_suite(include_dfast=False)
    full_suite = builder.build_suite(include_dfast=True)
    print(f"Core suite circuits: {len(core_suite)}, Total shots: {sum(c[0]['shots'] for c in core_suite)}")
    print(f"Full suite (with D_fast): {len(full_suite)}, Total shots: {sum(c[0]['shots'] for c in full_suite)}")
    for cdef, qc, h in core_suite:
        print(f"  [{cdef['label']}] shots={cdef['shots']} hash={h[:16]}... depth={qc.depth()}")
