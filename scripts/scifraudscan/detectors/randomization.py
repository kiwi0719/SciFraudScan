"""Carlisle-style baseline balance check for randomized trials.

Carlisle (2017): under real randomization, baseline comparisons between arms
produce p-values that are uniform on [0, 1]. Fabricated data tends to be *too*
balanced, piling p-values up near 1.

The uniformity assumption is only exactly true for independent baseline
variables. Real baseline tables are correlated (height and weight, age and
comorbidity), which makes the KS test anti-conservative, so a flag here is a
reason to look, never a result to report on its own.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import numeric_frame

MIN_VARIABLES = 5
MAX_CATEGORY_LEVELS = 20
ALPHA = 0.01
CAVEAT = (
    "Baseline variables are usually correlated, which violates the independence the "
    "uniformity test assumes; treat a flag as a prompt to inspect, not as evidence."
)


def carlisle_method(df: pd.DataFrame, group_column: str | None = None) -> Finding:
    check = "Carlisle Baseline Balance"
    if not group_column:
        return not_applicable(check, "No group column was supplied.")
    if group_column not in df.columns:
        return not_applicable(check, f"Group column '{group_column}' is not in the dataset.")

    groups = [g for g in df[group_column].dropna().unique()]
    if len(groups) < 2:
        return not_applicable(check, f"Column '{group_column}' has fewer than 2 groups.")

    p_values: list[float] = []
    variables: list[dict[str, object]] = []
    numeric = numeric_frame(df.drop(columns=[group_column], errors="ignore"))

    for column in numeric.columns:
        samples = [
            numeric.loc[df[group_column] == group, column].dropna().to_numpy(dtype=float)
            for group in groups
        ]
        samples = [s for s in samples if len(s) >= 2 and np.std(s) > 0]
        if len(samples) < 2:
            continue
        result = (
            stats.f_oneway(*samples)
            if len(samples) > 2
            else stats.ttest_ind(*samples, equal_var=False)
        )
        p_value = float(result.pvalue)
        if np.isfinite(p_value):
            p_values.append(p_value)
            variables.append(
                {
                    "column": str(column),
                    "test": "anova" if len(samples) > 2 else "welch_t",
                    "p_value": float(f"{p_value:.6g}"),
                }
            )

    for column in df.columns:
        if column == group_column or column in numeric.columns:
            continue
        levels = df[column].nunique(dropna=True)
        # An ID column has one level per row; it is bookkeeping, not a baseline variable.
        if levels > MAX_CATEGORY_LEVELS or levels > len(df) / 10:
            continue
        table = pd.crosstab(df[group_column], df[column])
        if table.shape[0] < 2 or table.shape[1] < 2 or table.to_numpy().sum() < 20:
            continue
        try:
            p_value = float(stats.chi2_contingency(table).pvalue)
        except ValueError:
            continue
        if np.isfinite(p_value):
            p_values.append(p_value)
            variables.append({"column": str(column), "test": "chi2",
                              "p_value": float(f"{p_value:.6g}")})

    if len(p_values) < MIN_VARIABLES:
        return not_applicable(
            check,
            f"Only {len(p_values)} usable baseline variables; {MIN_VARIABLES} are needed.",
            group_column=group_column,
            variables=variables,
        )

    p = np.array(p_values)
    ks_p = float(stats.kstest(p, "uniform").pvalue)
    # Fabricated balance pushes baseline p-values toward 1, so a one-sided test
    # in that direction has more power than the two-sided test against it.
    too_balanced_p = float(stats.kstest(p, "uniform", alternative="less").pvalue)
    too_similar = int((p > 0.95).sum())
    too_different = int((p < 0.05).sum())
    shared = {
        "group_column": group_column,
        "variable_count": len(p_values),
        "ks_p_value": float(f"{ks_p:.6g}"),
        "too_balanced_p_value": float(f"{too_balanced_p:.6g}"),
        "mean_baseline_p": round(float(p.mean()), 6),
        "count_above_0_95": too_similar,
        "count_below_0_05": too_different,
        "variables": variables[:50],
        "caveat": CAVEAT,
    }
    best_p = min(ks_p, too_balanced_p)
    if best_p >= ALPHA:
        return clear(
            check,
            f"{len(p_values)} baseline p-values are consistent with uniformity "
            f"(two-sided KS p={ks_p:.3g}, too-balanced p={too_balanced_p:.3g}).",
            **shared,
        )
    if too_balanced_p < ks_p:
        detail = (
            f"they sit higher than randomization produces (one-sided KS p={too_balanced_p:.3g}), "
            "the pattern left by baselines that were balanced after the fact"
        )
    else:
        detail = f"they depart from uniformity in both directions (KS p={ks_p:.3g})"
    return flag(
        check,
        "high" if best_p < 0.001 else "moderate",
        f"{len(p_values)} baseline p-values are not uniform: {detail}; "
        f"{too_similar} are above .95 and {too_different} below .05.",
        **shared,
    )


def run_randomization_checks(df: pd.DataFrame, group_column: str | None = None) -> list[Finding]:
    return [carlisle_method(df, group_column)]
