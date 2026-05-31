from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from research_integrity_screen.models import Finding


def load_p_values(p_values_df: pd.DataFrame) -> np.ndarray:
    if "p" in p_values_df.columns:
        values = p_values_df["p"]
    else:
        values = p_values_df.iloc[:, 0]
    p = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    return p[(p >= 0) & (p <= 1)]


def p_curve_shape(p_values: np.ndarray) -> Finding:
    significant = p_values[(p_values > 0) & (p_values < 0.05)]
    if len(significant) < 5:
        return Finding("P-Curve", "Pass", 0, "Fewer than 5 significant p-values available.")
    left = int((significant < 0.025).sum())
    right = int(((significant >= 0.025) & (significant < 0.05)).sum())
    # Real evidential value tends to be right-skewed toward smaller p-values.
    binom_p = float(stats.binomtest(left, len(significant), 0.5, alternative="less").pvalue)
    score = min(100.0, (1.0 - (left / len(significant))) * 70 + (binom_p < 0.05) * 30)
    return Finding(
        "P-Curve",
        _status(score),
        score,
        f"{left} p-values are < .025 and {right} are between .025 and .05.",
        {"significant_count": int(len(significant)), "binomial_p": round(binom_p, 6)},
    )


def threshold_clustering(p_values: np.ndarray) -> Finding:
    near = int(((p_values >= 0.045) & (p_values < 0.05)).sum())
    sig = int(((p_values > 0) & (p_values < 0.05)).sum())
    rate = near / sig if sig else 0.0
    score = min(100.0, rate * 180)
    return Finding(
        "P-Value Threshold Clustering",
        _status(score),
        score,
        f"{near} of {sig} significant p-values fall in [0.045, 0.05).",
        {"near_threshold": near, "significant_count": sig, "rate": round(rate, 6)},
    )


def excess_significance(p_values: np.ndarray, expected_power: float = 0.5) -> Finding:
    usable = p_values[(p_values > 0) & (p_values <= 1)]
    if len(usable) < 5:
        return Finding("Excess Significance", "Pass", 0, "Fewer than 5 p-values available.")
    observed = int((usable < 0.05).sum())
    expected = len(usable) * expected_power
    p = float(stats.binomtest(observed, len(usable), expected_power, alternative="greater").pvalue)
    ratio = observed / expected if expected else 0.0
    score = min(100.0, max(0.0, ratio - 1.0) * 60 + (p < 0.05) * 35)
    return Finding(
        "Excess Significance",
        _status(score),
        score,
        f"{observed} of {len(usable)} p-values are significant; expected about {expected:.1f}.",
        {"observed": observed, "expected": round(expected, 3), "binomial_p": round(p, 6)},
    )


def run_p_value_checks(p_values_df: pd.DataFrame) -> list[Finding]:
    p_values = load_p_values(p_values_df)
    return [
        threshold_clustering(p_values),
        p_curve_shape(p_values),
        excess_significance(p_values),
    ]


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
