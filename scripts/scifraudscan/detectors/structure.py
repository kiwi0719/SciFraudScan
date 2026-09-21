"""Deterministic relationships between columns.

A constant difference or ratio between two measured variables means one was
computed from the other. That is often legitimate (a derived score, a unit
conversion) -- the finding is that the two columns are not independent
evidence, which matters when both are treated as measurements.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag
from scifraudscan.utils import finite_pair, is_index_like, numeric_frame

MIN_PAIR_N = 8
MIN_SERIES_N = 10


def constant_difference(df: pd.DataFrame, tolerance: float = 1e-9) -> Finding:
    check = "Constant Difference"
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < MIN_PAIR_N or np.std(x) <= tolerance:
            continue
        diff = y - x
        if float(np.nanstd(diff)) <= tolerance:
            matches.append(
                {"left": str(left), "right": str(right), "n": len(x),
                 "difference": round(float(diff[0]), 8)}
            )
    if not matches:
        return clear(check, "No column pair differs by a constant.")
    return flag(
        check,
        "moderate",
        f"{len(matches)} column pairs differ by a fixed constant, e.g. "
        f"'{matches[0]['right']}' = '{matches[0]['left']}' + {matches[0]['difference']}.",
        matches=matches[:20],
        match_count=len(matches),
    )


def constant_ratio(df: pd.DataFrame, tolerance: float = 1e-9) -> Finding:
    check = "Constant Ratio"
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        mask = np.abs(x) > tolerance
        x, y = x[mask], y[mask]
        if len(x) < MIN_PAIR_N or np.std(x) <= tolerance:
            continue
        ratio = y / x
        if float(np.nanstd(ratio)) <= tolerance:
            matches.append(
                {"left": str(left), "right": str(right), "n": len(x),
                 "ratio": round(float(ratio[0]), 8)}
            )
    if not matches:
        return clear(check, "No column pair is related by a constant factor.")
    return flag(
        check,
        "moderate",
        f"{len(matches)} column pairs are related by a fixed factor, e.g. "
        f"'{matches[0]['right']}' = {matches[0]['ratio']} x '{matches[0]['left']}'.",
        matches=matches[:20],
        match_count=len(matches),
    )


def perfect_correlation(df: pd.DataFrame, threshold: float = 0.999) -> Finding:
    check = "Near-Perfect Correlation"
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < MIN_PAIR_N or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
            continue
        r = float(stats.pearsonr(x, y).statistic)
        if abs(r) >= threshold:
            matches.append({"left": str(left), "right": str(right), "n": len(x), "r": round(r, 8)})
    if not matches:
        return clear(check, f"No column pair reaches |r| >= {threshold}.")
    return flag(
        check,
        "moderate",
        f"{len(matches)} column pairs correlate at |r| >= {threshold}, which is higher than "
        "independently measured variables normally reach.",
        matches=matches[:20],
        match_count=len(matches),
    )


def over_regularity(df: pd.DataFrame) -> Finding:
    """Series that advance in near-identical steps.

    Step regularity is measured relative to the spread of the series itself,
    so the test does not depend on the unit the variable is recorded in.
    """
    check = "Over-Regularity"
    num = numeric_frame(df)
    flagged: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < MIN_SERIES_N or is_index_like(values):
            continue  # a row counter has constant steps by construction
        scale = float(np.std(values))
        if scale <= 1e-12:
            continue  # a constant column is a separate, obvious problem
        diffs = np.diff(values)
        step_irregularity = float(np.std(diffs)) / scale
        if step_irregularity < 0.05:
            flagged.append(
                {
                    "column": column if isinstance(column, str) else str(column),
                    "n": len(values),
                    "mean_step": round(float(np.mean(diffs)), 8),
                    "step_irregularity": round(step_irregularity, 6),
                }
            )
    if not flagged:
        return clear(check, "No column advances in near-identical steps.")
    worst = min(flagged, key=lambda item: item["step_irregularity"])
    severity = "high" if float(worst["step_irregularity"]) < 0.01 else "moderate"
    return flag(
        check,
        severity,
        f"{len(flagged)} columns advance in almost constant steps; '{worst['column']}' varies by "
        f"only {float(worst['step_irregularity']):.1%} of its own spread between consecutive rows.",
        columns=flagged[:20],
        column_count=len(flagged),
    )


def run_structure_checks(df: pd.DataFrame) -> list[Finding]:
    return [
        constant_difference(df),
        constant_ratio(df),
        perfect_correlation(df),
        over_regularity(df),
    ]
