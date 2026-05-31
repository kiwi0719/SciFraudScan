from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import finite_pair, numeric_frame


def constant_difference(df: pd.DataFrame, tolerance: float = 1e-9) -> Finding:
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < 4:
            continue
        diff = y - x
        if float(np.nanstd(diff)) <= tolerance:
            matches.append({"left": str(left), "right": str(right), "difference": round(float(diff[0]), 8)})
    score = min(100.0, len(matches) * 45)
    return Finding(
        "Constant Difference",
        _status(score),
        score,
        f"{len(matches)} column pairs have a constant difference.",
        {"matches": matches[:20], "match_count": len(matches)},
    )


def constant_ratio(df: pd.DataFrame, tolerance: float = 1e-9) -> Finding:
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        mask = np.abs(x) > tolerance
        x, y = x[mask], y[mask]
        if len(x) < 4:
            continue
        ratio = y / x
        if float(np.nanstd(ratio)) <= tolerance:
            matches.append({"left": str(left), "right": str(right), "ratio": round(float(ratio[0]), 8)})
    score = min(100.0, len(matches) * 45)
    return Finding(
        "Constant Ratio",
        _status(score),
        score,
        f"{len(matches)} column pairs have a constant ratio.",
        {"matches": matches[:20], "match_count": len(matches)},
    )


def perfect_correlation(df: pd.DataFrame, threshold: float = 0.995) -> Finding:
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < 4 or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
            continue
        r = float(stats.pearsonr(x, y).statistic)
        if abs(r) >= threshold:
            matches.append({"left": str(left), "right": str(right), "r": round(r, 8)})
    score = min(100.0, len(matches) * 30)
    return Finding(
        "Perfect Correlation",
        _status(score),
        score,
        f"{len(matches)} column pairs have |r| >= {threshold}.",
        {"matches": matches[:20], "match_count": len(matches)},
    )


def over_regularity(df: pd.DataFrame) -> Finding:
    num = numeric_frame(df)
    flagged: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < 6 or np.mean(np.abs(values)) == 0:
            continue
        diffs = np.diff(values)
        if len(diffs) < 3:
            continue
        cv = float(np.std(values) / (abs(np.mean(values)) + 1e-12))
        diff_cv = float(np.std(diffs) / (abs(np.mean(diffs)) + 1e-12)) if np.mean(diffs) else float(np.std(diffs))
        if cv < 0.02 or diff_cv < 0.02:
            flagged.append({"column": str(column), "cv": round(cv, 6), "diff_cv": round(diff_cv, 6)})
    score = min(100.0, len(flagged) * 35)
    return Finding(
        "Over-Regularity",
        _status(score),
        score,
        f"{len(flagged)} numeric columns have unusually low variation or overly regular steps.",
        {"columns": flagged[:20], "column_count": len(flagged)},
    )


def run_structure_checks(df: pd.DataFrame) -> list[Finding]:
    return [
        constant_difference(df),
        constant_ratio(df),
        perfect_correlation(df),
        over_regularity(df),
    ]


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
