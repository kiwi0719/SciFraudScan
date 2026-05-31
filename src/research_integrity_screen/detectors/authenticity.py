from __future__ import annotations

import math
import re
import zlib

import benford
import numpy as np
import pandas as pd
from scipy import stats

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import numeric_frame


def benford_law(df: pd.DataFrame) -> Finding:
    values = _benford_values(numeric_frame(df))
    if len(values) < 30:
        return Finding("Benford Law", "Pass", 0, "Fewer than 30 usable leading digits.")

    result = benford.first_digits(pd.Series(values), digs=1, decimals=8, sign="all", verbose=False)
    observed = result["Counts"].to_numpy(dtype=float)
    expected_probs = result["Expected"].to_numpy(dtype=float)
    expected = expected_probs * observed.sum()
    chi_square = float(((observed - expected) ** 2 / expected).sum())
    p_value = float(stats.chi2.sf(chi_square, df=8))
    mad = float(benford.mad(pd.Series(values), test=1, decimals=8, sign="all", verbose=False))
    score = min(100.0, max(0.0, -math.log10(max(p_value, 1e-12)) * 18 + mad * 900))
    return Finding(
        "Benford Law",
        _status(score),
        score,
        f"Leading-digit distribution has chi-square p={p_value:.4g} and MAD={mad:.4f}.",
        {
            "n": int(len(values)),
            "observed": observed.astype(int).tolist(),
            "expected_probabilities": [round(float(x), 6) for x in expected_probs],
            "chi_square": round(chi_square, 6),
            "p_value": round(p_value, 8),
            "mad": round(mad, 6),
        },
    )


def digit_preference(df: pd.DataFrame) -> Finding:
    last_digits = _last_digits(numeric_frame(df))
    if len(last_digits) < 30:
        return Finding("Digit Preference", "Pass", 0, "Fewer than 30 usable terminal digits.")
    counts = np.array([(last_digits == digit).sum() for digit in range(10)], dtype=float)
    probs = counts / counts.sum()
    entropy = float(stats.entropy(probs, base=2))
    expected_entropy = math.log2(10)
    top_digit = int(np.argmax(counts))
    top_rate = float(counts.max() / counts.sum())
    chi_square = float(stats.chisquare(counts, np.ones(10) * counts.sum() / 10).statistic)
    p_value = float(stats.chi2.sf(chi_square, df=9))
    score = min(100.0, max(0.0, (expected_entropy - entropy) * 45 + top_rate * 120 - 12))
    return Finding(
        "Digit Preference",
        _status(score),
        score,
        f"Most common terminal digit is {top_digit} at {top_rate:.1%}; entropy={entropy:.3f}.",
        {
            "n": int(len(last_digits)),
            "counts": counts.astype(int).tolist(),
            "entropy": round(entropy, 6),
            "top_digit": top_digit,
            "top_rate": round(top_rate, 6),
            "chi_square": round(chi_square, 6),
            "p_value": round(p_value, 8),
        },
    )


def information_entropy(df: pd.DataFrame) -> Finding:
    num = numeric_frame(df)
    flagged: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < 10:
            continue
        rounded = [f"{value:.8g}" for value in values]
        raw = ",".join(rounded).encode("utf-8")
        compressed = zlib.compress(raw)
        ratio = len(compressed) / max(1, len(raw))
        unique_rate = len(set(rounded)) / len(rounded)
        diffs = np.diff(values)
        diff_unique_rate = len(set(np.round(diffs, 8))) / len(diffs) if len(diffs) else 1.0
        if ratio < 0.45 or unique_rate < 0.4 or diff_unique_rate < 0.35:
            flagged.append(
                {
                    "column": str(column),
                    "compression_ratio": round(float(ratio), 6),
                    "unique_rate": round(float(unique_rate), 6),
                    "difference_unique_rate": round(float(diff_unique_rate), 6),
                }
            )
    score = min(100.0, len(flagged) * 35)
    return Finding(
        "Information Entropy",
        _status(score),
        score,
        f"{len(flagged)} numeric columns have low complexity or strongly repeated increments.",
        {"columns": flagged[:20], "column_count": len(flagged)},
    )


def run_authenticity_checks(df: pd.DataFrame) -> list[Finding]:
    return [benford_law(df), digit_preference(df), information_entropy(df)]


def _benford_values(df: pd.DataFrame) -> np.ndarray:
    values: list[float] = []
    for value in df.to_numpy().ravel():
        if pd.isna(value) or float(value) == 0:
            continue
        values.append(float(value))
    return np.array(values, dtype=float)


def _last_digits(df: pd.DataFrame) -> np.ndarray:
    digits: list[int] = []
    for value in df.to_numpy().ravel():
        if pd.isna(value):
            continue
        text = f"{abs(float(value)):.12g}".rstrip("0").rstrip(".")
        match = re.search(r"(\d)$", text)
        if match:
            digits.append(int(match.group(1)))
    return np.array(digits, dtype=int)


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
