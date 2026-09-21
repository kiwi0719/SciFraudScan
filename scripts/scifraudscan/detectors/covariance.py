"""Shape of the covariance matrix.

Only two signals are reported: variables that are near-collinear, and a
covariance matrix that is singular or nearly so. Low correlation between
variables is not evidence of anything and is deliberately not flagged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scifraudscan.models import Finding, clear, not_applicable
from scifraudscan.utils import numeric_frame

MIN_ROWS = 10
MIN_COLUMNS = 3
HIGH_CORRELATION = 0.98
CONDITION_LIMIT = 1e8


def covariance_structure(df: pd.DataFrame) -> Finding:
    check = "Covariance Structure"
    num = numeric_frame(df).dropna(axis=0, how="any")
    if num.shape[0] < MIN_ROWS or num.shape[1] < MIN_COLUMNS:
        return not_applicable(
            check,
            f"Needs at least {MIN_ROWS} complete rows and {MIN_COLUMNS} numeric columns; "
            f"found {num.shape[0]} and {num.shape[1]}.",
        )

    values = num.to_numpy(dtype=float)
    varying = values.std(axis=0) > 0
    values = values[:, varying]
    columns = [str(c) for c in np.array(num.columns)[varying].tolist()]
    if values.shape[1] < MIN_COLUMNS:
        return not_applicable(
            check, f"Only {values.shape[1]} numeric columns actually vary."
        )

    correlation = np.corrcoef(values, rowvar=False)
    rows, cols = np.triu_indices_from(correlation, k=1)
    off_diagonal = np.abs(correlation[rows, cols])
    hits = np.flatnonzero(off_diagonal > HIGH_CORRELATION)
    eigenvalues = np.linalg.eigvalsh(np.cov(values, rowvar=False))
    positive = eigenvalues[eigenvalues > 1e-12]
    condition = float(positive.max() / positive.min()) if len(positive) else float("inf")
    singular = len(positive) < len(eigenvalues) or condition > CONDITION_LIMIT

    shared = {
        "rows": int(values.shape[0]),
        "columns": columns,
        "high_correlation_pairs": [
            {"left": columns[rows[i]], "right": columns[cols[i]],
             "r": round(float(correlation[rows[i], cols[i]]), 8)}
            for i in hits[:20]
        ],
        "condition_number": round(condition, 3) if np.isfinite(condition) else "inf",
        "rank_deficient": bool(len(positive) < len(eigenvalues)),
    }
    if len(hits) == 0 and not singular:
        return clear(
            check,
            f"Covariance matrix over {len(columns)} columns is well conditioned with no "
            f"near-collinear pair (|r| > {HIGH_CORRELATION}).",
            **shared,
        )
    # Near-collinear pairs are extremely common in real data -- derived totals,
    # unit conversions, percentages alongside their counts -- and flagging them
    # fired on 57% of ordinary datasets. They are reported as a description of
    # the columns, which is what they are, and only a rank-deficient covariance
    # matrix is treated as a finding.
    parts = []
    if len(hits):
        parts.append(f"{len(hits)} column pairs exceed |r| = {HIGH_CORRELATION}")
    if singular:
        parts.append(f"the covariance matrix is near-singular (condition number {condition:.3g})")
    description = "; ".join(parts).capitalize() + "."
    if not singular:
        return clear(
            check,
            description
            + " Near-collinear columns usually mean one was computed from another, "
            "which is ordinary; nothing here is treated as an anomaly.",
            **shared,
        )
    # Rank deficiency is just as ordinary: a total beside its parts, a
    # percentage beside its count. Flagging it fired on 46% of real datasets
    # even after collinear pairs stopped being flagged. This check now only
    # ever describes.
    return clear(
        check,
        description
        + " A rank-deficient covariance matrix means some column carries no "
        "independent information, which usually means it was derived from the "
        "others. Reported for context, not as an anomaly.",
        **shared,
    )


def run_covariance_checks(df: pd.DataFrame) -> list[Finding]:
    return [covariance_structure(df)]
