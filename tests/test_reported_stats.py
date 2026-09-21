"""GRIM and GRIMMER are exact arithmetic, so they get exact tests.

Cases are worked by hand: with n responses the total is an integer, so the
attainable means are exactly the multiples of 1/n.
"""

from __future__ import annotations

import pandas as pd
import pytest
from scifraudscan.detectors.reported_stats import (
    grim_consistent,
    grimmer_consistent,
    p_from_statistic,
    sd_bounds,
    validate_reported_stats,
)


@pytest.mark.parametrize(
    ("n", "mean", "decimals", "expected"),
    [
        (20, 3.45, 2, True),    # 69/20 = 3.45 exactly
        (20, 3.40, 2, True),    # 68/20 = 3.40 exactly
        (20, 3.46, 2, False),   # between 69/20 and 70/20, reachable by neither
        (28, 5.19, 2, False),
        (10, 2.5, 1, True),     # 25/10
        (7, 3.14, 2, True),     # 22/7 = 3.142857 -> rounds to 3.14
        (7, 3.15, 2, False),
    ],
)
def test_grim(n: int, mean: float, decimals: int, expected: bool) -> None:
    assert grim_consistent(n, mean, decimals) is expected


def test_grim_respects_scale_step() -> None:
    # Averaging a 4-item scale makes quarter-points attainable.
    assert grim_consistent(20, 3.4625, 4, scale_step=0.25) is True


def test_grim_uses_written_precision_not_float_value() -> None:
    # With n = 3 the attainable 1-decimal means are 10/3 -> 3.3 and 11/3 -> 3.7,
    # so 3.4 is impossible at either precision; at n = 20 it is fine.
    assert grim_consistent(20, 3.40, 2) is True
    assert grim_consistent(3, 3.40, 2) is False
    assert grim_consistent(3, 3.4, 1) is False
    assert grim_consistent(3, 3.3, 1) is True


def test_grimmer_rejects_impossible_sd() -> None:
    assert grimmer_consistent(20, 3.40, 0.76, 2, 2) is False


def test_grimmer_accepts_attainable_sd() -> None:
    assert grimmer_consistent(30, 3.00, 1.20, 2, 2) is True


def test_sd_bounds_are_tight_at_the_scale_edge() -> None:
    minimum, maximum = sd_bounds(30, 4.5, 1, 5)
    assert 0 < minimum < maximum < 1.5
    # A mean at the very top of the scale forces near-zero variance.
    assert sd_bounds(30, 5.0, 1, 5)[1] == pytest.approx(0.0, abs=1e-9)


def test_p_recomputation() -> None:
    assert p_from_statistic("t", 2.35, 18, None) == pytest.approx(0.0304, abs=1e-3)
    assert p_from_statistic("f", 4.20, 2, 57) == pytest.approx(0.0198, abs=1e-3)
    assert p_from_statistic("chi2", 7.82, 3, None) == pytest.approx(0.0499, abs=1e-3)
    assert p_from_statistic("unsupported", 1.0, 1, None) is None


def test_one_tailed_p_is_not_reported_as_an_error() -> None:
    """t(18) = 2.35 is p = .030 two-tailed and .015 one-tailed. Neither is wrong."""
    frame = pd.DataFrame([{"test": "t", "stat": 2.35, "df1": 18, "p": "0.015"}])
    finding = next(f for f in validate_reported_stats(frame) if f.check.startswith("Reported p"))
    assert finding.outcome == "clear"


def test_decision_error_is_escalated() -> None:
    frame = pd.DataFrame([{"test": "t", "stat": 2.35, "df1": 18, "p": "0.004"}])
    finding = next(f for f in validate_reported_stats(frame) if f.check.startswith("Reported p"))
    assert finding.outcome == "flag"
    assert finding.details["mismatch_count"] == 1


def test_checks_that_cannot_run_say_so() -> None:
    findings = validate_reported_stats(pd.DataFrame([{"test": "grim"}]))
    assert {f.outcome for f in findings} == {"not_applicable"}
    assert all(f.message for f in findings)
