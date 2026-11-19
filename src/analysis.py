#!/usr/bin/env python3
"""
analysis.py — Pre-registered Frozen Statistical Analysis Pipeline
Implements Section 6, 10, 11, and 12:
- Calibrated to empirical T1 = 220.0 us
- Fail-safe handling: non-positive signal yields 'ERVENYTELEN' instead of throwing
- S(t) = P_E(t) - P_G(t)
- Gamma = -ln(S(T) / S(0)) / T
- L = ln(Gamma_I / Gamma_D) at tau_0
- Model check at t = 2T (alpha = 0.01)
- Block-level one-sample t-test at alpha = 0.01
- Holm-Bonferroni family-wise error rate control for secondary metrics S1 - S6
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

class StatisticalPipeline:
    def __init__(self, t_decay: float = 220.0e-6, alpha: float = 0.01, delta_eq: float = 0.064):
        self.t_decay = t_decay
        self.alpha = alpha
        self.delta_eq = delta_eq

    def compute_s_and_gamma(self, p_e_0: float, p_g_0: float, p_e_t: float, p_g_t: float, t_val: float) -> Optional[Tuple[float, float, float]]:
        """
        Calculates S(0), S(T), and Gamma.
        Returns None if signal is non-positive (fail-safe).
        """
        s_0 = p_e_0 - p_g_0
        s_t = p_e_t - p_g_t
        if s_0 <= 0 or s_t <= 0:
            return None
        gamma = -math.log(s_t / s_0) / t_val
        return s_0, s_t, gamma

    def check_model_validity(self, s_0: float, s_t: float, s_2t: float, shots: int) -> bool:
        """
        Model check: S(2T) predicted vs observed under single exponential decay.
        S_pred(2T) = S(T)^2 / S(0)
        Rejects at two-sided alpha = 0.01 (z_crit = 2.576).
        """
        s_pred_2t = (s_t ** 2) / s_0
        se_s2t = math.sqrt(0.5 / shots)
        z = abs(s_2t - s_pred_2t) / se_s2t
        return z <= 2.576

    def analyze_secondary_hypotheses(self, s_metrics: Dict[str, float]) -> Dict:
        """
        Implements Holm-Bonferroni step-down procedure for S1-S6 secondary tests at alpha = 0.01:
        S1: L(tau) decay trend
        S2: Nb vs I contrast at tau_0
        S3: D vs D_fast contrast at tau_0
        S4: Carry-over check (pure vs interleaved Gamma_I)
        S5: Reset residual difference P_G(0) (D vs I)
        S6: Cascade signal difference (P_G(T) - P_G(0)) (D vs I)
        """
        tests = [
            ("S1_trend", s_metrics.get("p_val_s1", 1.0)),
            ("S2_Nb_vs_I", s_metrics.get("p_val_s2", 1.0)),
            ("S3_D_vs_Dfast", s_metrics.get("p_val_s3", 1.0)),
            ("S4_carryover", s_metrics.get("p_val_s4", 1.0)),
            ("S5_reset_residual", s_metrics.get("p_val_s5", 1.0)),
            ("S6_cascade", s_metrics.get("p_val_s6", 1.0)),
        ]
        tests.sort(key=lambda x: x[1])
        m = len(tests)
        holm_results = {}
        for rank, (name, p_val) in enumerate(tests):
            adjusted_alpha = self.alpha / (m - rank)
            significant = p_val < adjusted_alpha
            holm_results[name] = {
                "raw_p": float(p_val),
                "adjusted_alpha": float(adjusted_alpha),
                "significant": bool(significant)
            }
        return holm_results

    def analyze_campaign_blocks(self, block_results: List[Dict[str, float]], model_checks_passed: bool = True) -> Dict:
        """
        Block-level analysis implementing Section 10 decision rules.
        """
        valid_blocks = [b for b in block_results if b.get("L_tau0") is not None]
        n_blocks = len(valid_blocks)

        if n_blocks < 6:
            return {
                "verdict": "ERVENYTELEN",
                "reason": f"Insufficient valid blocks ({n_blocks} < 6 required)",
                "n_blocks": n_blocks
            }

        if not model_checks_passed:
            return {
                "verdict": "ERVENYTELEN",
                "reason": "Model check failed (non-exponential relaxation at 2T)",
                "n_blocks": n_blocks
            }

        l_vals = np.array([b["L_tau0"] for b in valid_blocks])
        mean_l = float(np.mean(l_vals))
        std_l = float(np.std(l_vals, ddof=1))
        se_l = std_l / math.sqrt(n_blocks)

        t_stat, p_val = stats.ttest_1samp(l_vals, 0.0)
        df = n_blocks - 1
        t_crit = stats.t.ppf(1.0 - self.alpha / 2.0, df)
        ci_lower = mean_l - t_crit * se_l
        ci_upper = mean_l + t_crit * se_l

        if p_val < self.alpha and mean_l > 0:
            verdict = "ELOZMENY-LASSIT"
        elif p_val < self.alpha and mean_l < 0:
            verdict = "ELOZMENY-GYORSIT"
        elif ci_lower >= -self.delta_eq and ci_upper <= self.delta_eq:
            verdict = "NULL"
        else:
            verdict = "NEM DONTO"

        return {
            "verdict": verdict,
            "mean_L": mean_l,
            "std_L": std_l,
            "se_L": se_l,
            "p_value": float(p_val),
            "t_statistic": float(t_stat),
            "ci_99": [float(ci_lower), float(ci_upper)],
            "delta_eq": self.delta_eq,
            "n_blocks": n_blocks
        }
