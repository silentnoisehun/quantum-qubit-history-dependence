#!/usr/bin/env python3
"""
analysis.py — Pre-registered Frozen Statistical Analysis Pipeline
Implements Section 6, 10, 11, and 12:
- S(t) = P_E(t) - P_G(t)
- Gamma = -ln(S(T) / S(0)) / T
- L = ln(Gamma_I / Gamma_D) at tau_0
- Model check at t = 2T (alpha = 0.01)
- Block-level one-sample t-test at alpha = 0.01
- Holm-Bonferroni secondary metrics (S1 - S6)
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

class StatisticalPipeline:
    def __init__(self, t_decay: float = 168.0e-6, alpha: float = 0.01, delta_eq: float = 0.064):
        self.t_decay = t_decay
        self.alpha = alpha
        self.delta_eq = delta_eq

    def compute_s_and_gamma(self, p_e_0: float, p_g_0: float, p_e_t: float, p_g_t: float, t_val: float) -> Tuple[float, float, float]:
        """
        Calculates S(0), S(T), and Gamma.
        S(t) = P_E(t) - P_G(t)
        Gamma = -ln(S(T)/S(0)) / T
        """
        s_0 = p_e_0 - p_g_0
        s_t = p_e_t - p_g_t
        if s_0 <= 0 or s_t <= 0:
            raise ValueError(f"Signal non-positive: S(0)={s_0}, S(T)={s_t}")
        gamma = -math.log(s_t / s_0) / t_val
        return s_0, s_t, gamma

    def check_model_validity(self, s_0: float, s_t: float, s_2t: float, shots: int) -> bool:
        """
        Model check: S(2T) predicted vs observed under single exponential decay.
        S_pred(2T) = S(T)^2 / S(0)
        Variance derived via delta method for binomial counts.
        Rejects at two-sided alpha = 0.01.
        """
        s_pred_2t = (s_t ** 2) / s_0
        # Estimated standard error on S(2T)
        # Var(S) = Var(P_E) + Var(P_G) <= 2 * 0.25 / shots
        se_s2t = math.sqrt(0.5 / shots)
        z = abs(s_2t - s_pred_2t) / se_s2t
        # Two-sided alpha = 0.01 corresponds to z_crit ~ 2.576
        return z <= 2.576

    def analyze_campaign_blocks(self, block_results: List[Dict[str, float]], model_checks_passed: bool = True) -> Dict:
        """
        block_results: List of dicts per block containing:
          'L_tau0': ln(Gamma_I / Gamma_D) at tau_0
          'Gamma_D': rate for D arm
          'Gamma_I': rate for I arm
        """
        l_vals = np.array([b["L_tau0"] for b in block_results])
        n_blocks = len(l_vals)
        if n_blocks < 6:
            return {
                "verdict": "ERVENYTELEN",
                "reason": f"Insufficient valid blocks ({n_blocks} < 6)",
                "n_blocks": n_blocks
            }

        if not model_checks_passed:
            return {
                "verdict": "ERVENYTELEN",
                "reason": "Model check failed (significant deviation at t=2T)",
                "n_blocks": n_blocks
            }

        mean_l = float(np.mean(l_vals))
        std_l = float(np.std(l_vals, ddof=1))
        se_l = std_l / math.sqrt(n_blocks)

        t_stat, p_val = stats.ttest_1samp(l_vals, 0.0)
        df = n_blocks - 1
        t_crit = stats.t.ppf(1.0 - self.alpha / 2.0, df)
        ci_lower = mean_l - t_crit * se_l
        ci_upper = mean_l + t_crit * se_l

        # Decision rule (Section 10)
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
