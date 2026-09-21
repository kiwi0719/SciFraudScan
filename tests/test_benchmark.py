"""Regression benchmark: the toolkit must separate honest from fabricated data.

This is the check that matters most. A screening tool that flags honest data is
worse than no tool, because a false flag lands on a real person.
"""

from __future__ import annotations

import pandas as pd
import pytest
from scifraudscan.pipeline import scan

EXPECTED_ON_FABRICATED = {
    "Terminal Digit Preference",
    "Linear Transformation Duplicate",
    "Repeated Value Blocks",
    "Carlisle Baseline Balance",
    "GRIM",
    "SD Feasibility (GRIMMER / variance bounds)",
    "Reported p-value Consistency",
    "Just-Significant Clustering (caliper test)",
    "P-Curve Shape",
}


def _flagged(result: dict) -> set[str]:
    return {
        finding["check"]
        for section in result["sections"]
        for finding in section["findings"]
        if finding["outcome"] == "flag"
    }


@pytest.fixture(scope="module")
def clean_result(examples_dir) -> dict:
    return scan(
        pd.read_csv(examples_dir / "clean_trial.csv"),
        group_column="arm",
        time_column="enrol_day",
    )


@pytest.fixture(scope="module")
def fabricated_result(examples_dir) -> dict:
    return scan(
        pd.read_csv(examples_dir / "fabricated_trial.csv"),
        group_column="arm",
        time_column="enrol_day",
        reported_stats=pd.read_csv(examples_dir / "reported_stats.csv"),
        p_values=pd.read_csv(examples_dir / "p_values.csv"),
    )


def test_honest_data_raises_no_flags(clean_result) -> None:
    assert _flagged(clean_result) == set(), (
        "false positives on honestly generated data: " + ", ".join(sorted(_flagged(clean_result)))
    )


def test_fabricated_data_is_caught(fabricated_result) -> None:
    missed = EXPECTED_ON_FABRICATED - _flagged(fabricated_result)
    assert not missed, "planted defects not detected: " + ", ".join(sorted(missed))


def test_every_check_reports_an_outcome(fabricated_result) -> None:
    findings = [f for s in fabricated_result["sections"] for f in s["findings"]]
    assert len(findings) == 22
    assert all(f["outcome"] in {"flag", "clear", "not_applicable"} for f in findings)
    assert all(f["message"] for f in findings)


def test_no_aggregate_score_is_produced(clean_result) -> None:
    """The absence of a single risk number is a design decision, not an omission."""
    serialized = str(clean_result)
    assert "research_integrity_score" not in serialized
    assert "score" not in clean_result["summary"]
