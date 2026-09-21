"""The reference distribution for published baseline p-values.

Baseline p-values computed from rounded, published summary statistics are not
uniform even when the trial is honest. Testing them against a uniform null
flags honest papers, and at a few hundred variables it does so essentially
always. These tests pin that fact and the fix for it.
"""

from __future__ import annotations

import numpy as np
import pytest
from scifraudscan.detectors.randomization import (
    _carlisle_reference,
    _reference_monte_carlo,
    carlisle_reference_cdf,
)
from scipy import stats

ALPHA = 0.01


def _honest_sample(n: int, rng: np.random.Generator) -> np.ndarray:
    """Baseline p-values shaped like those in real published trials."""
    quantiles, cumulative = _carlisle_reference()
    return np.interp(rng.random(n), cumulative, quantiles)


def test_real_baseline_p_values_are_not_uniform() -> None:
    """The premise: 13% of real baseline p-values exceed 0.95, not 5%."""
    assert float(carlisle_reference_cdf(0.95)) == pytest.approx(0.869, abs=0.005)
    assert float(carlisle_reference_cdf(0.99)) == pytest.approx(0.889, abs=0.005)
    assert float(carlisle_reference_cdf(0.8)) == pytest.approx(0.763, abs=0.005)
    assert float(carlisle_reference_cdf(0.5)) == pytest.approx(0.491, abs=0.005)


def test_uniform_null_flags_an_honest_collection() -> None:
    """Why the uniform null was abandoned for published tables."""
    rng = np.random.default_rng(7)
    honest = _honest_sample(500, rng)
    uniform_verdict = stats.kstest(honest, "uniform", alternative="less").pvalue
    assert uniform_verdict < 0.001, "expected the uniform null to reject honest data here"

    too_balanced, _, _ = _reference_monte_carlo(honest, simulations=4000)
    assert too_balanced > ALPHA, "the reference test should not reject honest data"


def test_false_positive_rate_is_near_nominal() -> None:
    rng = np.random.default_rng(21)
    rejections = sum(
        _reference_monte_carlo(_honest_sample(200, rng), simulations=2000)[0] < ALPHA
        for _ in range(60)
    )
    assert rejections <= 3, f"{rejections}/60 honest collections flagged at alpha={ALPHA}"


def test_a_genuinely_too_balanced_collection_is_still_caught() -> None:
    rng = np.random.default_rng(5)
    detections = 0
    for _ in range(20):
        nudged = np.clip(_honest_sample(200, rng) + rng.uniform(0, 0.25, 200), 0, 1)
        detections += _reference_monte_carlo(nudged, simulations=2000)[0] < ALPHA
    assert detections >= 18, f"only {detections}/20 fabricated-looking collections detected"


def test_the_test_is_reproducible() -> None:
    rng = np.random.default_rng(1)
    sample = _honest_sample(80, rng)
    assert _reference_monte_carlo(sample, simulations=2000) == _reference_monte_carlo(
        sample, simulations=2000
    )
