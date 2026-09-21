"""Sequential structure in the data.

These only mean anything when the rows have a real order. Without a time or
sequence column, row order in a CSV is an artefact of how the file was
assembled, so both checks refuse to run rather than report on noise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import lag1_autocorrelation, numeric_frame

MIN_AUTOCORRELATION_N = 30
MIN_SPECTRAL_N = 32
AUTOCORRELATION_LIMIT = 0.9
DOMINANT_POWER_LIMIT = 0.5


def autocorrelation_analysis(df: pd.DataFrame, time_column: str | None = None) -> Finding:
    check = "Serial Autocorrelation"
    if not time_column:
        return not_applicable(
            check, "No time or sequence column was supplied, so row order is not meaningful."
        )
    ordered, error = _ordered(df, time_column)
    if error:
        return not_applicable(check, error)

    num = numeric_frame(ordered.drop(columns=[time_column], errors="ignore"))
    flagged: list[dict[str, object]] = []
    evaluated = 0
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < MIN_AUTOCORRELATION_N or np.std(values) <= 1e-12:
            continue
        evaluated += 1
        lag1 = lag1_autocorrelation(values)
        diff_lag1 = lag1_autocorrelation(np.diff(values)) if len(values) > 3 else 0.0
        if abs(lag1) > AUTOCORRELATION_LIMIT or abs(diff_lag1) > AUTOCORRELATION_LIMIT:
            flagged.append(
                {"column": str(column), "n": len(values),
                 "lag1": round(lag1, 6), "lag1_of_differences": round(diff_lag1, 6)}
            )

    if evaluated == 0:
        return not_applicable(
            check, f"No numeric column has {MIN_AUTOCORRELATION_N} or more ordered observations."
        )
    if not flagged:
        return clear(
            check,
            f"None of {evaluated} ordered series exceeds |lag-1 autocorrelation| "
            f"{AUTOCORRELATION_LIMIT}.",
            time_column=time_column,
            columns_evaluated=evaluated,
        )
    return flag(
        check,
        "moderate",
        f"{len(flagged)} of {evaluated} ordered series have near-deterministic "
        f"serial dependence (|lag-1| > {AUTOCORRELATION_LIMIT}).",
        time_column=time_column,
        columns_evaluated=evaluated,
        columns=flagged[:20],
    )


def spectral_analysis(df: pd.DataFrame, time_column: str | None = None) -> Finding:
    check = "Spectral Periodicity"
    if not time_column:
        return not_applicable(
            check, "No time or sequence column was supplied, so row order is not meaningful."
        )
    ordered, error = _ordered(df, time_column)
    if error:
        return not_applicable(check, error)

    num = numeric_frame(ordered.drop(columns=[time_column], errors="ignore"))
    flagged: list[dict[str, object]] = []
    evaluated = 0
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < MIN_SPECTRAL_N or np.std(values) == 0:
            continue
        evaluated += 1
        frequencies, power = signal.periodogram(values, detrend="linear")
        power = power[1:]
        frequencies = frequencies[1:]
        if len(power) < 2 or power.sum() <= 0:
            continue
        share = float(power.max() / power.sum())
        if share > DOMINANT_POWER_LIMIT:
            peak = int(power.argmax())
            flagged.append(
                {
                    "column": str(column),
                    "n": len(values),
                    "dominant_power_share": round(share, 6),
                    "period_in_rows": (
                        round(float(1 / frequencies[peak]), 4)
                        if frequencies[peak]
                        else None
                    ),
                }
            )

    if evaluated == 0:
        return not_applicable(
            check, f"No numeric column has {MIN_SPECTRAL_N} or more ordered observations."
        )
    if not flagged:
        return clear(
            check,
            f"None of {evaluated} ordered series is dominated by a single frequency.",
            time_column=time_column,
            columns_evaluated=evaluated,
        )
    return flag(
        check,
        "moderate",
        f"{len(flagged)} of {evaluated} ordered series carry a single repeating cycle holding "
        f"over {DOMINANT_POWER_LIMIT:.0%} of their spectral power.",
        time_column=time_column,
        columns_evaluated=evaluated,
        columns=flagged[:20],
    )


def run_timeseries_checks(df: pd.DataFrame, time_column: str | None = None) -> list[Finding]:
    return [autocorrelation_analysis(df, time_column), spectral_analysis(df, time_column)]


def _ordered(df: pd.DataFrame, time_column: str) -> tuple[pd.DataFrame, str | None]:
    if time_column not in df.columns:
        return df, f"Time column '{time_column}' is not in the dataset."
    parsed = pd.to_datetime(df[time_column], errors="coerce")
    if parsed.notna().sum() < len(df) * 0.8:
        parsed = pd.to_numeric(df[time_column], errors="coerce")
    if parsed.notna().sum() < len(df) * 0.8:
        return df, f"Column '{time_column}' could not be parsed as a date or a sequence number."
    ordered = df.assign(_order=parsed).sort_values("_order", kind="stable").drop(columns=["_order"])
    return ordered, None
