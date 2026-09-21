from __future__ import annotations

import pytest
from scifraudscan.models import Finding, clear, flag, not_applicable


def test_a_flag_must_carry_a_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        Finding("X", "flag", "something", None)


def test_a_non_flag_must_not_carry_a_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        Finding("X", "clear", "nothing", "high")


def test_serialization_omits_empty_fields() -> None:
    assert clear("X", "nothing found").as_dict() == {
        "check": "X",
        "outcome": "clear",
        "message": "nothing found",
    }


def test_flag_serializes_severity_and_details() -> None:
    payload = flag("X", "high", "found it", count=3).as_dict()
    assert payload["severity"] == "high"
    assert payload["details"] == {"count": 3}


def test_not_applicable_carries_the_reason_in_the_message() -> None:
    finding = not_applicable("X", "needs 100 rows, got 4")
    assert finding.outcome == "not_applicable"
    assert "needs 100 rows" in finding.message


def test_every_report_carries_the_version_that_produced_it() -> None:
    """A finding has to be traceable to a build, since the thresholds change."""
    import pandas as pd
    from scifraudscan._version import __version__
    from scifraudscan.pipeline import scan

    result = scan(pd.DataFrame({"a": [1.0, 2.0, 3.0]}), groups=["duplication"])
    assert result["scifraudscan_version"] == __version__
