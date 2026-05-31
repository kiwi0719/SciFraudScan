from __future__ import annotations

import pandas as pd

from research_integrity_screen.detectors.authenticity import digit_preference, information_entropy
from research_integrity_screen.detectors.covariance import covariance_structure
from research_integrity_screen.detectors.duplication import (
    exact_duplicates,
    linear_transformation_duplicates,
    permutation_duplicates,
)
from research_integrity_screen.detectors.randomization import carlisle_method
from research_integrity_screen.detectors.reported_stats import grim_possible
from research_integrity_screen.detectors.structure import constant_difference, constant_ratio
from research_integrity_screen.detectors.timeseries import autocorrelation_analysis, spectral_analysis
from research_integrity_screen.pipeline import scan_dataframe


def test_structural_and_duplicate_signals_are_detected() -> None:
    df = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5],
            "b": [6, 7, 8, 9, 10],
            "c": [2, 4, 6, 8, 10],
            "d": [3, 1, 5, 2, 4],
        }
    )

    assert constant_difference(df).details["match_count"] >= 1
    assert constant_ratio(df).details["match_count"] >= 1
    assert linear_transformation_duplicates(df).details["match_count"] >= 1
    assert permutation_duplicates(df).details["match_count"] >= 1


def test_exact_duplicate_rows() -> None:
    df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
    finding = exact_duplicates(df)
    assert finding.details["duplicate_rows"] == 2
    assert finding.score > 0


def test_grim_possible() -> None:
    assert grim_possible(20, 3.45)
    assert not grim_possible(20, 3.43)


def test_pipeline_returns_sections() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8]})
    report = scan_dataframe(df)
    assert report["research_integrity_score"] >= 0
    assert {"Data Authenticity", "Duplication", "Structure", "Randomization", "Covariance", "Time Series"} <= {
        section["name"] for section in report["sections"]
    }


def test_authenticity_checks_detect_digit_and_entropy_patterns() -> None:
    df = pd.DataFrame({"a": [10, 20, 30, 40, 50] * 10})
    assert digit_preference(df).score > 0
    assert information_entropy(df).details["column_count"] >= 1


def test_carlisle_covariance_and_timeseries_checks_run() -> None:
    df = pd.DataFrame(
        {
            "group": ["a"] * 10 + ["b"] * 10,
            "x": list(range(20)),
            "y": [value * 2 for value in range(20)],
            "z": [1, 2, 1, 2] * 5,
        }
    )

    assert carlisle_method(df, "group").check == "Carlisle Randomization"
    assert covariance_structure(df).check == "Covariance Structure"
    assert autocorrelation_analysis(df).details["column_count"] >= 1
    assert spectral_analysis(df).check == "Spectral Analysis"
