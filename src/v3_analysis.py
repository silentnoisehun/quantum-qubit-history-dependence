#!/usr/bin/env python3
"""
v3_analysis.py — Strict Pre-registered Analysis Engine for L-Measurement v3.

Revisions (Point 1):
- FAIL-CLOSED: No default counts (no zero-padding or fallbacks).
- Strict validation: Every required circuit must be present with exact shot count,
  non-negative counts, and ones <= shots.
- Missing circuit, corrupted count, or rate calculation failure IMMEDIATELY halts
  the campaign with 'NEM ERTEKELHETO' and blocks CI computation.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from scipy import stats

EXPECTED_CORE_CIRCUITS = {
    # arm, prep, t_name: expected_shots
    ("D", "G", "t0"): 500,
    ("D", "E", "t0"): 500,
    ("D", "G", "tT"): 500,
    ("D", "E", "tT"): 1500,
    ("D", "G", "t2T"): 1000,
    ("D", "E", "t2T"): 1000,
    ("I", "G", "t0"): 500,
    ("I", "E", "t0"): 500,
    ("I", "G", "tT"): 500,
    ("I", "E", "tT"): 1500,
    ("I", "G", "t2T"): 1000,
    ("I", "E", "t2T"): 1000,
}

@dataclass
class SessionRawCounts:
    session_id: int
    # key: (arm, prep, t_name) -> {'ones': int, 'shots': int}
    counts: Dict[Tuple[str, str, str], Dict[str, int]]

@dataclass
class ArmDecayMetrics:
    arm: str
    p_e0: float
    p_g0: float
    s0: float
    var_s0: float
    p_eT: float
    p_gT: float
    sT: float
    var_sT: float
    p_e2T: float
    p_g2T: float
    s2T: float
    var_s2T: float
    gamma: Optional[float]
    gamma_error: Optional[str]
    d2: Optional[float]
    d2_se: Optional[float]
    d2_z: Optional[float]
    d2_p: Optional[float]
    d2_deviation_flag: bool

@dataclass
class SessionMetrics:
    session_id: int
    arm_D: Optional[ArmDecayMetrics]
    arm_I: Optional[ArmDecayMetrics]
    L_s: Optional[float]
    error_note: Optional[str]
    is_valid: bool

@dataclass
class CampaignAnalysisResult:
    n_sessions_total: int
    n_sessions_evaluable: int
    all_evaluable: bool
    l_values: List[float]
    mean_L: Optional[float]
    std_L: Optional[float]
    se_L: Optional[float]
    df: int
    ci99_lower: Optional[float]
    ci99_upper: Optional[float]
    t_stat_vs_0: Optional[float]
    p_val_vs_0: Optional[float]
    t_stat_vs_008: Optional[float]
    p_val_vs_008: Optional[float]
    decision_verdict: str
    decision_explanation: str
    d2_model_check_summary: Dict[str, Any]
    undefined_sessions: List[Dict[str, Any]]

class AnalysisEngineV3:
    def __init__(self, T: float = 220.0e-6):
        self.T = T
        self.alpha_total = 0.01
        self.n_bonf_tests = 32
        self.alpha_bonf = self.alpha_total / self.n_bonf_tests  # 0.0003125

    def validate_session_counts(self, counts: Dict[Tuple[str, str, str], Dict[str, int]]) -> Optional[str]:
        """
        Validates completeness, shot counts, and numerical validity without any fallback defaults.
        """
        for key, exp_shots in EXPECTED_CORE_CIRCUITS.items():
            if key not in counts:
                return f"Missing required circuit: {key}"
            entry = counts[key]
            if not isinstance(entry, dict) or "ones" not in entry or "shots" not in entry:
                return f"Corrupted circuit entry structure for {key}: {entry}"
            shots = entry["shots"]
            ones = entry["ones"]
            if shots != exp_shots:
                return f"Shot count mismatch for {key}: expected {exp_shots}, found {shots}"
            if ones < 0 or ones > shots:
                return f"Invalid ones count for {key}: {ones} out of {shots}"
        return None

    def compute_prob_and_var(self, ones: int, shots: int) -> Tuple[float, float]:
        p = ones / shots
        var_p = (p * (1.0 - p)) / shots
        return p, var_p

    def analyze_arm(self, arm: str, counts: Dict[Tuple[str, str, str], Dict[str, int]]) -> Tuple[Optional[ArmDecayMetrics], Optional[str]]:
        # Strictly require all 6 circuits for the arm
        required = [
            ("G", "t0", 500), ("E", "t0", 500),
            ("G", "tT", 500), ("E", "tT", 1500),
            ("G", "t2T", 1000), ("E", "t2T", 1000)
        ]
        for prep, t_name, exp_shots in required:
            k = (arm, prep, t_name)
            if k not in counts:
                return None, f"Arm {arm} missing circuit {k}"
            if counts[k]["shots"] != exp_shots:
                return None, f"Arm {arm} circuit {k} shots {counts[k]['shots']} != {exp_shots}"
            if counts[k]["ones"] < 0 or counts[k]["ones"] > counts[k]["shots"]:
                return None, f"Arm {arm} circuit {k} invalid ones {counts[k]['ones']}"

        c_e0 = counts[(arm, "E", "t0")]
        c_g0 = counts[(arm, "G", "t0")]
        p_e0, var_e0 = self.compute_prob_and_var(c_e0["ones"], c_e0["shots"])
        p_g0, var_g0 = self.compute_prob_and_var(c_g0["ones"], c_g0["shots"])
        s0 = p_e0 - p_g0
        var_s0 = var_e0 + var_g0

        c_eT = counts[(arm, "E", "tT")]
        c_gT = counts[(arm, "G", "tT")]
        p_eT, var_eT = self.compute_prob_and_var(c_eT["ones"], c_eT["shots"])
        p_gT, var_gT = self.compute_prob_and_var(c_gT["ones"], c_gT["shots"])
        sT = p_eT - p_gT
        var_sT = var_eT + var_gT

        c_e2T = counts[(arm, "E", "t2T")]
        c_g2T = counts[(arm, "G", "t2T")]
        p_e2T, var_e2T = self.compute_prob_and_var(c_e2T["ones"], c_e2T["shots"])
        p_g2T, var_g2T = self.compute_prob_and_var(c_g2T["ones"], c_g2T["shots"])
        s2T = p_e2T - p_g2T
        var_s2T = var_e2T + var_g2T

        # Gamma calculation
        gamma = None
        gamma_err = None
        if s0 <= 0 or sT <= 0:
            gamma_err = f"Non-positive contrast in arm {arm}: s0={s0:.4f}, sT={sT:.4f}"
        else:
            ratio = sT / s0
            if ratio <= 0:
                gamma_err = f"Non-positive contrast ratio in arm {arm}: sT/s0={ratio:.4f}"
            else:
                gamma = -math.log(ratio) / self.T

        # D2 Model check
        d2 = None
        d2_se = None
        d2_z = None
        d2_p = None
        d2_flag = False

        if s0 > 1e-6:
            s_pred_2T = (sT ** 2) / s0
            d2 = s2T - s_pred_2T

            # Delta method:
            grad_2T = 1.0
            grad_T = -2.0 * sT / s0
            grad_0 = (sT / s0) ** 2

            var_d2 = (grad_2T ** 2) * var_s2T + (grad_T ** 2) * var_sT + (grad_0 ** 2) * var_s0
            d2_se = math.sqrt(max(var_d2, 1e-18))
            d2_z = d2 / d2_se
            d2_p = 2.0 * (1.0 - stats.norm.cdf(abs(d2_z)))
            if d2_p < self.alpha_bonf:
                d2_flag = True

        return ArmDecayMetrics(
            arm=arm,
            p_e0=p_e0, p_g0=p_g0, s0=s0, var_s0=var_s0,
            p_eT=p_eT, p_gT=p_gT, sT=sT, var_sT=var_sT,
            p_e2T=p_e2T, p_g2T=p_g2T, s2T=s2T, var_s2T=var_s2T,
            gamma=gamma, gamma_error=gamma_err,
            d2=d2, d2_se=d2_se, d2_z=d2_z, d2_p=d2_p,
            d2_deviation_flag=d2_flag
        ), None

    def analyze_session(self, session: SessionRawCounts) -> SessionMetrics:
        val_err = self.validate_session_counts(session.counts)
        if val_err:
            return SessionMetrics(
                session_id=session.session_id,
                arm_D=None, arm_I=None, L_s=None,
                error_note=val_err, is_valid=False
            )

        arm_d, err_d = self.analyze_arm("D", session.counts)
        if err_d:
            return SessionMetrics(
                session_id=session.session_id,
                arm_D=None, arm_I=None, L_s=None,
                error_note=err_d, is_valid=False
            )

        arm_i, err_i = self.analyze_arm("I", session.counts)
        if err_i:
            return SessionMetrics(
                session_id=session.session_id,
                arm_D=arm_d, arm_I=None, L_s=None,
                error_note=err_i, is_valid=False
            )

        l_s = None
        err = None
        if arm_d.gamma is None:
            err = f"Arm D rate undefined: {arm_d.gamma_error}"
        elif arm_i.gamma is None:
            err = f"Arm I rate undefined: {arm_i.gamma_error}"
        elif arm_d.gamma <= 0 or arm_i.gamma <= 0:
            err = f"Non-positive relaxation rate: gamma_D={arm_d.gamma:.2f}, gamma_I={arm_i.gamma:.2f}"
        else:
            l_s = math.log(arm_i.gamma / arm_d.gamma)

        return SessionMetrics(
            session_id=session.session_id,
            arm_D=arm_d, arm_I=arm_i, L_s=l_s,
            error_note=err, is_valid=(l_s is not None)
        )

    def analyze_campaign(self, sessions: List[SessionRawCounts]) -> CampaignAnalysisResult:
        n_total = len(sessions)
        session_metrics = [self.analyze_session(s) for s in sessions]
        evaluable_sessions = [m for m in session_metrics if m.L_s is not None]
        n_eval = len(evaluable_sessions)
        undefined_list = [
            {"session_id": m.session_id, "error": m.error_note}
            for m in session_metrics if m.L_s is None
        ]

        all_d2_tests = []
        for m in session_metrics:
            if m.arm_D is not None and m.arm_I is not None:
                for arm_m in [m.arm_D, m.arm_I]:
                    all_d2_tests.append({
                        "session_id": m.session_id,
                        "arm": arm_m.arm,
                        "d2": arm_m.d2,
                        "d2_se": arm_m.d2_se,
                        "d2_z": arm_m.d2_z,
                        "d2_p": arm_m.d2_p,
                        "flagged": arm_m.d2_deviation_flag
                    })

        num_flagged_d2 = sum(1 for t in all_d2_tests if t["flagged"])
        d2_summary = {
            "total_checks": len(all_d2_tests),
            "bonferroni_threshold": self.alpha_bonf,
            "num_flagged_deviations": num_flagged_d2,
            "tests": all_d2_tests,
            "diagnostic_note": "Interpretive diagnostic only; no sessions are excluded based on D2."
        }

        # FAIL-CLOSED: If any session is missing, invalid, or undefined, STOP and refuse CI
        if n_eval < n_total or n_total != 16:
            return CampaignAnalysisResult(
                n_sessions_total=n_total,
                n_sessions_evaluable=n_eval,
                all_evaluable=False,
                l_values=[m.L_s for m in evaluable_sessions],
                mean_L=None, std_L=None, se_L=None, df=n_eval - 1 if n_eval > 0 else 0,
                ci99_lower=None, ci99_upper=None,
                t_stat_vs_0=None, p_val_vs_0=None,
                t_stat_vs_008=None, p_val_vs_008=None,
                decision_verdict="NEM ERTEKELHETO",
                decision_explanation=f"A kampány {n_total} alkalmából csak {n_eval} értékelhető hiánytalanul. Hiányos vagy hibás adatoknál elsődleges konfidenciaintervallum nem képezhető.",
                d2_model_check_summary=d2_summary,
                undefined_sessions=undefined_list
            )

        l_vals = [m.L_s for m in evaluable_sessions]
        mean_l = float(np.mean(l_vals))
        std_l = float(np.std(l_vals, ddof=1))
        se_l = std_l / math.sqrt(n_total)
        df = n_total - 1  # 15 for 16 sessions

        t_crit = stats.t.ppf(0.995, df)
        ci_lower = mean_l - t_crit * se_l
        ci_upper = mean_l + t_crit * se_l

        t_stat_0 = (mean_l - 0.0) / se_l
        p_val_0 = 2.0 * (1.0 - stats.t.cdf(abs(t_stat_0), df))

        t_stat_008 = (mean_l - 0.08) / se_l
        p_val_008 = 2.0 * (1.0 - stats.t.cdf(abs(t_stat_008), df))

        contains_0 = (ci_lower <= 0.0 <= ci_upper)
        contains_008 = (ci_lower <= 0.08 <= ci_upper)

        if contains_0 and not contains_008:
            verdict = "OSSZEEGYEZTETHETO 0-VAL, NEM +0.08-CAL"
            explanation = "A 99%-os konfidenciaintervallum tartalmazza a 0.00 értéket, de nem tartalmazza a +0.08 értéket."
        elif contains_008 and not contains_0:
            verdict = "OSSZEEGYEZTETHETO +0.08-CAL, NEM 0-VAL"
            explanation = "A 99%-os konfidenciaintervallum tartalmazza a +0.08 értéket, de nem tartalmazza a 0.00 értéket."
        elif not contains_0 and not contains_008:
            verdict = "EGYIK PONTJOSLATTAL SEM EGYEZTETHETO OSSZE"
            explanation = "A 99%-os konfidenciaintervallum sem a 0.00, sem a +0.08 értéket nem tartalmazza."
        else:
            verdict = "NEM DONTO"
            explanation = "A 99%-os konfidenciaintervallum mindkét pontjóslatot (0.00 és +0.08) tartalmazza."

        return CampaignAnalysisResult(
            n_sessions_total=n_total,
            n_sessions_evaluable=n_eval,
            all_evaluable=True,
            l_values=l_vals,
            mean_L=mean_l,
            std_L=std_l,
            se_L=se_l,
            df=df,
            ci99_lower=ci_lower,
            ci99_upper=ci_upper,
            t_stat_vs_0=t_stat_0,
            p_val_vs_0=p_val_0,
            t_stat_vs_008=t_stat_008,
            p_val_vs_008=p_val_008,
            decision_verdict=verdict,
            decision_explanation=explanation,
            d2_model_check_summary=d2_summary,
            undefined_sessions=[]
        )
