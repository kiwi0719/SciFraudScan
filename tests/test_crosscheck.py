"""Agreement with an independent implementation of the same published methods.

Everything else here was written by the author of the code under test. These
verdicts come from scrutiny 0.6.1, the R reference implementation of GRIM and
GRIMMER. See benchmarks/crosscheck/README.md.
"""

from __future__ import annotations

import csv

import pytest
from scifraudscan.detectors.reported_stats import grim_consistent, grimmer_consistent
from scifraudscan.utils import decimal_places


@pytest.fixture(scope="module")
def cases(real_cases_dir) -> list[dict[str, str]]:
    path = real_cases_dir.parent / "crosscheck" / "scrutiny_grim_grimmer.csv"
    with path.open() as fh:
        return list(csv.DictReader(fh))


def test_grim_agrees_exactly_with_scrutiny(cases) -> None:
    disagreements = [
        f"n={c['n']} mean={c['mean']}: ours={ours}, scrutiny={c['scrutiny_grim'] == '1'}"
        for c in cases
        if (ours := grim_consistent(int(c["n"]), float(c["mean"]), decimal_places(c["mean"])))
        != (c["scrutiny_grim"] == "1")
    ]
    assert not disagreements, "\n".join(disagreements[:10])
    assert len(cases) == 800
    # both verdicts have to be well represented or the test proves nothing
    impossible = sum(1 for c in cases if c["scrutiny_grim"] == "0")
    assert 200 < impossible < 600


def test_grimmer_never_rejects_where_scrutiny_accepts(cases) -> None:
    """Ours is the weaker test. It may miss, but it must not over-reject.

    scrutiny implements the published refinements; this implementation has the
    basic integer sum-of-squares and parity conditions only. Disagreement is
    expected, in one direction only.
    """
    over_rejections = []
    misses = 0
    for c in cases:
        ours = grimmer_consistent(
            int(c["n"]),
            float(c["mean"]),
            float(c["sd"]),
            decimal_places(c["mean"]),
            decimal_places(c["sd"]),
        )
        reference = c["scrutiny_grimmer"] == "1"
        if reference and not ours:
            over_rejections.append(f"n={c['n']} mean={c['mean']} sd={c['sd']}")
        if ours and not reference:
            misses += 1
    assert not over_rejections, (
        "we call these impossible but scrutiny does not:\n" + "\n".join(over_rejections[:10])
    )
    assert misses / len(cases) < 0.05, (
        f"our GRIMMER now misses {misses / len(cases):.1%} of what scrutiny catches; "
        "the documented gap is about 2.6%"
    )
