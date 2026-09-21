"""Duplicated and derived records.

Duplication is the one family here that can be close to conclusive: two
columns holding the same multiset, or one being an exact linear rescaling of
another, does not happen by chance in independently measured data. Benign
explanations exist -- a unit conversion stored twice, a merge artefact -- so
these are reported as findings to explain, not as verdicts.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import finite_pair, numeric_frame

MIN_PAIR_N = 8
MIN_NEAR_DUPLICATE_COLUMNS = 4


def exact_duplicates(df: pd.DataFrame) -> Finding:
    check = "Exact Duplicate Rows"
    if df.empty:
        return clear(check, "The dataset has no rows.")
    mask = df.duplicated(keep=False)
    count = int(mask.sum())
    if count == 0:
        return clear(check, "No row is repeated in full.")
    rate = count / len(df)
    severity = "high" if rate > 0.10 else "moderate" if rate > 0.02 else "low"
    return flag(
        check,
        severity,
        f"{count} of {len(df)} rows ({rate:.1%}) are part of an exactly repeated row.",
        duplicate_rows=count,
        duplicate_rate=round(rate, 6),
        example_row_indices=[int(i) for i in df.index[mask][:20]],
    )


def near_duplicate_rows(
    df: pd.DataFrame, threshold: float = 0.999, max_rows: int = 2000
) -> Finding:
    check = "Near Duplicate Rows"
    num = numeric_frame(df).dropna(axis=0, how="any")
    if num.shape[1] < MIN_NEAR_DUPLICATE_COLUMNS:
        return Finding(
            check,
            "not_applicable",
            f"Needs at least {MIN_NEAR_DUPLICATE_COLUMNS} complete numeric columns; "
            f"found {num.shape[1]}. With fewer columns near-identical rows are ordinary.",
        )
    if len(num) < 2:
        return Finding(check, "not_applicable", "Fewer than 2 complete numeric rows.")

    sampled = num.head(max_rows)
    values = sampled.to_numpy(dtype=float)
    spread = values.std(axis=0)
    spread[spread == 0] = 1.0
    standardized = (values - values.mean(axis=0)) / spread
    norms = np.linalg.norm(standardized, axis=1)
    keep = norms > 1e-12
    standardized = standardized[keep] / norms[keep, None]
    if len(standardized) < 2:
        return Finding(check, "not_applicable", "Rows carry no variation once standardized.")

    similarity = standardized @ standardized.T
    rows, cols = np.triu_indices_from(similarity, k=1)
    scores = similarity[rows, cols]
    hits = np.flatnonzero(scores >= threshold)
    index = sampled.index[keep]

    # How many such pairs arise from rows assembled at random out of these very
    # columns? Shuffling each column independently keeps every value and every
    # marginal distribution and destroys only the pairing between them.
    generator = np.random.default_rng(0)
    null_counts = []
    for _ in range(10):
        shuffled = np.column_stack(
            [generator.permutation(standardized[:, j]) for j in range(standardized.shape[1])]
        )
        norms_s = np.linalg.norm(shuffled, axis=1)
        keep_s = norms_s > 1e-12
        unit = shuffled[keep_s] / norms_s[keep_s, None]
        sim = unit @ unit.T
        null_counts.append(int((sim[np.triu_indices_from(sim, k=1)] >= threshold).sum()))
    expected = float(np.mean(null_counts))

    if len(hits) and len(hits) <= max(expected, 1) * 2:
        return clear(
            check,
            f"{len(hits)} near-identical row pairs, against {expected:.1f} expected from "
            "rows assembled at random out of these same columns. Ordinary for data "
            "with this many repeated values.",
            pair_count=len(hits),
            expected_when_shuffled=round(expected, 2),
            rows_evaluated=len(standardized),
        )
    if len(hits) == 0:
        return clear(
            check,
            f"No row pair reaches cosine similarity {threshold} "
            f"across {len(standardized)} standardized rows.",
            rows_evaluated=len(standardized),
            max_similarity=round(float(scores.max()), 6) if len(scores) else None,
        )
    pairs = [
        {
            "row_a": int(index[rows[i]]),
            "row_b": int(index[cols[i]]),
            "cosine": round(float(scores[i]), 8),
        }
        for i in hits[:20]
    ]
    severity = "high" if len(hits) > len(standardized) * 0.05 else "moderate"
    return flag(
        check,
        severity,
        f"{len(hits)} row pairs are near-identical across all numeric columns "
        f"(cosine >= {threshold}).",
        pair_count=len(hits),
        rows_evaluated=len(standardized),
        pairs=pairs,
    )


def linear_transformation_duplicates(df: pd.DataFrame, r2_threshold: float = 0.9999) -> Finding:
    check = "Linear Transformation Duplicate"
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < MIN_PAIR_N or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
            continue
        slope, intercept = np.polyfit(x, y, 1)
        residual = float(np.sum((y - (slope * x + intercept)) ** 2))
        total = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - residual / total if total else 0.0
        if r2 >= r2_threshold:
            matches.append(
                {
                    "left": str(left),
                    "right": str(right),
                    "n": len(x),
                    "r_squared": round(float(r2), 10),
                    "slope": round(float(slope), 8),
                    "intercept": round(float(intercept), 8),
                }
            )
    if not matches:
        return clear(check, "No numeric column is a linear rescaling of another.")
    return flag(
        check,
        "high",
        f"{len(matches)} column pairs satisfy y = ax + b almost exactly "
        f"(R^2 >= {r2_threshold}), e.g. '{matches[0]['left']}' -> '{matches[0]['right']}'.",
        matches=matches[:20],
        match_count=len(matches),
    )


def permutation_duplicates(df: pd.DataFrame) -> Finding:
    check = "Permutation Duplicate"
    num = numeric_frame(df)
    matches: list[dict[str, object]] = []
    for left, right in combinations(num.columns, 2):
        x, y = finite_pair(num[left], num[right])
        if len(x) < MIN_PAIR_N:
            continue
        if np.array_equal(np.sort(x), np.sort(y)) and not np.array_equal(x, y):
            matches.append({"left": str(left), "right": str(right), "n": len(x)})
    if not matches:
        return clear(check, "No two numeric columns hold the same values in a different order.")
    return flag(
        check,
        "high",
        f"{len(matches)} column pairs contain an identical multiset of values in a different "
        f"order, e.g. '{matches[0]['left']}' and '{matches[0]['right']}'.",
        matches=matches[:20],
        match_count=len(matches),
    )


def _count_repeated_blocks(
    columns: list[tuple[str, np.ndarray]], window: int
) -> tuple[int, list[dict[str, object]]]:
    seen: dict[tuple[float, ...], tuple[str, int]] = {}
    matches: list[dict[str, object]] = []
    for name, values in columns:
        for start in range(len(values) - window + 1):
            block = values[start : start + window]
            if np.std(block) <= 1e-12:
                continue  # a run of one repeated value is a different finding
            key = tuple(np.round(block, 10).tolist())
            previous = seen.get(key)
            if previous is None:
                seen[key] = (name, start)
            elif previous[0] != name or abs(previous[1] - start) >= window:
                matches.append(
                    {
                        "column": name,
                        "start": start,
                        "previous_column": previous[0],
                        "previous_start": previous[1],
                        "length": window,
                    }
                )
    return len(matches), matches


def partial_duplicate_windows(
    df: pd.DataFrame, window: int = 6, permutations: int = 25, seed: int = 0
) -> Finding:
    """Runs of consecutive values that reappear elsewhere, against chance.

    A column with few distinct values repeats short runs constantly, so the
    raw count says more about the column's diversity than about its
    provenance: counting them fired on 70% of ordinary datasets. The count is
    now compared against the same count after shuffling each column, which
    destroys the ordering while keeping every value exactly as it was.
    """
    check = "Repeated Value Blocks"
    num = numeric_frame(df)
    columns = []
    sorted_out = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < window or np.std(values) <= 1e-12:
            continue
        # A sorted column repeats runs for a reason that has nothing to do with
        # provenance, and shuffling it makes any permutation test significant.
        if np.all(np.diff(values) >= 0) or np.all(np.diff(values) <= 0):
            sorted_out.append(str(column))
            continue
        columns.append((str(column), values))
    if not columns:
        reason = (
            f"Every numeric column is sorted ({len(sorted_out)} of them), so repeated runs "
            "carry no information about how the data was assembled."
            if sorted_out
            else f"No numeric column has {window} varying values."
        )
        return not_applicable(check, reason, sorted_columns=sorted_out[:20])

    observed, matches = _count_repeated_blocks(columns, window)
    rng = np.random.default_rng(seed)
    null = np.array(
        [
            _count_repeated_blocks(
                [(name, rng.permutation(values)) for name, values in columns], window
            )[0]
            for _ in range(permutations)
        ],
        dtype=float,
    )
    exceedances = int((null >= observed).sum())
    p_value = (exceedances + 1) / (permutations + 1)
    shared = {
        "window": window,
        "observed_blocks": observed,
        "expected_blocks_when_shuffled": round(float(null.mean()), 2),
        "permutation_p_value": round(p_value, 4),
        "permutations": permutations,
        "sorted_columns_excluded": sorted_out[:20],
    }
    if observed == 0:
        return clear(check, f"No run of {window} consecutive values repeats elsewhere.", **shared)
    if p_value > 0.05:
        return clear(
            check,
            f"{observed} repeated runs of {window} values, against "
            f"{null.mean():.1f} expected from these columns' own values in random order "
            f"(permutation p={p_value:.3g}). Ordinary for data this granular.",
            **shared,
        )
    return flag(
        check,
        "high" if observed > 3 * max(null.mean(), 1) else "moderate",
        f"{observed} runs of {window} consecutive values reappear elsewhere, against "
        f"{null.mean():.1f} expected when the same values are shuffled "
        f"(permutation p={p_value:.3g}).",
        matches=matches[:20],
        match_count=observed,
        **shared,
    )


def run_duplication_checks(df: pd.DataFrame) -> list[Finding]:
    return [
        exact_duplicates(df),
        near_duplicate_rows(df),
        linear_transformation_duplicates(df),
        permutation_duplicates(df),
        partial_duplicate_windows(df),
    ]
