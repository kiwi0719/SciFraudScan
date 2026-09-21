"""Regression benchmark: the toolkit must separate honest from fabricated data.

This is the check that matters most. A screening tool that flags honest data is
worse than no tool, because a false flag lands on a real person.
"""

from __future__ import annotations

import pandas as pd
import pytest
from scifraudscan.pipeline import scan

# Terminal digit preference is deliberately absent. The planted heaping in
# outcome_score sits at the 94th percentile of real published columns, and a
# threshold low enough to catch it flags 8% of ordinary data. Real data heaps
# on 0 and 5 as hard as this fabrication does; see
# benchmarks/false_positives/README.md.
EXPECTED_ON_FABRICATED = {
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
        include_experimental=True,
    )


@pytest.fixture(scope="module")
def fabricated_result(examples_dir) -> dict:
    return scan(
        pd.read_csv(examples_dir / "fabricated_trial.csv"),
        group_column="arm",
        time_column="enrol_day",
        reported_stats=pd.read_csv(examples_dir / "reported_stats.csv"),
        p_values=pd.read_csv(examples_dir / "p_values.csv"),
        include_experimental=True,
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


def test_the_default_run_is_the_validated_checks_only(examples_dir) -> None:
    """A raw dataset reaches no validated check, and must not silently appear clean."""
    result = scan(pd.read_csv(examples_dir / "fabricated_trial.csv"), group_column="arm")
    assert result["sections"] == []
    assert result["summary"]["groups_run"] == ["reported_stats", "baseline_p"]
    assert result["summary"]["experimental_groups_run"] == []

    opted_in = scan(
        pd.read_csv(examples_dir / "fabricated_trial.csv"),
        group_column="arm",
        include_experimental=True,
    )
    assert opted_in["summary"]["experimental_groups_run"]
    assert all(
        s["validation"].startswith("none")
        for s in opted_in["sections"]
        if s["group"] not in {"reported_stats", "baseline_p"}
    )


def test_no_aggregate_score_is_produced(clean_result) -> None:
    """The absence of a single risk number is a design decision, not an omission."""
    serialized = str(clean_result)
    assert "research_integrity_score" not in serialized
    assert "score" not in clean_result["summary"]
