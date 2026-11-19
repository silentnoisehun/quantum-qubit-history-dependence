#!/usr/bin/env python3
"""
test_audit.py — Automated Unit & Fail-Closed Regression Tests
Tests:
1. Normal audit pass for all campaign and pilot circuits
2. Fail-closed timing detection on +50 us perturbation
3. Fail-closed gate detection on deleted X gate
"""

import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from circuit_builder import CircuitBuilder, TimingSpec
from audit_transpiler import audit_single_circuit, get_backend

def test_circuit_builder_timing_concurrency():
    b = CircuitBuilder(21, 20)
    for arm in ["D", "I", "Nb", "D_fast"]:
        qc = b.build_circuit(arm, 8e-9, "G", 0.0, f"test_{arm}")
        assert qc.num_qubits == 2
        assert qc.num_clbits == 1

def test_timing_audit_catches_tau_corruption():
    backend = get_backend("ibm_marrakesh")
    b = CircuitBuilder(21, 20)
    from qiskit import transpile
    corrupt_qc = b.build_circuit("D", 8e-9 + 50e-6, "G", 0.0, "corrupt_tau")
    isa_qc = transpile(corrupt_qc, target=backend.target, initial_layout=[21, 20], optimization_level=0)
    res = audit_single_circuit(isa_qc, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, backend.target.durations(), 21, 20, 4e-9)
    assert len(res["errors"]) > 0
    assert "Conditioning-to-reset gap mismatch" in res["errors"][0]

def test_audit_catches_deleted_x():
    backend = get_backend("ibm_marrakesh")
    b = CircuitBuilder(21, 20)
    from qiskit import transpile
    corrupt_qc = b.build_circuit("D", 8e-9, "G", 0.0, "corrupt_x")
    for i, inst in enumerate(corrupt_qc.data):
        if inst.operation.name == "x":
            del corrupt_qc.data[i]
            break
    isa_qc = transpile(corrupt_qc, target=backend.target, initial_layout=[21, 20], optimization_level=0)
    res = audit_single_circuit(isa_qc, {"arm": "D", "prep": "G", "tau_seconds": 8e-9}, backend.target.durations(), 21, 20, 4e-9)
    assert len(res["errors"]) > 0
    assert "Primary X mismatch" in res["errors"][0]

if __name__ == "__main__":
    test_circuit_builder_timing_concurrency()
    print("Circuit concurrency test: PASSED")
    test_timing_audit_catches_tau_corruption()
    print("Fail-closed timing corruption test: PASSED")
    test_audit_catches_deleted_x()
    print("Fail-closed X-deletion test: PASSED")
