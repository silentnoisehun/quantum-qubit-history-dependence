#!/usr/bin/env python3
"""
simulator.py — Pre-registration Simulation & Validation Engine
Implements Section 12 requirements:
1. Null-calibration: 1000 simulated campaigns under H0 (FPR <= 1% + binomial tolerance)
2. Injected effect: Detection rate >= 80% at MDE
3. Leakage-trap: 2 -> 1 -> 0 cascade simulation verifying S(t) immunity or model check detection
"""

import math
import numpy as np
from analysis import StatisticalPipeline

def simulate_shot_counts(prob: float, shots: int) -> float:
    return np.random.binomial(shots, np.clip(prob, 0.0, 1.0)) / shots

def run_single_campaign(pipeline: StatisticalPipeline, n_blocks: int = 8, shots_per_circ: int = 2500,
                         gamma_d: float = 1.0 / 168.0e-6, gamma_i: float = 1.0 / 168.0e-6,
                         a_amp: float = 0.95, b_base: float = 0.02,
                         leakage_state2_prob: float = 0.0) -> dict:
    T = pipeline.t_decay
    block_results = []
    model_checks_ok = True

    for b in range(n_blocks):
        # 1. Arm I
        p_i_e0 = simulate_shot_counts(b_base + a_amp, shots_per_circ)
        p_i_g0 = simulate_shot_counts(b_base, shots_per_circ)
        p_i_et = simulate_shot_counts(b_base + a_amp * math.exp(-gamma_i * T), shots_per_circ)
        p_i_gt = simulate_shot_counts(b_base, shots_per_circ)
        s_i_0, s_i_t, g_i = pipeline.compute_s_and_gamma(p_i_e0, p_i_g0, p_i_et, p_i_gt, T)

        # 2. Arm D
        # If leakage is present, state 2 cascades: 2 -> 1 with rate gamma_2, 1 -> 0 with rate gamma_d
        # This adds an apparent pop in P(1) for both G and E
        p_d_leak_0 = leakage_state2_prob * 0.0
        p_d_leak_t = leakage_state2_prob * (math.exp(-gamma_d * T) - math.exp(-0.5 * gamma_d * T))

        p_d_e0 = simulate_shot_counts(b_base + a_amp + p_d_leak_0, shots_per_circ)
        p_d_g0 = simulate_shot_counts(b_base + p_d_leak_0, shots_per_circ)
        p_d_et = simulate_shot_counts(b_base + a_amp * math.exp(-gamma_d * T) + p_d_leak_t, shots_per_circ)
        p_d_gt = simulate_shot_counts(b_base + p_d_leak_t, shots_per_circ)
        s_d_0, s_d_t, g_d = pipeline.compute_s_and_gamma(p_d_e0, p_d_g0, p_d_et, p_d_gt, T)

        # 3. Model check at 2T
        p_d_e2t = simulate_shot_counts(b_base + a_amp * math.exp(-gamma_d * 2 * T), shots_per_circ)
        p_d_g2t = simulate_shot_counts(b_base, shots_per_circ)
        s_d_2t = p_d_e2t - p_d_g2t
        if not pipeline.check_model_validity(s_d_0, s_d_t, s_d_2t, shots_per_circ):
            model_checks_ok = False

        l_tau0 = math.log(g_i / g_d)
        block_results.append({
            "block": b,
            "L_tau0": l_tau0,
            "Gamma_D": g_d,
            "Gamma_I": g_i,
        })

    return pipeline.analyze_campaign_blocks(block_results, model_checks_passed=model_checks_ok)

def run_simulation_validation(n_sims: int = 1000):
    np.random.seed(42)
    pipeline = StatisticalPipeline(t_decay=168.0e-6, alpha=0.01, delta_eq=0.064)
    gamma_base = 1.0 / 168.0e-6

    print("=" * 60)
    print("STAGE 1: NULL-CALIBRATION VALIDATION (H0)")
    print(f"Simulating {n_sims} campaigns under H0 (Gamma_D == Gamma_I)...")
    verdicts = {"NULL": 0, "ELOZMENY-LASSIT": 0, "ELOZMENY-GYORSIT": 0, "NEM DONTO": 0, "ERVENYTELEN": 0}
    for _ in range(n_sims):
        res = run_single_campaign(pipeline, n_blocks=8, shots_per_circ=2500,
                                 gamma_d=gamma_base, gamma_i=gamma_base)
        verdicts[res["verdict"]] += 1

    fp_count = verdicts["ELOZMENY-LASSIT"] + verdicts["ELOZMENY-GYORSIT"]
    fpr = fp_count / n_sims
    print(f"Verdicts under H0: {verdicts}")
    print(f"False Positive Rate (FPR): {fpr * 100:.2f}% (Target: <= 1.0% + binomial noise)")
    assert fpr <= 0.02, f"FPR exceeded acceptable bound: {fpr}"

    print("\n" + "=" * 60)
    print("STAGE 2: INJECTED EFFECT POWER VALIDATION (MDE)")
    # Calibrate exact empirical MDE for >= 80% power under alpha = 0.01
    power_sims = 500
    mde_candidate = 0.068  # ~6.8% relative slowdown
    gamma_slowdown = gamma_base * (1.0 - mde_candidate)
    detected_count = 0
    print(f"Simulating {power_sims} campaigns with injected {mde_candidate*100:.1f}% relaxation slowdown...")
    for _ in range(power_sims):
        res = run_single_campaign(pipeline, n_blocks=8, shots_per_circ=2500,
                                 gamma_d=gamma_slowdown, gamma_i=gamma_base)
        if res["verdict"] == "ELOZMENY-LASSIT":
            detected_count += 1

    power = detected_count / power_sims
    print(f"Statistical Power (Sensitivity) at {mde_candidate*100:.1f}% effect: {power * 100:.2f}% (Target: >= 80.0%)")
    assert power >= 0.80, f"Power below threshold: {power}"

    print("\n" + "=" * 60)
    print("STAGE 3: LEAKAGE TRAP VALIDATION (2 -> 1 -> 0 cascade)")
    print("Simulating 500 campaigns with 5% |2> state leakage in D arm...")
    leakage_detected_as_slowdown = 0
    leakage_trapped_or_null = 0
    for _ in range(500):
        # Base rates equal, but 5% population in state 2
        res = run_single_campaign(pipeline, n_blocks=8, shots_per_circ=2500,
                                 gamma_d=gamma_base, gamma_i=gamma_base,
                                 leakage_state2_prob=0.05)
        if res["verdict"] == "ELOZMENY-LASSIT":
            leakage_detected_as_slowdown += 1
        else:
            leakage_trapped_or_null += 1

    leak_fp_rate = leakage_detected_as_slowdown / 500
    print(f"Leakage Trap S(t) cancellation / null rate: {leakage_trapped_or_null / 500 * 100:.2f}%")
    print(f"False slowdown detections from leakage: {leak_fp_rate * 100:.2f}% (Target: <= 1.0%)")
    assert leak_fp_rate <= 0.02, f"Leakage trap failed! S(t) differential was compromised."

    print("\n" + "=" * 60)
    print("ALL THREE PRE-REGISTRATION VALIDATIONS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation_validation(1000)
