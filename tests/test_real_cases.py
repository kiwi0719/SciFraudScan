"""Validation against real published papers.

Each case reproduces the per-cell verdicts of a published forensic reanalysis.
The cells that reanalysis found *consistent* are the false-positive controls
and matter as much as the failures: a GRIM implementation that flags
everything would pass the positive half of this test and be useless.

See benchmarks/real_cases/README.md and each case's SOURCE.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scifraudscan.detectors.randomization import (
    baseline_summary_check,
    reported_baseline_p_check,
)
from scifraudscan.detectors.reported_stats import (
    grim_consistent,
    grimmer_consistent,
    mann_whitney_p_upper_bound,
    validate_reported_stats,
)
from scifraudscan.utils import decimal_places
from scipy import stats


def _load(real_cases_dir, case: str) -> pd.DataFrame:
    return pd.read_csv(real_cases_dir / case / "reported_stats.csv", dtype=str)


def _verdict(consistent: bool) -> str:
    return "consistent" if consistent else "inconsistent"


def _grim(row: pd.Series) -> bool:
    step = float(row["scale_step"]) if pd.notna(row.get("scale_step")) else 1.0
    return grim_consistent(int(row["n"]), float(row["mean"]), decimal_places(row["mean"]), step)


@pytest.fixture(scope="module")
def buffet(real_cases_dir) -> pd.DataFrame:
    return _load(real_cases_dir, "wansink_2014_buffet")


@pytest.fixture(scope="module")
def regret(real_cases_dir) -> pd.DataFrame:
    return _load(real_cases_dir, "sigirci_wansink_2015_regret")


def test_buffet_matches_published_verdicts(buffet: pd.DataFrame) -> None:
    """Just, Sigirci & Wansink (2014), corrected; 28 cells from van der Zee et al."""
    disagreements = []
    for _, row in buffet.iterrows():
        consistent = _grim(row)
        if consistent and pd.notna(row["sd"]):
            consistent = grimmer_consistent(
                int(row["n"]), float(row["mean"]), float(row["sd"]),
                decimal_places(row["mean"]), decimal_places(row["sd"]),
            )
        if _verdict(consistent) != row["published_verdict"]:
            disagreements.append(
                f"n={row['n']} mean={row['mean']} sd={row['sd']} "
                f"({row['source_location']}): we say {_verdict(consistent)}, "
                f"published says {row['published_verdict']}"
            )
    assert not disagreements, "\n".join(disagreements)
    assert len(buffet) == 28
    assert (buffet["published_verdict"] == "inconsistent").sum() == 13


def test_regret_means_match_published_verdicts(regret: pd.DataFrame) -> None:
    """Sigirci & Wansink (2015), RETRACTED; Table 2, 30 cells."""
    disagreements = [
        f"n={row['n']} mean={row['mean']} ({row['item']}, {row['source_location']}): "
        f"we say {_verdict(_grim(row))}, published says {row['published_mean_verdict']}"
        for _, row in regret.iterrows()
        if _verdict(_grim(row)) != row["published_mean_verdict"]
    ]
    assert not disagreements, "\n".join(disagreements)
    assert len(regret) == 30
    assert (regret["published_mean_verdict"] == "inconsistent").sum() == 10


def test_regret_sds_match_where_the_mean_is_attainable(regret: pd.DataFrame) -> None:
    """GRIMMER says nothing independent about the SD once the mean is impossible."""
    disagreements = []
    checked = 0
    for _, row in regret.iterrows():
        if not _grim(row):
            continue
        checked += 1
        consistent = grimmer_consistent(
            int(row["n"]), float(row["mean"]), float(row["sd"]),
            decimal_places(row["mean"]), decimal_places(row["sd"]),
        )
        if _verdict(consistent) != row["published_sd_verdict"]:
            disagreements.append(
                f"n={row['n']} mean={row['mean']} sd={row['sd']} ({row['item']}): "
                f"we say {_verdict(consistent)}, published says {row['published_sd_verdict']}"
            )
    assert not disagreements, "\n".join(disagreements)
    assert checked == 20


def test_percentages_need_the_right_granularity(buffet: pd.DataFrame) -> None:
    """A percentage of N diners moves in steps of 100/N, not 1/N.

    Both gender cells are impossible, but only when scale_step is 100. Treating
    a percentage as an ordinary mean makes them look fine.
    """
    gender = buffet[buffet["item"].fillna("").str.contains("percent male")]
    assert len(gender) == 2
    for _, row in gender.iterrows():
        n, value, decimals = int(row["n"]), float(row["mean"]), decimal_places(row["mean"])
        assert grim_consistent(n, value, decimals, 100.0) is False
        assert grim_consistent(n, value, decimals, 1.0) is True  # the wrong answer


# --- Sato / Iwamoto retracted trials: published baseline tables ---------------


@pytest.fixture(scope="module")
def sato(real_cases_dir) -> pd.DataFrame:
    return pd.read_csv(
        real_cases_dir / "sato_iwamoto_baselines" / "baseline_summary.csv", dtype=str
    )


def test_sato_reported_baseline_p_values_are_unreachable(sato: pd.DataFrame) -> None:
    """5 of 10 printed p-values cannot come from the statistics printed beside them."""
    finding = reported_baseline_p_check(sato)
    assert finding.outcome == "flag"
    assert finding.severity == "high"
    assert finding.details["n_checked"] == 10
    assert finding.details["unreachable_count"] == 5
    unreachable = {
        (v["study"], v["variable"]) for v in finding.details["variables"] if v["unreachable"]
    }
    assert unreachable == {
        ("H3", "Intact side"),
        ("H3", "Intact BGP (ng/mL)"),
        ("H30", "Intact side"),
        ("H30", "Ionized calcium (mEq/L)"),
        ("H30", "Deoxypyridinoline"),
    }


def test_sato_reachable_p_values_are_not_flagged(sato: pd.DataFrame) -> None:
    """The five reachable ones are the false-positive control for this case."""
    finding = reported_baseline_p_check(sato)
    reachable = [v for v in finding.details["variables"] if not v["unreachable"]]
    assert len(reachable) == 5
    for entry in reachable:
        tolerance = entry["reported_p_tolerance"]
        assert entry["reported_p"] + tolerance >= entry["reachable_p_min"]
        assert entry["reported_p"] - tolerance <= entry["reachable_p_max"]


def test_sato_baseline_balance_does_not_fire_and_that_is_recorded(sato: pd.DataFrame) -> None:
    """A negative result on real fabricated data, pinned so it cannot drift silently.

    50 variables is a 10% sample of the set Bolland et al. analysed, and the
    test has little power at that size. Note how small the excess is once the
    right reference is used: 30% of these p-values exceed 0.8, against 23.7%
    in real published trials -- not the 20% a uniform null would assume. See
    the case's SOURCE.md. If a change makes this fire, that change needs
    justifying on its own merits, not because it improved this number.
    """
    finding = baseline_summary_check(sato)
    assert finding.outcome == "clear"
    assert finding.details["variable_count"] == 50
    assert finding.details["observed_mean_p"] == pytest.approx(0.567, abs=0.005)
    assert finding.details["reference_mean_p"] == pytest.approx(0.516, abs=0.005)
    assert finding.details["observed_proportion_above_0_8"] == pytest.approx(0.30, abs=0.01)
    assert finding.details["reference_proportion_above_0_8"] == pytest.approx(0.237, abs=0.005)


def test_honest_summary_table_is_not_flagged() -> None:
    """False-positive control: p-values computed correctly are always reachable."""
    rng = np.random.default_rng(11)
    rows = []
    for i in range(30):
        n1 = n2 = int(rng.integers(30, 120))
        # Both arms are drawn from one population, as randomization implies, so
        # the arm means differ only by sampling error.
        population_mean, population_sd = rng.normal(50, 10), rng.uniform(5, 15)
        standard_error = population_sd / np.sqrt(n1)
        m1 = rng.normal(population_mean, standard_error)
        m2 = rng.normal(population_mean, standard_error)
        s1 = population_sd * rng.uniform(0.9, 1.1)
        s2 = population_sd * rng.uniform(0.9, 1.1)
        p = stats.ttest_ind_from_stats(m1, s1, n1, m2, s2, n2, equal_var=False).pvalue
        rows.append(
            {"study": f"T{i}", "var": "x", "n1": n1, "n2": n2,
             "m1": round(m1, 2), "m2": round(m2, 2),
             "s1": round(s1, 2), "s2": round(s2, 2), "p": round(float(p), 2)}
        )
    table = pd.DataFrame(rows)
    assert reported_baseline_p_check(table).outcome == "clear"
    assert baseline_summary_check(table).outcome == "clear"


# --- anonymous case: real reported Mann-Whitney comparisons --------------------


@pytest.fixture(scope="module")
def anonymous_utests(real_cases_dir) -> pd.DataFrame:
    return pd.read_csv(real_cases_dir / "anonymous_utests" / "reported_stats.csv", dtype=str)


def test_real_reported_u_tests_mostly_pass(anonymous_utests: pd.DataFrame) -> None:
    """29 of 30 real reported p-values are consistent with their own U statistic.

    This is NOT a false-positive control: the integrity of the source paper has
    not been independently established, so "these passed" cannot be evidence
    that passing is correct. It pins behaviour on real input. See SOURCE.md.
    """
    finding = next(
        f
        for f in validate_reported_stats(anonymous_utests)
        if f.check.startswith("Reported p")
    )
    assert finding.details["n_checked"] == 30
    assert finding.details["mismatch_count"] == 1, (
        "expected exactly one inconsistency; see the case's SOURCE.md before "
        "accepting any change to this number"
    )
    assert finding.details["decision_error_count"] == 0


def test_a_reported_p_below_the_bound_is_never_flagged(
    anonymous_utests: pd.DataFrame,
) -> None:
    """Ties only move p downward, so a p under the bound cannot be called impossible.

    Correct by construction, independently of whether the source paper is sound.
    """
    below = 0
    for _, row in anonymous_utests.iterrows():
        bound = mann_whitney_p_upper_bound(float(row["stat"]), int(row["n1"]), int(row["n2"]))
        if float(row["p"]) < bound / 10:
            below += 1
    assert below >= 4, "expected several rows well under the bound in this case"
    finding = next(
        f
        for f in validate_reported_stats(anonymous_utests)
        if f.check.startswith("Reported p")
    )
    flagged = {m["reported_p"] for m in finding.details["mismatches"]}
    for _, row in anonymous_utests.iterrows():
        bound = mann_whitney_p_upper_bound(float(row["stat"]), int(row["n1"]), int(row["n2"]))
        if float(row["p"]) < bound:
            assert float(row["p"]) not in flagged
