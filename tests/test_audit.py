#!/usr/bin/env python3
"""
test_audit.py — Automated Unit & Fail-Closed Regression Tests (Offline with FakeMarrakesh)
"""

import sys
from pathlib import Path
import numpy as np
import pytest
from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from circuit_builder import CircuitBuilder, TimingSpec
from audit_transpiler import audit_single_circuit
from pilot_blind_analysis import PilotBlindAnalyzer

def test_circuit_builder_timing_concurrency():
    b = CircuitBuilder(21, 20)
    for arm in ["D", "I", "Nb", "D_fast"]:
        qc = b.build_circuit(arm, 8e-9, "G", 0.0, f"test_{arm}")
        assert qc.num_qubits == 2
        assert qc.num_clbits == 1

def test_timing_audit_catches_tau_corruption():
    backend = FakeMarrakesh()
    b = CircuitBuilder(21, 20)
    corrupt_qc = b.build_circuit("D", 8e-9 + 50e-6, "G", 0.0, "corrupt_tau")
    isa_qc = transpile(corrupt_qc, target=backend.target, initial_layout=[21, 20], optimization_level=0)
    res = audit_single_circuit(isa_qc, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, backend.target.durations(), 21, 20, 4e-9)
    assert len(res["errors"]) > 0
    assert "Conditioning-to-reset gap mismatch" in res["errors"][0]

def test_audit_catches_deleted_x():
    backend = FakeMarrakesh()
    b = CircuitBuilder(21, 20)
    corrupt_qc = b.build_circuit("D", 8e-9, "G", 0.0, "corrupt_x")
    for i, inst in enumerate(corrupt_qc.data):
        if inst.operation.name == "x":
            del corrupt_qc.data[i]
            break
    isa_qc = transpile(corrupt_qc, target=backend.target, initial_layout=[21, 20], optimization_level=0)
    res = audit_single_circuit(isa_qc, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, backend.target.durations(), 21, 20, 4e-9)
    assert len(res["errors"]) > 0
    assert "Primary X mismatch" in res["errors"][0]

def test_blind_analyzer():
    analyzer = PilotBlindAnalyzer()
    mock_t = [i * 30e-6 for i in range(8)]
    mock_p = [0.95 * np.exp(-t / 168e-6) + 0.02 for t in mock_t]
    fit = analyzer.fit_t1(mock_t, mock_p)
    assert 150.0 < fit["t1_empirical_us"] < 190.0

if __name__ == "__main__":
    import numpy as np
    test_circuit_builder_timing_concurrency()
    print("Circuit concurrency test: PASSED")
    test_timing_audit_catches_tau_corruption()
    print("Fail-closed timing corruption test: PASSED")
    test_audit_catches_deleted_x()
    print("Fail-closed X-deletion test: PASSED")
    test_blind_analyzer()
    print("Blind analyzer self-test: PASSED")
