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
from research_integrity_screen.models import SectionReport


def scan_dataframe(
    df: pd.DataFrame,
    reported_stats: pd.DataFrame | None = None,
    p_values: pd.DataFrame | None = None,
    group_column: str | None = None,
    time_column: str | None = None,
) -> dict[str, Any]:
    sections = [
        SectionReport("Data Authenticity", run_authenticity_checks(df)),
        SectionReport("Duplication", run_duplication_checks(df)),
        SectionReport("Structure", run_structure_checks(df)),
        SectionReport("Randomization", run_randomization_checks(df, group_column)),
        SectionReport("Covariance", run_covariance_checks(df)),
        SectionReport("Time Series", run_timeseries_checks(df, time_column)),
    ]
    if reported_stats is not None:
        sections.append(SectionReport("Reported Statistics", validate_reported_stats(reported_stats)))
    if p_values is not None:
        sections.append(SectionReport("Significance", run_p_value_checks(p_values)))

    overall = min(100.0, sum(section.score for section in sections) / len(sections)) if sections else 0.0
    return {
        "research_integrity_score": round(overall, 3),
        "overall_risk": _status(overall),
        "sections": [section.as_dict() for section in sections],
    }


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
