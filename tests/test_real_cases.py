"""Validation against real published papers.

Each case reproduces the per-cell verdicts of a published forensic reanalysis.
The cells that reanalysis found *consistent* are the false-positive controls
and matter as much as the failures: a GRIM implementation that flags
everything would pass the positive half of this test and be useless.

See benchmarks/real_cases/README.md and each case's SOURCE.md.
"""

from __future__ import annotations

import pandas as pd
import pytest
from scifraudscan.detectors.reported_stats import grim_consistent, grimmer_consistent
from scifraudscan.utils import decimal_places

CASES = ("wansink_2014_buffet", "sigirci_wansink_2015_regret")


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
