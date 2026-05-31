from __future__ import annotations

import numpy as np
import pandas as pd

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import numeric_frame


def covariance_structure(df: pd.DataFrame) -> Finding:
    num = numeric_frame(df).dropna(axis=0, how="any")
    if num.shape[0] < 5 or num.shape[1] < 3:
        return Finding("Covariance Structure", "Pass", 0, "Need at least 5 complete rows and 3 numeric columns.")

    values = num.to_numpy(dtype=float)
    std = values.std(axis=0)
    usable = std > 0
    values = values[:, usable]
    columns = np.array(num.columns)[usable]
    if values.shape[1] < 3:
        return Finding("Covariance Structure", "Pass", 0, "Fewer than 3 varying numeric columns.")

    corr = np.corrcoef(values, rowvar=False)
    off_diag = np.abs(corr[np.triu_indices_from(corr, k=1)])
    near_identity_rate = float((off_diag < 0.01).sum() / len(off_diag))
    high_corr_rate = float((off_diag > 0.98).sum() / len(off_diag))
    eigvals = np.linalg.eigvalsh(np.cov(values, rowvar=False))
    positive = eigvals[eigvals > 1e-12]
    condition_number = float(positive.max() / positive.min()) if len(positive) else float("inf")
    near_singular = condition_number > 1e8 or len(positive) < len(eigvals)
    score = min(100.0, high_corr_rate * 120 + near_identity_rate * 35 + (35 if near_singular else 0))
    return Finding(
        "Covariance Structure",
        _status(score),
        score,
        f"High-correlation rate={high_corr_rate:.1%}, near-zero-correlation rate={near_identity_rate:.1%}.",
        {
            "rows": int(values.shape[0]),
            "columns": [str(column) for column in columns.tolist()],
            "high_correlation_rate": round(high_corr_rate, 6),
            "near_identity_rate": round(near_identity_rate, 6),
            "condition_number": round(condition_number, 6) if np.isfinite(condition_number) else "inf",
            "near_singular": bool(near_singular),
        },
    )


def run_covariance_checks(df: pd.DataFrame) -> list[Finding]:
    return [covariance_structure(df)]


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
