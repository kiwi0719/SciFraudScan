"""Digit-level authenticity checks.

Both digit tests are run per column, never on all columns pooled together:
pooling variables that carry different units produces a digit distribution
with no expected shape, so any deviation from it is meaningless.

Benford's law in particular is easy to misapply. It describes data produced by
multiplicative processes and spanning many orders of magnitude -- financial
totals, population counts. Ordinary bounded measurements do not follow it even
when they are entirely honest: a Gamma-distributed clinical variable covering
two orders of magnitude fails the test routinely. So the check demands a wide
spread before it will run at all, and never raises more than a moderate flag.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import (
    cramers_v,
    is_index_like,
    numeric_frame,
    order_of_magnitude_span,
    terminal_digits,
)

# Nigrini (2012) mean absolute deviation cut-offs for the first digit.
MAD_MARGINAL = 0.012
MAD_NONCONFORM = 0.015
BENFORD_MIN_N = 150
BENFORD_MIN_SPAN = 3.0
DIGIT_MIN_N = 100
ALPHA = 0.01

BENFORD_EXPECTED = np.array([math.log10(1 + 1 / digit) for digit in range(1, 10)])


def benford_law(df: pd.DataFrame) -> Finding:
    check = "Benford First Digit"
    eligible: list[tuple[str, np.ndarray]] = []
    skipped: list[dict[str, object]] = []
    for column, raw in _columns(df):
        values = raw[raw != 0]
        span = order_of_magnitude_span(values)
        if len(values) < BENFORD_MIN_N or span < BENFORD_MIN_SPAN:
            skipped.append(
                {"column": column, "n": len(values), "order_of_magnitude_span": round(span, 3)}
            )
            continue
        eligible.append((column, values))

    if not eligible:
        return not_applicable(
            check,
            f"No column has both n >= {BENFORD_MIN_N} and a spread of >= {BENFORD_MIN_SPAN} "
            "orders of magnitude, which Benford's law requires.",
            skipped_columns=skipped[:20],
        )

    results = [_benford_column(column, values) for column, values in eligible]
    flagged = [r for r in results if r["mad"] > MAD_NONCONFORM and r["p_value"] < ALPHA]
    if not flagged:
        return clear(
            check,
            f"{len(results)} eligible columns conform to Benford's law "
            f"(MAD <= {MAD_NONCONFORM} or chi-square p >= {ALPHA}).",
            columns=results,
        )
    worst = max(flagged, key=lambda r: r["mad"])
    # Capped at moderate on purpose: non-conformity is common in honest
    # measurement data, so this is never strong evidence on its own.
    return flag(
        check,
        "moderate",
        f"{len(flagged)} of {len(results)} eligible columns deviate from Benford's law; "
        f"worst is '{worst['column']}' with MAD={worst['mad']:.4f} (p={worst['p_value']:.3g}). "
        "Benford non-conformity is weak evidence unless the variable is known to be "
        "scale-invariant.",
        flagged_columns=flagged,
        evaluated_columns=results,
        mad_thresholds={"marginal": MAD_MARGINAL, "nonconformity": MAD_NONCONFORM},
    )


def digit_preference(df: pd.DataFrame) -> Finding:
    check = "Terminal Digit Preference"
    results: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for column, values in _columns(df):
        digits = terminal_digits(values)
        if len(digits) < DIGIT_MIN_N:
            skipped.append({"column": column, "n": len(digits)})
            continue
        results.append(_digit_column(column, digits))

    if not results:
        return not_applicable(
            check,
            f"No column has {DIGIT_MIN_N} or more usable terminal digits.",
            skipped_columns=skipped[:20],
        )

    flagged = [r for r in results if r["p_value"] < ALPHA and r["cramers_v"] >= 0.10]
    if not flagged:
        return clear(
            check,
            f"Terminal digits in {len(results)} columns are consistent with a "
            "uniform distribution.",
            columns=results,
        )
    worst = max(flagged, key=lambda r: r["cramers_v"])
    v = float(worst["cramers_v"])
    severity = "high" if v >= 0.30 else "moderate" if v >= 0.20 else "low"
    return flag(
        check,
        severity,
        f"{len(flagged)} of {len(results)} columns show terminal-digit preference; "
        f"worst is '{worst['column']}' (digit {worst['top_digit']} at "
        f"{float(worst['top_rate']):.1%}, Cramer's V={v:.3f}).",
        flagged_columns=flagged,
        evaluated_columns=results,
    )


def repeated_increments(df: pd.DataFrame, min_n: int = 20) -> Finding:
    """Columns whose consecutive differences repeat far more than real data would."""
    check = "Repeated Increments"
    results: list[dict[str, object]] = []
    for column, values in _columns(df):
        if len(values) < min_n:
            continue
        # Integer-valued measures repeat their increments for ordinary reasons.
        if np.allclose(values, np.rint(values)):
            continue
        diffs = np.round(np.diff(values), 10)
        if len(diffs) < min_n - 1 or np.allclose(values, values[0]):
            continue
        unique_rate = len(set(diffs.tolist())) / len(diffs)
        if unique_rate < 0.25:
            results.append(
                {
                    "column": column,
                    "n": len(values),
                    "distinct_increment_rate": round(float(unique_rate), 6),
                    "most_common_increment": float(pd.Series(diffs).mode().iloc[0]),
                }
            )

    if not results:
        return clear(check, "No column is built from a small set of repeated increments.")
    worst = min(results, key=lambda r: r["distinct_increment_rate"])
    rate = float(worst["distinct_increment_rate"])
    severity = "high" if rate < 0.05 else "moderate" if rate < 0.15 else "low"
    return flag(
        check,
        severity,
        f"{len(results)} columns advance by a small set of repeated steps; "
        f"'{worst['column']}' has only {rate:.1%} distinct increments.",
        columns=results,
    )


def run_authenticity_checks(df: pd.DataFrame) -> list[Finding]:
    return [benford_law(df), digit_preference(df), repeated_increments(df)]


def _columns(df: pd.DataFrame):
    """Measurement columns only: row counters and ID sequences are skipped."""
    num = numeric_frame(df)
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if is_index_like(values):
            continue
        yield str(column), values


def index_like_columns(df: pd.DataFrame) -> list[str]:
    num = numeric_frame(df)
    return [
        str(column)
        for column in num.columns
        if is_index_like(num[column].dropna().to_numpy(dtype=float))
    ]


def _benford_column(column: str, values: np.ndarray) -> dict[str, object]:
    observed = _first_digit_counts(values)
    total = float(observed.sum())
    expected = BENFORD_EXPECTED * total
    chi_square = float(np.sum((observed - expected) ** 2 / expected))
    p_value = float(stats.chi2.sf(chi_square, df=8))
    mad = float(np.mean(np.abs(observed / total - BENFORD_EXPECTED)))
    return {
        "column": column,
        "n": int(total),
        "observed_counts": observed.astype(int).tolist(),
        "expected_probabilities": [round(float(p), 6) for p in BENFORD_EXPECTED],
        "chi_square": round(chi_square, 6),
        "p_value": float(f"{p_value:.6g}"),
        "mad": round(mad, 6),
        "order_of_magnitude_span": round(order_of_magnitude_span(values), 3),
    }


def _digit_column(column: str, digits: np.ndarray) -> dict[str, object]:
    counts = np.bincount(digits, minlength=10).astype(float)
    total = counts.sum()
    chi_square = float(stats.chisquare(counts, np.full(10, total / 10)).statistic)
    p_value = float(stats.chi2.sf(chi_square, df=9))
    return {
        "column": column,
        "n": int(total),
        "counts_0_to_9": counts.astype(int).tolist(),
        "top_digit": int(np.argmax(counts)),
        "top_rate": round(float(counts.max() / total), 6),
        "entropy_bits": round(float(stats.entropy(counts / total, base=2)), 6),
        "chi_square": round(chi_square, 6),
        "p_value": float(f"{p_value:.6g}"),
        "cramers_v": round(cramers_v(counts, chi_square), 6),
    }


def _first_digit_counts(values: np.ndarray) -> np.ndarray:
    counts = np.zeros(9, dtype=float)
    for value in np.abs(values):
        text = f"{value:.12e}"
        digit = int(text[0])
        if 1 <= digit <= 9:
            counts[digit - 1] += 1
    return counts

