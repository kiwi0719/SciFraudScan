from __future__ import annotations

import pandas as pd

from research_integrity_screen.inference import (
    infer_group_column,
    infer_inputs,
    infer_p_values,
    infer_reported_stats,
    infer_time_column,
)


def test_infers_group_time_and_p_value_columns() -> None:
    df = pd.DataFrame(
        {
            "subject_id": ["S1", "S2", "S3", "S4"],
            "treatment": ["A", "A", "B", "B"],
            "visit_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "score": [10, 12, 25, 27],
            "p_value": [0.049, 0.031, 0.2, 0.8],
        }
    )

    assert infer_group_column(df) == "treatment"
    assert infer_time_column(df) == "visit_date"
    assert infer_p_values(df) is not None


def test_infers_reported_stats_table() -> None:
    df = pd.DataFrame(
        {
            "test": ["grim", "t"],
            "n": [20, None],
            "mean": [3.43, None],
            "stat": [None, 2.35],
            "df1": [None, 18],
            "p_value": [None, 0.03],
        }
    )

    reported = infer_reported_stats(df)

    assert reported is not None
    assert "p" in reported.columns


def test_infer_inputs_notes_detected_columns() -> None:
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "value": [1, 2, 3, 4],
        }
    )

    inferred = infer_inputs(df)

    assert inferred.group_column == "group"
    assert inferred.time_column == "date"
    assert inferred.notes
