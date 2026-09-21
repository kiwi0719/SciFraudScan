"""Run selected check groups and collect their findings.

The pipeline does no interpretation. It reports what each check found, what it
could not run and why, and leaves the weighing of those facts to the reader.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from scifraudscan._version import __version__
from scifraudscan.detectors.authenticity import index_like_columns, run_authenticity_checks
from scifraudscan.detectors.covariance import run_covariance_checks
from scifraudscan.detectors.duplication import run_duplication_checks
from scifraudscan.detectors.pvalues import run_p_value_checks
from scifraudscan.detectors.randomization import (
    baseline_summary_check,
    reported_baseline_p_check,
    run_randomization_checks,
)
from scifraudscan.detectors.reported_stats import validate_reported_stats
from scifraudscan.detectors.structure import run_structure_checks
from scifraudscan.detectors.timeseries import run_timeseries_checks
from scifraudscan.models import Finding

CHECK_GROUPS: tuple[str, ...] = (
    "authenticity",
    "duplication",
    "structure",
    "randomization",
    "covariance",
    "timeseries",
    "reported_stats",
    "pvalues",
    "baseline",
)

DATA_GROUPS = frozenset({"authenticity", "duplication", "structure", "randomization",
                         "covariance", "timeseries"})


def scan(
    df: pd.DataFrame | None = None,
    *,
    groups: list[str] | tuple[str, ...] | None = None,
    reported_stats: pd.DataFrame | None = None,
    p_values: pd.DataFrame | None = None,
    baseline_summary: pd.DataFrame | None = None,
    group_column: str | None = None,
    time_column: str | None = None,
    assumed_power: float = 0.5,
) -> dict[str, Any]:
    selected = tuple(groups) if groups else CHECK_GROUPS
    unknown = [g for g in selected if g not in CHECK_GROUPS]
    if unknown:
        raise ValueError(f"Unknown check groups: {', '.join(unknown)}")

    runners: dict[str, Callable[[], list[Finding]]] = {
        "authenticity": lambda: run_authenticity_checks(df),
        "duplication": lambda: run_duplication_checks(df),
        "structure": lambda: run_structure_checks(df),
        "randomization": lambda: run_randomization_checks(df, group_column),
        "covariance": lambda: run_covariance_checks(df),
        "timeseries": lambda: run_timeseries_checks(df, time_column),
        "reported_stats": lambda: validate_reported_stats(reported_stats),
        "pvalues": lambda: run_p_value_checks(p_values, assumed_power),
        "baseline": lambda: [
            baseline_summary_check(baseline_summary),
            reported_baseline_p_check(baseline_summary),
        ],
    }

    sections: list[dict[str, Any]] = []
    for name in selected:
        if name in DATA_GROUPS and df is None:
            continue
        if name == "reported_stats" and reported_stats is None:
            continue
        if name == "pvalues" and p_values is None:
            continue
        if name == "baseline" and baseline_summary is None:
            continue
        findings = runners[name]()
        sections.append({"group": name, "findings": [f.as_dict() for f in findings]})

    findings = [f for section in sections for f in section["findings"]]
    flagged = [f for f in findings if f["outcome"] == "flag"]
    severities = [f.get("severity") for f in flagged]
    return {
        "scifraudscan_version": __version__,
        "inputs": {
            "rows": len(df) if df is not None else 0,
            "columns": [str(c) for c in df.columns] if df is not None else [],
            "group_column": group_column,
            "time_column": time_column,
            "index_like_columns_skipped": index_like_columns(df) if df is not None else [],
            "reported_stats_rows": len(reported_stats) if reported_stats is not None else 0,
            "p_value_count": len(p_values) if p_values is not None else 0,
        },
        "summary": {
            "groups_run": list(selected),
            "flagged": len(flagged),
            "cleared": sum(1 for f in findings if f["outcome"] == "clear"),
            "not_applicable": sum(1 for f in findings if f["outcome"] == "not_applicable"),
            "highest_severity": (
                "high" if "high" in severities
                else "moderate" if "moderate" in severities
                else "low" if "low" in severities
                else None
            ),
        },
        "sections": sections,
    }
