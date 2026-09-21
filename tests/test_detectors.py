"""Unit tests for the data-side detectors, including the false positives the
benchmark caught during development."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scifraudscan.detectors.authenticity import (
    benford_law,
    digit_preference,
    repeated_increments,
)
from scifraudscan.detectors.duplication import (
    exact_duplicates,
    linear_transformation_duplicates,
    permutation_duplicates,
)
from scifraudscan.detectors.pvalues import p_curve_shape, threshold_clustering
from scifraudscan.detectors.structure import constant_difference, over_regularity
from scifraudscan.utils import is_index_like, terminal_digits


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(1234)


def test_exact_duplicates_reports_the_rows() -> None:
    frame = pd.DataFrame({"a": [1, 2, 1, 4], "b": ["x", "y", "x", "z"]})
    finding = exact_duplicates(frame)
    assert finding.outcome == "flag"
    assert finding.details["duplicate_rows"] == 2


def test_linear_transformation_is_caught_with_the_coefficients() -> None:
    base = np.arange(30, dtype=float)
    finding = linear_transformation_duplicates(pd.DataFrame({"a": base, "b": base * 2.5 + 7}))
    assert finding.outcome == "flag"
    assert finding.details["matches"][0]["slope"] == pytest.approx(2.5)
    assert finding.details["matches"][0]["intercept"] == pytest.approx(7.0)


def test_permutation_duplicate_needs_a_reordering_not_a_copy() -> None:
    values = np.arange(12, dtype=float)
    identical = pd.DataFrame({"a": values, "b": values})
    assert permutation_duplicates(identical).outcome == "clear"
    shuffled = pd.DataFrame({"a": values, "b": values[::-1]})
    assert permutation_duplicates(shuffled).outcome == "flag"


def test_constant_difference_reports_the_offset() -> None:
    base = np.arange(20, dtype=float)
    finding = constant_difference(pd.DataFrame({"a": base, "b": base + 3}))
    assert finding.outcome == "flag"
    assert finding.details["matches"][0]["difference"] == pytest.approx(3.0)


def test_benford_refuses_narrow_range_data(rng) -> None:
    """A bounded measurement does not follow Benford's law even when honest."""
    frame = pd.DataFrame({"bp": rng.normal(130, 15, 400)})
    assert benford_law(frame).outcome == "not_applicable"


def test_benford_does_not_run_unless_the_caller_asserts_it_applies(rng) -> None:
    """Whether a variable is scale-invariant is a fact about the world.

    Left to decide for itself, Benford fired on 74% of the real datasets where
    it was eligible. It now runs only on request.
    """
    wide = 10 ** rng.uniform(0, 5, 2000)
    assert benford_law(pd.DataFrame({"amount": wide})).outcome == "not_applicable"


def test_benford_runs_on_wide_range_data_and_stays_moderate(rng) -> None:
    conforming = 10 ** rng.uniform(0, 5, 2000)
    finding = benford_law(pd.DataFrame({"amount": conforming}), scale_invariant=True)
    assert finding.outcome == "clear"
    leading_ones = np.concatenate([rng.uniform(1, 2, 1500) * 10 ** rng.integers(0, 5, 1500),
                                   10 ** rng.uniform(0, 5, 500)])
    flagged = benford_law(pd.DataFrame({"amount": leading_ones}), scale_invariant=True)
    assert flagged.outcome == "flag"
    assert flagged.severity == "moderate"  # never stronger than that, by design


def test_terminal_digits_count_trailing_zeros() -> None:
    """54.0 in a one-decimal column ends in 0, not 4."""
    assert terminal_digits(np.array([54.0, 54.3, 12.0])).tolist() == [0, 3, 0]
    assert terminal_digits(np.array([54.0, 12.0])).tolist() == [4, 2]


def test_digit_preference_clears_honest_data(rng) -> None:
    frame = pd.DataFrame({"value": np.round(rng.normal(50, 10, 600), 1)})
    assert digit_preference(frame).outcome == "clear"


def test_wholly_coarse_columns_are_untestable_not_positive(rng) -> None:
    """Every value ending in 0 or 5 fits a scale marked in fives just as well
    as rounding by hand, and the data cannot say which. Treating it as
    positive flagged 100% of such columns in real data."""
    values = np.round(rng.normal(50, 10, 600) * 2) / 2
    finding = digit_preference(pd.DataFrame({"value": values}))
    assert finding.outcome == "not_applicable"
    assert finding.details["coarse_columns"]


def test_digit_preference_needs_to_beat_real_published_data(rng) -> None:
    """Partial heaping is testable, but has to clear what real columns do.

    At the old threshold of V >= 0.10, 40% of real full-precision columns were
    flagged. The threshold is now the 97.5% quantile of real columns, measured
    on 150 datasets and checked on 150 held out, where it fires on 8%.
    """
    values = np.round(rng.normal(50, 10, 600), 1)
    nudge = rng.random(600) < 0.6
    values[nudge] = np.round(values[nudge] * 2) / 2
    moderate = digit_preference(pd.DataFrame({"value": values}))
    assert moderate.outcome == "clear"
    assert moderate.details["evaluated_columns"][0]["percentile_among_real_columns"] > 0.5

    extreme = np.round(rng.normal(50, 10, 600), 1)
    heap = rng.random(600) < 0.93
    extreme[heap] = np.round(extreme[heap])
    assert digit_preference(pd.DataFrame({"value": extreme})).outcome in {
        "flag",
        "not_applicable",
    }


def test_index_columns_are_not_treated_as_measurements() -> None:
    assert is_index_like(np.arange(100, dtype=float))
    assert is_index_like(np.array([2.0, 4.0, 6.0, 8.0]))
    assert not is_index_like(np.array([1.0, 2.0, 2.0, 5.0]))  # repeats
    assert not is_index_like(np.array([1.5, 2.5, 3.5]))       # not integers

    counter = pd.DataFrame({"row_id": np.arange(1, 241, dtype=float)})
    assert over_regularity(counter).outcome == "clear"
    assert repeated_increments(counter).outcome == "clear"


def test_over_regularity_is_scale_invariant() -> None:
    """The same series in different units must give the same verdict."""
    ramp = np.arange(40, dtype=float) * 3.0 + np.array([0.001] * 40)
    small = over_regularity(pd.DataFrame({"a": ramp, "b": np.arange(40.0) ** 2}))
    large = over_regularity(pd.DataFrame({"a": ramp * 1e6, "b": np.arange(40.0) ** 2}))
    assert small.outcome == large.outcome == "flag"
    assert small.details["columns"][0]["column"] == "a"


def test_caliper_test_needs_enough_p_values_near_the_threshold() -> None:
    sparse = np.array([0.01, 0.046, 0.2, 0.5])
    assert threshold_clustering(sparse).outcome == "not_applicable"


def test_caliper_test_detects_a_pile_up_just_below_05() -> None:
    p_values = np.concatenate([np.full(24, 0.047), np.full(4, 0.052)])
    finding = threshold_clustering(p_values)
    assert finding.outcome == "flag"
    assert finding.details["inside"] == 24


def test_p_curve_clears_a_real_effect(rng) -> None:
    """A genuine effect gives a right-skewed p-curve, which must not flag."""
    strong = rng.beta(0.4, 8.0, 200)
    assert p_curve_shape(strong).outcome == "clear"
