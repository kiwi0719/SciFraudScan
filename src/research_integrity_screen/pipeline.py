from __future__ import annotations

from typing import Any

import pandas as pd

from research_integrity_screen.detectors.authenticity import run_authenticity_checks
from research_integrity_screen.detectors.covariance import run_covariance_checks
from research_integrity_screen.detectors.duplication import run_duplication_checks
from research_integrity_screen.detectors.pvalues import run_p_value_checks
from research_integrity_screen.detectors.randomization import run_randomization_checks
from research_integrity_screen.detectors.reported_stats import validate_reported_stats
from research_integrity_screen.detectors.structure import run_structure_checks
from research_integrity_screen.detectors.timeseries import run_timeseries_checks
from research_integrity_screen.inference import infer_inputs
from research_integrity_screen.models import SectionReport


def scan_dataframe(
    df: pd.DataFrame,
    reported_stats: pd.DataFrame | None = None,
    p_values: pd.DataFrame | None = None,
    group_column: str | None = None,
    time_column: str | None = None,
) -> dict[str, Any]:
    inferred = infer_inputs(df)
    effective_group_column = group_column or inferred.group_column
    effective_time_column = time_column or inferred.time_column
    effective_reported_stats = reported_stats if reported_stats is not None else inferred.reported_stats
    effective_p_values = p_values if p_values is not None else inferred.p_values

    sections = [
        SectionReport("Data Authenticity", run_authenticity_checks(df)),
        SectionReport("Duplication", run_duplication_checks(df)),
        SectionReport("Structure", run_structure_checks(df)),
        SectionReport("Randomization", run_randomization_checks(df, effective_group_column)),
        SectionReport("Covariance", run_covariance_checks(df)),
        SectionReport("Time Series", run_timeseries_checks(df, effective_time_column)),
    ]
    if effective_reported_stats is not None:
        sections.append(SectionReport("Reported Statistics", validate_reported_stats(effective_reported_stats)))
    if effective_p_values is not None:
        sections.append(SectionReport("Significance", run_p_value_checks(effective_p_values)))

    overall = min(100.0, sum(section.score for section in sections) / len(sections)) if sections else 0.0
    return {
        "research_integrity_score": round(overall, 3),
        "overall_risk": _status(overall),
        "auto_detection": {
            "group_column": effective_group_column,
            "time_column": effective_time_column,
            "p_values": effective_p_values is not None,
            "reported_stats": effective_reported_stats is not None,
            "notes": inferred.notes,
        },
        "sections": [section.as_dict() for section in sections],
    }


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
