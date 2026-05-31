from __future__ import annotations

from fastapi.testclient import TestClient

from research_integrity_screen.reporting import finding_detail_lines
from research_integrity_screen.web import app


def test_detail_lines_show_specific_match() -> None:
    finding = {
        "score": 100,
        "details": {
            "matches": [
                {"left": "baseline", "right": "shifted", "slope": 1.0, "intercept": 5.0}
            ],
            "match_count": 1,
        },
    }

    lines = finding_detail_lines(finding)

    assert "match: left=baseline, right=shifted, slope=1.0, intercept=5.0" in lines
    assert "match count = 1" in lines


def test_detail_lines_skip_zero_score_findings() -> None:
    finding = {"score": 0, "details": {"duplicate_rows": 0, "duplicate_rate": 0.0}}

    assert finding_detail_lines(finding) == []


def test_web_scan_api_returns_detail_lines() -> None:
    client = TestClient(app)
    csv = b"a,b\n1,2\n2,4\n3,6\n4,8\n5,10\n"

    response = client.post(
        "/api/scan",
        files={"data": ("data.csv", csv, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"]
    assert any(
        finding.get("detail_lines")
        for section in payload["sections"]
        for finding in section["findings"]
    )
