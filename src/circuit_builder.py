#!/usr/bin/env python3
"""
circuit_builder.py — Strict fail-closed circuit builder for Qubit History Dependence.
Constructs D, I, Nb, and D_fast circuits with exact timing matching:
- Total pre-reset duration: tau_max + T_c (strictly identical across all arms)
- Slot-matched concurrent execution for primary and spectator qubits
- Barriers around every conditioning gate (single-qubit barriers to prevent serialization)
- Explicit initial layout
"""

from dataclasses import dataclass
from typing import List, Tuple
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

@dataclass
class TimingSpec:
    dt: float = 4e-9                 # 4 ns sample rate on ibm_marrakesh
    t_x: float = 36e-9               # 9 dt = 36 ns
    t_c: float = 16.128e-6           # 4032 dt = 16128 ns
    n_pulses: int = 64               # N = 64 X pulses
    tau_max: float = 64.0e-6         # 16000 dt = 64000 ns
    tau_0: float = 8e-9              # 2 dt min delay
    t_decay: float = 168.0e-6        # T approx T1 = 168 us (42000 dt)

class CircuitBuilder:
    def __init__(self, q_primary: int = 21, q_spectator: int = 20, timing: TimingSpec = None):
        self.q = q_primary
        self.q_prime = q_spectator
        self.timing = timing or TimingSpec()

    def build_circuit(self, arm: str, tau: float, prep_state: str, t_readout: float, label: str) -> QuantumCircuit:
        """
        Builds a single pre-registered circuit.
        arm: 'D', 'I', 'Nb', 'D_fast'
        tau: delay between conditioning and reset (seconds)
        prep_state: 'G' (ground reference, no prep) or 'E' (excited, X prep)
        t_readout: decay time after preparation (seconds)
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

        # 2. Conditioning block (duration T_c) - STRICTLY CONCURRENT ON BOTH QUBITS
        if arm == "D":
            # 64 slots of 252 ns each
            # Primary: delay(108 ns) -> X(36 ns) -> delay(108 ns)
            # Spectator: delay(252 ns) concurrent in each slot
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
                # Concurrent slot delay on spectator
                qc.delay(slot_total, qr[qp_idx], unit="s")

        elif arm == "I":
            # Primary and spectator both idle for T_c concurrently
            qc.delay(self.timing.t_c, qr[q_idx], unit="s")
            qc.delay(self.timing.t_c, qr[qp_idx], unit="s")

        elif arm == "Nb":
            # 64 slots of 252 ns each
            # Spectator: delay(108 ns) -> X(36 ns) -> delay(108 ns)
            # Primary: delay(252 ns) concurrent in each slot
            slot_delay = (self.timing.t_c - self.timing.n_pulses * self.timing.t_x) / self.timing.n_pulses
            half_delay = slot_delay / 2.0
            slot_total = self.timing.t_x + slot_delay
            for _ in range(self.timing.n_pulses):
                qc.barrier([qr[qp_idx]])
                qc.delay(half_delay, qr[qp_idx], unit="s")
                qc.barrier([qr[qp_idx]])
                qc.x(qr[qp_idx])
                qc.barrier([qr[qp_idx]])
                qc.delay(half_delay, qr[qp_idx], unit="s")
                qc.barrier([qr[qp_idx]])
                # Concurrent slot delay on primary
                qc.delay(slot_total, qr[q_idx], unit="s")

        elif arm == "D_fast":
            # 32 slots of 504 ns each
            # Primary: X(36 ns) -> X(36 ns) -> delay(432 ns)
            # Spectator: delay(504 ns) concurrent in each slot
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
                # Concurrent slot delay on spectator
                qc.delay(slot_total, qr[qp_idx], unit="s")
        else:
            raise ValueError(f"Unknown conditioning arm: {arm}")

        # Block boundary synchronization
        qc.barrier(qr)

        # 3. Post-conditioning delay: tau (concurrent on both qubits)
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

    def generate_full_circuit_suite(self) -> List[Tuple[str, QuantumCircuit, dict]]:
        """
        Generates the 44-circuit campaign suite per Section 8:
        - D and I arms at tau in [tau_0, 4 us, 16 us, 64 us] x [G0, GT, E0, ET] = 32 circuits
        - Model check: D and I at tau_0 x t=2T x [G, E] = 4 circuits
        - Nb and D_fast controls at tau_0 x [G0, GT, E0, ET] = 8 circuits
        Total = 44 circuits
        """
        tau_list = [self.timing.tau_0, 4.0e-6, 16.0e-6, 64.0e-6]
        T = self.timing.t_decay
        circuits = []

        # 1. Primary D & I arms
        for arm in ["D", "I"]:
            for tau in tau_list:
                tau_label = f"tau_{int(tau*1e9)}ns"
                for prep in ["G", "E"]:
                    for t_val, t_name in [(0.0, "t0"), (T, "tT")]:
                        label = f"{arm}_{tau_label}_{prep}_{t_name}"
                        meta = {
                            "arm": arm, "tau_seconds": tau, "prep": prep,
                            "t_readout_seconds": t_val, "is_model_check": False
                        }
                        circuits.append((label, self.build_circuit(arm, tau, prep, t_val, label), meta))

        # 2. Model check: t = 2T for D and I at tau_0
        tau_0 = self.timing.tau_0
        for arm in ["D", "I"]:
            for prep in ["G", "E"]:
                label = f"{arm}_tau_{int(tau_0*1e9)}ns_{prep}_t2T_modelcheck"
                meta = {
                    "arm": arm, "tau_seconds": tau_0, "prep": prep,
                    "t_readout_seconds": 2 * T, "is_model_check": True
                }
                circuits.append((label, self.build_circuit(arm, tau_0, prep, 2 * T, label), meta))

        # 3. Controls: Nb and D_fast at tau_0
        for arm in ["Nb", "D_fast"]:
            for prep in ["G", "E"]:
                for t_val, t_name in [(0.0, "t0"), (T, "tT")]:
                    label = f"{arm}_tau_{int(tau_0*1e9)}ns_{prep}_{t_name}"
                    meta = {
                        "arm": arm, "tau_seconds": tau_0, "prep": prep,
                        "t_readout_seconds": t_val, "is_model_check": False
                    }
                    circuits.append((label, self.build_circuit(arm, tau_0, prep, t_val, label), meta))

        return circuits

    def generate_pilot_t1_curve(self, num_points: int = 8) -> List[Tuple[str, QuantumCircuit, dict]]:
        """
        Generates 8-point T1 characterization curve on primary qubit q
        (prep X -> delay t -> measure)
        """
        t_max = 3.0 * self.timing.t_decay
        t_points = [i * (t_max / (num_points - 1)) for i in range(num_points)]
        pilot_circuits = []
        for idx, t_val in enumerate(t_points):
            label = f"T1_pilot_pt{idx}_{int(t_val*1e6)}us"
            qr = QuantumRegister(2, "q")
            cr = ClassicalRegister(1, "c")
            qc = QuantumCircuit(qr, cr, name=label)
            qc.reset(qr[0])
            qc.barrier(qr)
            qc.x(qr[0])
            qc.barrier(qr)
            if t_val > 1e-12:
                qc.delay(t_val, qr[0], unit="s")
            qc.barrier(qr)
            qc.measure(qr[0], cr[0])
            meta = {
                "arm": "T1_CALIBRATION",
                "tau_seconds": 0.0,
                "prep": "E",
                "t_readout_seconds": t_val,
                "is_model_check": False,
                "type": "t1_calibration",
                "point": idx
            }
            pilot_circuits.append((label, qc, meta))
        return pilot_circuits

if __name__ == "__main__":
    builder = CircuitBuilder(q_primary=21, q_spectator=20)
    suite = builder.generate_full_circuit_suite()
    t1_curve = builder.generate_pilot_t1_curve()
    print(f"Total campaign circuits generated: {len(suite)}")
    print(f"Total pilot T1 calibration circuits: {len(t1_curve)}")
