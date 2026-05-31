from __future__ import annotations

from typing import Any


def render_text_report(report: dict[str, Any]) -> str:
    lines = [
        "SciFraudScan",
        f"Research Integrity Score: {report['research_integrity_score']} / 100",
        f"Overall Risk: {report['overall_risk']}",
        "",
    ]
    for section in report["sections"]:
        lines.append(f"{section['name']}: {section['status']} ({section['score']} / 100)")
        for finding in section["findings"]:
            lines.append(f"  - {finding['check']}: {finding['status']} ({finding['score']})")
            lines.append(f"    {finding['message']}")
            detail_lines = finding_detail_lines(finding)
            if detail_lines:
                lines.append("    Abnormal indicators:")
                lines.extend(f"      * {line}" for line in detail_lines)
        lines.append("")
    return "\n".join(lines).rstrip()


def finding_detail_lines(finding: dict[str, Any], limit: int = 6) -> list[str]:
    if float(finding.get("score") or 0) <= 0:
        return []

    details = finding.get("details") or {}
    if not isinstance(details, dict):
        return []

    lines: list[str] = []
    for key in ("matches", "columns", "failures", "mismatches", "variables"):
        items = details.get(key)
        if isinstance(items, list) and items:
            lines.extend(_format_items(key, items[:limit]))
            total_key = _count_key(key)
            total = details.get(total_key)
            if isinstance(total, int) and total > limit:
                lines.append(f"{total - limit} more {key.replace('_', ' ')} not shown")

    for key in (
        "duplicate_rows",
        "duplicate_rate",
        "pair_count",
        "max_similarity",
        "match_count",
        "column_count",
        "failure_count",
        "mismatch_count",
        "near_threshold",
        "significant_count",
        "rate",
        "observed",
        "expected",
        "binomial_p",
        "ks_p_value",
        "too_similar_count",
        "too_different_count",
        "high_correlation_rate",
        "near_identity_rate",
        "condition_number",
        "top_digit",
        "top_rate",
        "entropy",
        "chi_square",
        "p_value",
        "mad",
    ):
        if key in details and _is_signal_value(details[key]):
            lines.append(f"{_label(key)} = {details[key]}")

    observed = details.get("observed")
    expected = details.get("expected_probabilities")
    if isinstance(observed, list) and isinstance(expected, list):
        lines.append(f"leading digit counts 1-9 = {observed}")
        lines.append(f"Benford expected probabilities 1-9 = {expected}")

    counts = details.get("counts")
    if isinstance(counts, list):
        lines.append(f"terminal digit counts 0-9 = {counts}")

    return _dedupe(lines)[: limit * 3]


def _format_items(key: str, items: list[Any]) -> list[str]:
    lines = []
    for item in items:
        if isinstance(item, dict):
            lines.append(f"{_item_label(key)}: {_format_dict(item)}")
        else:
            lines.append(f"{_item_label(key)}: {item}")
    return lines


def _format_dict(item: dict[str, Any]) -> str:
    return ", ".join(f"{_label(key)}={value}" for key, value in item.items())


def _label(key: str) -> str:
    return key.replace("_", " ")


def _item_label(key: str) -> str:
    return {
        "matches": "match",
        "columns": "column",
        "failures": "failure",
        "mismatches": "mismatch",
        "variables": "variable",
    }.get(key, key.replace("_", " "))


def _count_key(key: str) -> str:
    if key == "columns":
        return "column_count"
    if key == "mismatches":
        return "mismatch_count"
    if key == "failures":
        return "failure_count"
    return "match_count"


def _is_signal_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _dedupe(lines: list[str]) -> list[str]:
    seen = set()
    unique = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        unique.append(line)
    return unique
