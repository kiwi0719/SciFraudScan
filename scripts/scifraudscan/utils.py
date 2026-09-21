from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd


def numeric_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)


def finite_pair(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    pair = pd.concat([a, b], axis=1).dropna()
    if pair.empty:
        return np.array([]), np.array([])
    return pair.iloc[:, 0].to_numpy(dtype=float), pair.iloc[:, 1].to_numpy(dtype=float)


def safe_float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def decimal_places(value: object) -> int:
    """Decimal places exactly as written, so 3.40 reports 2 and 3.4 reports 1.

    GRIM and GRIMMER depend on the reported precision, so the string form
    matters and float(value) would destroy it.
    """
    try:
        text = format(Decimal(str(value).strip()), "f")
    except (InvalidOperation, AttributeError):
        return 0
    return len(text.split(".", 1)[1]) if "." in text else 0


def lag1_autocorrelation(values: np.ndarray) -> float:
    """Lag-1 autocorrelation, same estimator as statsmodels.tsa.stattools.acf."""
    series = np.asarray(values, dtype=float)
    n = len(series)
    if n < 3:
        return 0.0
    centered = series - series.mean()
    denominator = float(np.dot(centered, centered))
    if denominator <= 1e-300:
        return 0.0
    return float(np.dot(centered[:-1], centered[1:]) / denominator)


def cramers_v(counts: np.ndarray, chi_square: float) -> float:
    """Effect size for a one-way goodness-of-fit chi-square."""
    total = float(np.sum(counts))
    categories = len(counts)
    if total <= 0 or categories < 2:
        return 0.0
    return float(math.sqrt(chi_square / (total * (categories - 1))))


def order_of_magnitude_span(values: np.ndarray) -> float:
    """How many powers of ten the non-zero magnitudes cover."""
    magnitudes = np.abs(np.asarray(values, dtype=float))
    magnitudes = magnitudes[(magnitudes > 0) & np.isfinite(magnitudes)]
    if len(magnitudes) < 2:
        return 0.0
    return float(np.log10(magnitudes.max()) - np.log10(magnitudes.min()))


def reported_precision(values: np.ndarray) -> int:
    """Decimal places the column appears to be recorded to."""
    places = 0
    for value in np.asarray(values, dtype=float)[:5000]:
        text = f"{value:.12g}"
        if "e" in text or "E" in text:
            continue
        if "." in text:
            places = max(places, len(text.split(".", 1)[1]))
    return places


def terminal_digits(values: np.ndarray) -> np.ndarray:
    """Final recorded digit of each value, counting trailing zeros.

    A value of 54.0 in a column recorded to one decimal ends in 0, not 4.
    Stripping the zero would systematically deplete digit 0 and inflate the
    digit before it, which by itself looks like digit preference.
    """
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if len(series) == 0:
        return np.array([], dtype=int)
    scale = 10 ** reported_precision(series)
    scaled = np.rint(np.abs(series) * scale)
    return np.mod(scaled, 10).astype(int)


def is_index_like(values: np.ndarray) -> bool:
    """Row counters, IDs and enrolment sequences are bookkeeping, not measurements.

    Digit and regularity checks are meaningless on them: a 1..N counter fails
    Benford's law and has perfectly constant steps by construction.
    """
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if len(series) < 3:
        return False
    if not np.allclose(series, np.rint(series)):
        return False
    if len(np.unique(series)) != len(series):
        return False
    steps = np.diff(np.sort(series))
    return bool(np.all(steps == steps[0]))
