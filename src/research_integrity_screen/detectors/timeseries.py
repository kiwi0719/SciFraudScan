from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal
from statsmodels.tsa.stattools import acf

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import numeric_frame


def autocorrelation_analysis(df: pd.DataFrame, time_column: str | None = None) -> Finding:
    ordered = _ordered(df, time_column)
    num = numeric_frame(ordered.drop(columns=[time_column], errors="ignore") if time_column else ordered)
    flagged: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < 10 or np.std(values) <= 1e-12:
            continue
        lag1 = float(acf(values, nlags=1, fft=False, missing="drop")[1])
        diffs = np.diff(values)
        diff_lag1 = (
            float(acf(diffs, nlags=1, fft=False, missing="drop")[1])
            if len(diffs) > 2 and np.std(diffs[:-1]) > 1e-12 and np.std(diffs[1:]) > 1e-12
            else 0.0
        )
        if abs(lag1) > 0.9 or abs(diff_lag1) > 0.9:
            flagged.append({"column": str(column), "lag1": round(lag1, 6), "diff_lag1": round(diff_lag1, 6)})
    score = min(100.0, len(flagged) * 35)
    return Finding(
        "Autocorrelation Analysis",
        _status(score),
        score,
        f"{len(flagged)} numeric series have very high lag autocorrelation.",
        {"time_column": time_column, "columns": flagged[:20], "column_count": len(flagged)},
    )


def spectral_analysis(df: pd.DataFrame, time_column: str | None = None) -> Finding:
    ordered = _ordered(df, time_column)
    num = numeric_frame(ordered.drop(columns=[time_column], errors="ignore") if time_column else ordered)
    flagged: list[dict[str, object]] = []
    for column in num.columns:
        values = num[column].dropna().to_numpy(dtype=float)
        if len(values) < 16 or np.std(values) == 0:
            continue
        _, power = signal.periodogram(values, detrend="constant")
        if len(power) <= 2 or power.sum() == 0:
            continue
        power[0] = 0
        dominant_ratio = float(power.max() / power.sum())
        peak_index = int(power.argmax())
        # A single dominant frequency can indicate repeated artificial cycles.
        if dominant_ratio > 0.65:
            flagged.append(
                {
                    "column": str(column),
                    "dominant_power_ratio": round(dominant_ratio, 6),
                    "peak_index": peak_index,
                }
            )
    score = min(100.0, len(flagged) * 40)
    return Finding(
        "Spectral Analysis",
        _status(score),
        score,
        f"{len(flagged)} numeric series have a dominant repeated frequency.",
        {"time_column": time_column, "columns": flagged[:20], "column_count": len(flagged)},
    )


def run_timeseries_checks(df: pd.DataFrame, time_column: str | None = None) -> list[Finding]:
    return [autocorrelation_analysis(df, time_column), spectral_analysis(df, time_column)]


def _ordered(df: pd.DataFrame, time_column: str | None) -> pd.DataFrame:
    if not time_column or time_column not in df.columns:
        return df
    ordered = df.copy()
    parsed = pd.to_datetime(ordered[time_column], errors="coerce")
    if parsed.notna().sum() >= 2:
        ordered = ordered.assign(_riskscan_time=parsed).sort_values("_riskscan_time").drop(columns=["_riskscan_time"])
    return ordered


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
