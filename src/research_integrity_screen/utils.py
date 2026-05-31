from __future__ import annotations

import math

import numpy as np
import pandas as pd


def numeric_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)


def finite_pair(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    pair = pd.concat([a, b], axis=1).dropna()
    if pair.empty:
        return np.array([]), np.array([])
    return pair.iloc[:, 0].to_numpy(dtype=float), pair.iloc[:, 1].to_numpy(dtype=float)


def risk_status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"


def safe_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number
