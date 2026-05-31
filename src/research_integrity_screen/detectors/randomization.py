from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import numeric_frame


def carlisle_method(df: pd.DataFrame, group_column: str | None = None) -> Finding:
    if not group_column:
        return Finding("Carlisle Randomization", "Pass", 0, "No group column supplied; Carlisle check skipped.")
    if group_column not in df.columns:
        return Finding(
            "Carlisle Randomization",
            "Pass",
            0,
            f"Group column '{group_column}' was not found; Carlisle check skipped.",
        )

    groups = df[group_column].dropna().unique()
    if len(groups) < 2:
        return Finding("Carlisle Randomization", "Pass", 0, "Fewer than 2 groups available.")

    p_values: list[float] = []
    variables: list[dict[str, object]] = []
    num = numeric_frame(df.drop(columns=[group_column], errors="ignore"))
    for column in num.columns:
        samples = [
            num.loc[df[group_column] == group, column].dropna().to_numpy(dtype=float)
            for group in groups
        ]
        samples = [sample for sample in samples if len(sample) >= 2]
        if len(samples) < 2:
            continue
        p_value = float(stats.f_oneway(*samples).pvalue) if len(samples) > 2 else float(stats.ttest_ind(*samples, equal_var=False).pvalue)
        if np.isfinite(p_value):
            p_values.append(p_value)
            variables.append({"column": str(column), "p_value": round(p_value, 8)})

    for column in df.columns:
        if column == group_column or column in num.columns:
            continue
        table = pd.crosstab(df[group_column], df[column])
        if table.shape[0] >= 2 and table.shape[1] >= 2 and table.to_numpy().sum() >= 10:
            try:
                p_value = float(stats.chi2_contingency(table).pvalue)
            except ValueError:
                continue
            p_values.append(p_value)
            variables.append({"column": str(column), "p_value": round(p_value, 8)})

    if len(p_values) < 3:
        return Finding("Carlisle Randomization", "Pass", 0, "Fewer than 3 baseline variables available.")

    p = np.array(p_values)
    ks_p = float(stats.kstest(p, "uniform").pvalue)
    too_similar = int((p > 0.95).sum())
    too_different = int((p < 0.05).sum())
    extreme_rate = (too_similar + too_different) / len(p)
    score = min(100.0, -np.log10(max(ks_p, 1e-12)) * 20 + extreme_rate * 80)
    return Finding(
        "Carlisle Randomization",
        _status(score),
        float(score),
        f"Baseline p-values uniformity KS p={ks_p:.4g}; {too_similar} are >.95 and {too_different} are <.05.",
        {
            "group_column": group_column,
            "variable_count": len(p_values),
            "ks_p_value": round(ks_p, 8),
            "too_similar_count": too_similar,
            "too_different_count": too_different,
            "variables": variables[:30],
        },
    )


def run_randomization_checks(df: pd.DataFrame, group_column: str | None = None) -> list[Finding]:
    return [carlisle_method(df, group_column)]


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
