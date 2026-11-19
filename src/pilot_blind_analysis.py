#!/usr/bin/env python3
"""
pilot_blind_analysis.py — Blinded Pilot Analysis Pipeline
Implements Section 13 and Pre-registration Blinding Protocol:
- Analyzes 8-point T1 calibration curve to estimate empirical T1
- Computes arm-averaged pooled metrics: S(0) contrast, P_G(0) baseline, and variance
- STRICTLY BLINDS L(tau_0) sign and magnitude: no relative direction or hypothesis verdict is computed
- Outputs characterization report to calibrate thresholds for confirmatory pre-registration
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import curve_fit

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def exp_decay(t, a, inv_t1, b):
    return a * np.exp(-inv_t1 * t) + b

class PilotBlindAnalyzer:
    def __init__(self, dt: float = 4e-9):
        self.dt = dt

    def fit_t1(self, t_seconds: List[float], p1_values: List[float]) -> Dict:
        """
        Fits 8-point T1 relaxation curve: P1(t) = A * exp(-t / T1) + B
        """
        t_arr = np.array(t_seconds, dtype=float)
        p_arr = np.array(p1_values, dtype=float)

        p0 = [0.95, 1.0 / 168.0e-6, 0.02]
        bounds = ([0.5, 1.0 / 2000.0e-6, 0.0], [1.05, 1.0 / 10.0e-6, 0.2])

        popt, pcov = curve_fit(exp_decay, t_arr, p_arr, p0=p0, bounds=bounds, maxfev=10000)
        a_fit, inv_t1_fit, b_fit = popt
        t1_fit = 1.0 / inv_t1_fit
        t1_err = math.sqrt(pcov[1, 1]) / (inv_t1_fit ** 2)

        residuals = p_arr - exp_decay(t_arr, *popt)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((p_arr - np.mean(p_arr)) ** 2)
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0

        return {
            "t1_empirical_seconds": float(t1_fit),
            "t1_empirical_us": float(t1_fit * 1e6),
            "t1_stderr_seconds": float(t1_err),
            "amplitude_A": float(a_fit),
            "baseline_B": float(b_fit),
            "r_squared": r_squared
        }

    def analyze_blinded_pilot(self, circuit_metadata: List[Dict], bitstring_counts: List[Dict[str, int]]) -> Dict:
        """
        Processes pilot results with strict blinding of hypothesis direction.
        """
        t1_points_t = []
        t1_points_p1 = []

        campaign_s0 = []
        campaign_pg0 = []
        campaign_all_p = []

        for meta, counts in zip(circuit_metadata, bitstring_counts):
            total_shots = sum(counts.values())
            # Transmon measurement on single classical bit: '1' is excited state
            shots_1 = counts.get("1", 0) + counts.get("0x1", 0)
            p1 = shots_1 / total_shots if total_shots > 0 else 0.0
            campaign_all_p.append(p1)

            if meta.get("type") == "t1_calibration":
                t1_points_t.append(meta["t_readout_seconds"])
                t1_points_p1.append(p1)

            elif meta.get("prep") == "G" and meta.get("t_readout_seconds", 0.0) == 0.0:
                campaign_pg0.append(p1)

        # Pair E0 and G0 to compute S(0)
        e0_circuits = {m["arm"] + "_" + str(m.get("tau_seconds", 0)): p
                       for m, p in zip(circuit_metadata, campaign_all_p)
                       if m.get("prep") == "E" and m.get("t_readout_seconds", 0.0) == 0.0}
        g0_circuits = {m["arm"] + "_" + str(m.get("tau_seconds", 0)): p
                       for m, p in zip(circuit_metadata, campaign_all_p)
                       if m.get("prep") == "G" and m.get("t_readout_seconds", 0.0) == 0.0}

        for key, p_e0 in e0_circuits.items():
            if key in g0_circuits:
                campaign_s0.append(p_e0 - g0_circuits[key])

        t1_fit_result = self.fit_t1(t1_points_t, t1_points_p1) if len(t1_points_t) >= 4 else {}

        mean_s0 = float(np.mean(campaign_s0)) if campaign_s0 else None
        mean_pg0 = float(np.mean(campaign_pg0)) if campaign_pg0 else None
        pooled_std = float(np.std(campaign_all_p, ddof=1)) if len(campaign_all_p) > 1 else None

        # Estimated dispersion for sample size calibration
        # SE for binary readout S(t) = sqrt(Var(E) + Var(G)) approx sqrt(2 * P*(1-P)/N)
        est_se_s = math.sqrt(2 * 0.25 / 1000)

        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_type": "PILOT_BLINDED_CHARACTERIZATION",
            "blinding_status": "ENFORCED (L sign and magnitude completely suppressed)",
            "t1_fit": t1_fit_result,
            "pooled_metrics": {
                "mean_initial_contrast_S0": mean_s0,
                "mean_baseline_PG0": mean_pg0,
                "pooled_sample_std": pooled_std,
                "single_circuit_theoretical_se": est_se_s
            },
            "recommended_thresholds_for_confirmatory": {
                "min_contrast_S0_gate": 0.80,
                "max_baseline_PG0_gate": 0.08,
                "recommended_blocks": 8,
                "shots_per_circuit": 2500
            }
        }

        out_path = RESULTS_DIR / "pilot_characterization.json"
        with open(out_path, "wb") as f:
            f.write(json.dumps(report, sort_keys=True, indent=2).replace("\r\n", "\n").encode("utf-8"))

        print(f"Blinded pilot characterization report written to: {out_path}")
        print(f"T1 estimated: {t1_fit_result.get('t1_empirical_us', 'N/A'):.2f} us")
        print(f"Pooled S(0) contrast: {mean_s0:.4f}")
        print(f"Pooled P_G(0) baseline: {mean_pg0:.4f}")
        print("BLINDING ENFORCED: No hypothesis evaluation performed.")
        return report

if __name__ == "__main__":
    analyzer = PilotBlindAnalyzer()
    # Self-test on mock data
    mock_t = [i * 30e-6 for i in range(8)]
    mock_p = [0.95 * math.exp(-t / 168e-6) + 0.02 for t in mock_t]
    res = analyzer.fit_t1(mock_t, mock_p)
    print("Self-test T1 fit:", res)
