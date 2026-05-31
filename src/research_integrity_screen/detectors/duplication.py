from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import finite_pair, numeric_frame


def exact_duplicates(df: pd.DataFrame) -> Finding:
    duplicate_count = int(df.duplicated(keep=False).sum())
    rate = duplicate_count / len(df) if len(df) else 0.0
    score = min(100.0, rate * 250)
    return Finding(
        check="Exact Duplicate Rows",
        status=_status(score),
        score=score,
        message=f"{duplicate_count} rows participate in exact duplicates.",
        details={"duplicate_rows": duplicate_count, "duplicate_rate": round(rate, 6)},
    )


def near_duplicate_rows(df: pd.DataFrame, threshold: float = 0.995, max_rows: int = 500) -> Finding:
    num = numeric_frame(df).dropna(axis=0, how="any")
    if len(num) < 2:
        return Finding("Near Duplicate Rows", "Pass", 0, "Not enough complete numeric rows.")
    sampled = num.head(max_rows)
    values = sampled.to_numpy(dtype=float)
    std = values.std(axis=0)
    std[std == 0] = 1.0
    values = (values - values.mean(axis=0)) / std
    norms = np.linalg.norm(values, axis=1)
    valid = norms > 0
    values = values[valid]
    if len(values) < 2:
        return Finding("Near Duplicate Rows", "Pass", 0, "Rows have insufficient variation.")
    normalized = values / np.linalg.norm(values, axis=1, keepdims=True)
    similarity = normalized @ normalized.T
    upper = similarity[np.triu_indices_from(similarity, k=1)]
    pair_count = int((upper >= threshold).sum())
    max_similarity = float(upper.max()) if len(upper) else 0.0
    score = min(100.0, pair_count * 10 + max(0.0, max_similarity - 0.98) * 500)
    return Finding(
        check="Near Duplicate Rows",
        status=_status(score),
        score=score,
        message=f"{pair_count} numeric row pairs have cosine similarity >= {threshold}.",
        details={
            "pair_count": pair_count,
            "max_similarity": round(max_similarity, 6),
            "rows_evaluated": int(len(sampled)),
        },
    )


def linear_transformation_duplicates(df: pd.DataFrame, r2_threshold: float = 0.999) -> Finding:
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < 4 or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
            continue
        slope, intercept = np.polyfit(x, y, 1)
        predicted = slope * x + intercept
        ss_res = float(np.sum((y - predicted) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
        if r2 >= r2_threshold:
            matches.append(
                {
                    "left": str(left),
                    "right": str(right),
                    "r2": round(float(r2), 8),
                    "slope": round(float(slope), 8),
                    "intercept": round(float(intercept), 8),
                }
            )
    score = min(100.0, len(matches) * 45)
    return Finding(
        check="Linear Transformation Duplicate",
        status=_status(score),
        score=score,
        message=f"{len(matches)} column pairs look like y = ax + b copies.",
        details={"matches": matches[:20], "match_count": len(matches)},
    )


def permutation_duplicates(df: pd.DataFrame) -> Finding:
    num = numeric_frame(df)
    matches: list[dict[str, str]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < 4:
            continue
        if np.array_equal(np.sort(x), np.sort(y)) and not np.array_equal(x, y):
            matches.append({"left": str(left), "right": str(right)})
    score = min(100.0, len(matches) * 40)
    return Finding(
        check="Permutation Duplicate",
        status=_status(score),
        score=score,
        message=f"{len(matches)} numeric column pairs contain the same multiset in different order.",
        details={"matches": matches[:20], "match_count": len(matches)},
    )


def partial_duplicate_windows(df: pd.DataFrame, window: int = 4) -> Finding:
    num = numeric_frame(df)
    seen: dict[tuple[float, ...], tuple[str, int]] = {}
    matches: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < window:
            continue
        for start in range(0, len(values) - window + 1):
            key = tuple(np.round(values[start : start + window], 8))
            previous = seen.get(key)
            if previous and (previous[0] != str(column) or abs(previous[1] - start) >= window):
                matches.append(
                    {
                        "column": str(column),
                        "start": start,
                        "previous_column": previous[0],
                        "previous_start": previous[1],
                    }
                )
            else:
                seen[key] = (str(column), start)
    score = min(100.0, len(matches) * 12)
    return Finding(
        check="Partial Duplicate Windows",
        status=_status(score),
        score=score,
        message=f"{len(matches)} repeated numeric windows of length {window} found.",
        details={"window": window, "matches": matches[:20], "match_count": len(matches)},
    )


def run_duplication_checks(df: pd.DataFrame) -> list[Finding]:
    return [
        exact_duplicates(df),
        near_duplicate_rows(df),
        linear_transformation_duplicates(df),
        permutation_duplicates(df),
        partial_duplicate_windows(df),
    ]


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
