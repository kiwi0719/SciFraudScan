"""Distributional checks on a collection of p-values.

These only mean something across a body of results -- a literature, a lab, an
author's output. Run on a single study's handful of p-values they have almost
no power, so each check states the minimum it needs and returns
`not_applicable` below it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag, not_applicable

ALPHA = 0.05
MIN_SIGNIFICANT = 20
MIN_CALIPER = 10
MIN_TOTAL = 20


def load_p_values(p_values_df: pd.DataFrame) -> np.ndarray:
    column = "p" if "p" in p_values_df.columns else p_values_df.columns[0]
    values = pd.to_numeric(p_values_df[column], errors="coerce").dropna().to_numpy(dtype=float)
    return values[(values >= 0) & (values <= 1)]


def threshold_clustering(p_values: np.ndarray) -> Finding:
    """Caliper test: just-significant vs just-not-significant results.

    Under any smooth distribution of true effects the two narrow windows either
    side of .05 should hold roughly equal counts. A surplus on the significant
    side is the signature of results nudged across the line.
    """
    check = "Just-Significant Clustering (caliper test)"
    inside = int(((p_values >= 0.045) & (p_values < 0.050)).sum())
    outside = int(((p_values >= 0.050) & (p_values < 0.055)).sum())
    total = inside + outside
    if total < MIN_CALIPER:
        return not_applicable(
            check,
            f"Only {total} p-values fall in the caliper window [.045, .055); "
            f"{MIN_CALIPER} are needed.",
            inside=inside,
            outside=outside,
        )
    test = stats.binomtest(inside, total, 0.5, alternative="greater")
    p_value = float(test.pvalue)
    ratio = inside / total
    if p_value >= 0.05:
        return clear(
            check,
            f"{inside} p-values just below .05 vs {outside} just above; "
            f"no significant surplus (binomial p={p_value:.3g}).",
            inside=inside,
            outside=outside,
            binomial_p=float(f"{p_value:.6g}"),
        )
    severity = "high" if p_value < 0.001 and ratio > 0.75 else "moderate"
    return flag(
        check,
        severity,
        f"{inside} p-values fall in [.045, .05) against {outside} in [.05, .055); "
        f"surplus on the significant side, binomial p={p_value:.3g}.",
        inside=inside,
        outside=outside,
        ratio_inside=round(ratio, 6),
        binomial_p=float(f"{p_value:.6g}"),
    )


def p_curve_shape(p_values: np.ndarray) -> Finding:
    """Simonsohn, Nelson & Simmons (2014): real effects give a right-skewed p-curve."""
    check = "P-Curve Shape"
    significant = p_values[(p_values > 0) & (p_values < ALPHA)]
    if len(significant) < MIN_SIGNIFICANT:
        return not_applicable(
            check,
            f"Only {len(significant)} significant p-values; {MIN_SIGNIFICANT} are needed for "
            "the p-curve to carry information.",
            significant_count=len(significant),
        )
    low = int((significant < 0.025).sum())
    high = int(len(significant) - low)
    # Left skew (a surplus of .025-.05 results) is the p-hacking signature.
    test = stats.binomtest(high, len(significant), 0.5, alternative="greater")
    p_value = float(test.pvalue)
    if p_value >= 0.05:
        return clear(
            check,
            f"{low} p-values below .025 vs {high} between .025 and .05; "
            f"no significant left skew (binomial p={p_value:.3g}).",
            below_025=low,
            between_025_and_05=high,
            binomial_p=float(f"{p_value:.6g}"),
        )
    return flag(
        check,
        "high" if p_value < 0.001 else "moderate",
        f"P-curve is left-skewed: {high} of {len(significant)} significant p-values sit between "
        f".025 and .05 (binomial p={p_value:.3g}), which is the opposite of what a real effect "
        "produces.",
        below_025=low,
        between_025_and_05=high,
        binomial_p=float(f"{p_value:.6g}"),
    )


def excess_significance(p_values: np.ndarray, assumed_power: float = 0.5) -> Finding:
    """Ioannidis & Trikalinos (2007). The power assumption drives the result."""
    check = "Excess Significance"
    usable = p_values[(p_values > 0) & (p_values <= 1)]
    if len(usable) < MIN_TOTAL:
        return not_applicable(
            check,
            f"Only {len(usable)} p-values; {MIN_TOTAL} are needed.",
            p_value_count=len(usable),
        )
    observed = int((usable < ALPHA).sum())
    expected = len(usable) * assumed_power
    p_value = float(
        stats.binomtest(observed, len(usable), assumed_power, alternative="greater").pvalue
    )
    shared = {
        "observed_significant": observed,
        "expected_significant": round(expected, 3),
        "assumed_power": assumed_power,
        "binomial_p": float(f"{p_value:.6g}"),
        "caveat": (
            "Assumes every test had power "
            f"{assumed_power:.0%}; the result is only as good as that assumption."
        ),
    }
    if p_value >= 0.05:
        return clear(
            check,
            f"{observed} of {len(usable)} results are significant, against {expected:.1f} expected "
            f"at {assumed_power:.0%} power (binomial p={p_value:.3g}).",
            **shared,
        )
    return flag(
        check,
        "moderate",
        f"{observed} of {len(usable)} results are significant, well above the {expected:.1f} "
        f"expected at {assumed_power:.0%} power (binomial p={p_value:.3g}).",
        **shared,
    )


def run_p_value_checks(p_values_df: pd.DataFrame, assumed_power: float = 0.5) -> list[Finding]:
    p_values = load_p_values(p_values_df)
    return [
        threshold_clustering(p_values),
        p_curve_shape(p_values),
        excess_significance(p_values, assumed_power),
    ]
