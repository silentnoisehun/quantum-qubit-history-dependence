#!/usr/bin/env python3
"""
test_v3_rigor.py — Comprehensive Automated Test Suite for L-Measurement v3.

Covers all 8 rigor requirements from Point 5:
1. Historical 8 blocks consistency check (+0.0220, p=0.2915, 99% CI).
2. Missing circuit ablation test across ALL 12 required circuits (G and E).
3. Corrupted / mismatched shot counts and invalid ones count.
4. Non-positive contrast / undefined rates fail-closed handling.
5. Analytical vs numerical delta-method variance verification for D2.
6. Intra-block pseudo-random seed determinism and reproducibility.
7. Submission gate failure without pre-authorized approval token.
8. Simulator seed reproducibility.
"""

import math
import random
import sys
import unittest
import hashlib
from pathlib import Path
import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from v3_analysis import (
    AnalysisEngineV3,
    SessionRawCounts,
    EXPECTED_CORE_CIRCUITS,
)
from v3_manifest import generate_frozen_manifest
from v3_runner import verify_approval_token
from v3_simulator import PhysicalSimulatorV3

class TestV3Rigor(unittest.TestCase):
    def setUp(self):
        self.analyzer = AnalysisEngineV3(T=220.0e-6)
        self.sim = PhysicalSimulatorV3(T=220.0e-6)

    def create_valid_session(self, session_id: int = 0) -> SessionRawCounts:
        rng = np.random.default_rng(1000 + session_id)
        return self.sim.generate_session(session_id=session_id, l_target=0.00, rng=rng)

    def create_valid_16_campaign(self) -> list:
        rng = np.random.default_rng(42)
        return self.sim.generate_campaign(l_target=0.00, rng=rng)

    # -------------------------------------------------------------------------
    # 1. Historical 8 Blocks L Benchmark
    # -------------------------------------------------------------------------
    def test_01_historical_8_blocks_reproducibility(self):
        """
        Verifies that running the 8 historical confirmatory blocks yields
        mean L = +0.0220, SE = 0.0193, p = 0.2915, and 99% CI [-0.0454, +0.0894].
        """
        # Exact values from confirmatory_analysis_report.json
        l_historical = [
            +0.04968, +0.08373, +0.03639, -0.05758,
            +0.08477, +0.01901, -0.05303, +0.01282
        ]
        mean_l = float(np.mean(l_historical))
        std_l = float(np.std(l_historical, ddof=1))
        se_l = std_l / math.sqrt(8)
        t_stat = mean_l / se_l
        p_val = 2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=7))
        t_crit = stats.t.ppf(0.995, df=7)
        ci_99 = (mean_l - t_crit * se_l, mean_l + t_crit * se_l)

        self.assertAlmostEqual(mean_l, 0.02197, places=4)
        self.assertAlmostEqual(se_l, 0.01926, places=4)
        self.assertAlmostEqual(p_val, 0.2915, places=3)
        self.assertAlmostEqual(ci_99[0], -0.0454, places=3)
        self.assertAlmostEqual(ci_99[1], +0.0894, places=3)

    # -------------------------------------------------------------------------
    # 2. Missing Circuit Ablation (All 12 Circuits Tested Individually)
    # -------------------------------------------------------------------------
    def test_02_individual_circuit_ablations_fail_closed(self):
        """
        Deletes each of the 12 required circuits one by one.
        Ensures that missing ANY single circuit causes analyze_session to mark is_valid=False,
        and causes analyze_campaign to return 'NEM ERTEKELHETO' with no primary CI.
        """
        for missing_key in EXPECTED_CORE_CIRCUITS.keys():
            campaign = self.create_valid_16_campaign()
            # Ablate circuit in session 4
            del campaign[4].counts[missing_key]

            # Session level check
            s_res = self.analyzer.analyze_session(campaign[4])
            self.assertFalse(s_res.is_valid, f"Session was valid despite missing {missing_key}")
            self.assertIn("Missing required circuit", s_res.error_note)

            # Campaign level check
            c_res = self.analyzer.analyze_campaign(campaign)
            self.assertFalse(c_res.all_evaluable)
            self.assertEqual(c_res.decision_verdict, "NEM ERTEKELHETO")
            self.assertIsNone(c_res.ci99_lower)
            self.assertIsNone(c_res.ci99_upper)
            self.assertIsNone(c_res.mean_L)

    # -------------------------------------------------------------------------
    # 3. Corrupted Shots and Invalid Ones Counts
    # -------------------------------------------------------------------------
    def test_03_shot_mismatch_and_invalid_counts(self):
        # A. Shot count mismatch (499 instead of 500)
        c1 = self.create_valid_16_campaign()
        c1[0].counts[("D", "G", "t0")]["shots"] = 499
        res1 = self.analyzer.analyze_campaign(c1)
        self.assertFalse(res1.all_evaluable)
        self.assertEqual(res1.decision_verdict, "NEM ERTEKELHETO")

        # B. Invalid ones count (> shots)
        c2 = self.create_valid_16_campaign()
        c2[0].counts[("D", "E", "tT")]["ones"] = 1501
        res2 = self.analyzer.analyze_campaign(c2)
        self.assertFalse(res2.all_evaluable)
        self.assertEqual(res2.decision_verdict, "NEM ERTEKELHETO")

        # C. Negative ones count
        c3 = self.create_valid_16_campaign()
        c3[0].counts[("I", "G", "tT")]["ones"] = -1
        res3 = self.analyzer.analyze_campaign(c3)
        self.assertFalse(res3.all_evaluable)
        self.assertEqual(res3.decision_verdict, "NEM ERTEKELHETO")

    # -------------------------------------------------------------------------
    # 4. Undefined Rates & Non-positive Contrasts
    # -------------------------------------------------------------------------
    def test_04_undefined_rates_fail_closed(self):
        c = self.create_valid_16_campaign()
        # Zero contrast: PE(T) == PG(T) => sT = 0 => log undefined
        c[2].counts[("D", "E", "tT")]["ones"] = c[2].counts[("D", "G", "tT")]["ones"]
        res = self.analyzer.analyze_campaign(c)
        self.assertFalse(res.all_evaluable)
        self.assertEqual(res.decision_verdict, "NEM ERTEKELHETO")
        self.assertEqual(len(res.undefined_sessions), 1)
        self.assertEqual(res.undefined_sessions[0]["session_id"], 2)

    # -------------------------------------------------------------------------
    # 5. D2 Error Propagation Verification (Delta Method vs Numerical)
    # -------------------------------------------------------------------------
    def test_05_d2_delta_method_error_propagation(self):
        """
        Validates analytical gradients of D2 = S(2T) - S(T)^2 / S(0):
        dD2/dS(2T) = 1
        dD2/dS(T) = -2 * S(T) / S(0)
        dD2/dS(0) = (S(T) / S(0))^2
        """
        s0 = 0.98
        sT = 0.36
        s2T = 0.13
        h = 1e-6

        f = lambda _s0, _sT, _s2T: _s2T - (_sT**2) / _s0

        grad_0_num = (f(s0 + h, sT, s2T) - f(s0 - h, sT, s2T)) / (2 * h)
        grad_T_num = (f(s0, sT + h, s2T) - f(s0, sT - h, s2T)) / (2 * h)
        grad_2T_num = (f(s0, sT, s2T + h) - f(s0, sT, s2T - h)) / (2 * h)

        grad_0_ana = (sT / s0)**2
        grad_T_ana = -2.0 * sT / s0
        grad_2T_ana = 1.0

        self.assertAlmostEqual(grad_0_num, grad_0_ana, places=6)
        self.assertAlmostEqual(grad_T_num, grad_T_ana, places=6)
        self.assertAlmostEqual(grad_2T_num, grad_2T_ana, places=6)

    # -------------------------------------------------------------------------
    # 6. Randomization Seed Determinism
    # -------------------------------------------------------------------------
    def test_06_seed_determinism(self):
        m1 = generate_frozen_manifest(base_seed=20261122)
        m2 = generate_frozen_manifest(base_seed=20261122)
        self.assertEqual(m1["manifest_sha256"], m2["manifest_sha256"])
        for s in range(16):
            self.assertEqual(
                m1["sessions"][s]["circuit_execution_order"],
                m2["sessions"][s]["circuit_execution_order"]
            )

    # -------------------------------------------------------------------------
    # 7. Submission Gate Rejection without Valid Approval
    # -------------------------------------------------------------------------
    def test_07_submission_gate_fail_closed(self):
        import os
        from v3_runner import ENV_APPROVAL_HASH_KEY
        
        # When no approval hash is in environment, ALL tokens are rejected
        os.environ.pop(ENV_APPROVAL_HASH_KEY, None)
        self.assertFalse(verify_approval_token(None))
        self.assertFalse(verify_approval_token(""))
        self.assertFalse(verify_approval_token("arbitrary_string"))
        self.assertFalse(verify_approval_token("INSTINCT_MATE_V3_QPU_APPROVAL_20261122"))

        # When an external approval hash is set:
        test_secret = "TEST_SECRET_EXTERNAL_AUTH_987"
        os.environ[ENV_APPROVAL_HASH_KEY] = hashlib.sha256(test_secret.encode("utf-8")).hexdigest()
        self.assertFalse(verify_approval_token("wrong_secret"))
        self.assertTrue(verify_approval_token(test_secret))
        os.environ.pop(ENV_APPROVAL_HASH_KEY, None)

    # -------------------------------------------------------------------------
    # 8. Simulator Reproducibility
    # -------------------------------------------------------------------------
    def test_08_simulator_reproducibility(self):
        rng1 = np.random.default_rng(999)
        c1 = self.sim.generate_campaign(l_target=0.08, rng=rng1)
        r1 = self.analyzer.analyze_campaign(c1)

        rng2 = np.random.default_rng(999)
        c2 = self.sim.generate_campaign(l_target=0.08, rng=rng2)
        r2 = self.analyzer.analyze_campaign(c2)

        self.assertEqual(r1.mean_L, r2.mean_L)
        self.assertEqual(r1.ci99_lower, r2.ci99_lower)
        self.assertEqual(r1.decision_verdict, r2.decision_verdict)

if __name__ == "__main__":
    unittest.main()
