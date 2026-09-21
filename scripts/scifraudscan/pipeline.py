"""Run selected check groups and collect their findings.

The pipeline does no interpretation. It reports what each check found, what it
could not run and why, and leaves the weighing of those facts to the reader.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
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

# Checks whose verdicts have been reproduced against real published papers,
# cell by cell, against conclusions reached outside this toolkit. These are
# exact arithmetic: a failure means the reported numbers cannot all be true.
VALIDATED_GROUPS: tuple[str, ...] = (
    "reported_stats",
    "baseline_p",
)

# Everything else. These are not wrong, but nothing establishes how often they
# fire on sound data, so they are off unless asked for. See
# references/METHODOLOGY.md and benchmarks/real_cases/README.md.
EXPERIMENTAL_GROUPS: tuple[str, ...] = (
    "authenticity",
    "duplication",
    "structure",
    "randomization",
    "covariance",
    "timeseries",
    "pvalues",
    "baseline_balance",
)

CHECK_GROUPS: tuple[str, ...] = VALIDATED_GROUPS + EXPERIMENTAL_GROUPS

BASE_RATE_FILE = Path(__file__).resolve().parent / "reference" / "experimental_base_rates.csv"


def experimental_base_rates() -> dict[str, float]:
    """How often each experimental check fires on ordinary real datasets.

    Measured over 300 datasets from Rdatasets that have nothing to do with
    research misconduct. A severity means little without this number: a check
    that fires on 87% of ordinary data is describing the data, not an anomaly.
    """
    with BASE_RATE_FILE.open() as fh:
        return {row["check"]: float(row["base_rate"]) for row in csv.DictReader(fh)}

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
    benford_scale_invariant: bool = False,
    include_experimental: bool = False,
) -> dict[str, Any]:
    if groups:
        selected = tuple(groups)  # naming a group explicitly is opting into it
    elif include_experimental:
        selected = CHECK_GROUPS
    else:
        selected = VALIDATED_GROUPS
    unknown = [g for g in selected if g not in CHECK_GROUPS]
    if unknown:
        raise ValueError(f"Unknown check groups: {', '.join(unknown)}")

    runners: dict[str, Callable[[], list[Finding]]] = {
        "authenticity": lambda: run_authenticity_checks(df, benford_scale_invariant),
        "duplication": lambda: run_duplication_checks(df),
        "structure": lambda: run_structure_checks(df),
        "randomization": lambda: run_randomization_checks(df, group_column),
        "covariance": lambda: run_covariance_checks(df),
        "timeseries": lambda: run_timeseries_checks(df, time_column),
        "reported_stats": lambda: validate_reported_stats(reported_stats),
        "pvalues": lambda: run_p_value_checks(p_values, assumed_power),
        "baseline_p": lambda: [reported_baseline_p_check(baseline_summary)],
        "baseline_balance": lambda: [baseline_summary_check(baseline_summary)],
    }

    base_rates = experimental_base_rates()
    sections: list[dict[str, Any]] = []
    for name in selected:
        if name in DATA_GROUPS and df is None:
            continue
        if name == "reported_stats" and reported_stats is None:
            continue
        if name == "pvalues" and p_values is None:
            continue
        if name in {"baseline_p", "baseline_balance"} and baseline_summary is None:
            continue
        findings = runners[name]()
        serialized = []
        for finding in (f.as_dict() for f in findings):
            if name in EXPERIMENTAL_GROUPS and finding["check"] in base_rates:
                finding["fires_on_ordinary_data"] = base_rates[finding["check"]]
            serialized.append(finding)
        sections.append(
            {
                "group": name,
                "validation": (
                    "reproduced against real published cases"
                    if name in VALIDATED_GROUPS
                    else "none — see references/METHODOLOGY.md"
                ),
                "findings": serialized,
            }
        )

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
            "experimental_groups_run": [g for g in selected if g in EXPERIMENTAL_GROUPS],
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
