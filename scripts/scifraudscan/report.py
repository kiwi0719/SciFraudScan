"""Plain-text rendering of a scan result."""

from __future__ import annotations

from typing import Any

MARKERS = {"flag": "[FLAG]", "clear": "[ok]  ", "not_applicable": "[n/a] "}
GROUP_TITLES = {
    "authenticity": "Digit authenticity",
    "duplication": "Duplication",
    "structure": "Structural relationships",
    "randomization": "Randomization",
    "covariance": "Covariance structure",
    "timeseries": "Sequential structure",
    "reported_stats": "Reported statistics",
    "pvalues": "P-value distribution",
    "baseline_p": "Published baseline table — reported p-values",
    "baseline_balance": "Published baseline table — balance",
}
DISCLAIMER = (
    "These are statistical screening signals, not findings of misconduct. Every flag has "
    "innocent explanations and must be checked against the study's methods before it means "
    "anything. A clear result is not reassurance either: these checks test whether numbers "
    "are consistent with each other, and fabricated data processed by software is "
    "consistent with itself."
)


def render_text(result: dict[str, Any], show_details: bool = True) -> str:
    summary = result["summary"]
    inputs = result["inputs"]
    version = result.get("scifraudscan_version", "")
    lines = [f"SciFraudScan {version}".rstrip(), "=" * 60, ""]

    lines.append(
        f"Input: {inputs['rows']} rows, {len(inputs['columns'])} columns"
        + (
            f", {inputs['reported_stats_rows']} reported-statistic rows"
            if inputs["reported_stats_rows"]
            else ""
        )
        + (f", {inputs['p_value_count']} p-values" if inputs["p_value_count"] else "")
    )
    if inputs["group_column"]:
        lines.append(f"Group column: {inputs['group_column']}")
    if inputs["time_column"]:
        lines.append(f"Time column: {inputs['time_column']}")
    lines.append(
        f"Result: {summary['flagged']} flagged, {summary['cleared']} clear, "
        f"{summary['not_applicable']} not applicable"
        + (
            f" (highest severity: {summary['highest_severity']})"
            if summary["highest_severity"]
            else ""
        )
    )
    lines.append("")

    if not result["sections"]:
        lines.append("Nothing was run.")
        lines.append("-" * 60)
        lines.append(
            "The checks that run by default are the arithmetic ones, and they work from"
        )
        lines.append(
            "statistics as a paper reports them: --reported-stats for means, SDs and test"
        )
        lines.append(
            "statistics, --baseline-summary for a trial's baseline table. A raw dataset on"
        )
        lines.append(
            "its own reaches only the experimental checks; pass --experimental to run those,"
        )
        lines.append("having read what that means in references/METHODOLOGY.md.")
        lines.append("")
        lines.append("-" * 60)
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    for section in result["sections"]:
        experimental = section.get("validation", "").startswith("none")
        title = GROUP_TITLES.get(section["group"], section["group"])
        lines.append(f"{title}   [EXPERIMENTAL]" if experimental else title)
        lines.append("-" * 60)
        if experimental:
            lines.append(
                "        No real-case validation: how often these fire on sound data"
            )
            lines.append("        is not known. Weigh them accordingly.")
        for finding in section["findings"]:
            marker = MARKERS.get(finding["outcome"], "      ")
            severity = f" ({finding['severity']})" if finding.get("severity") else ""
            lines.append(f"{marker} {finding['check']}{severity}")
            rate = finding.get("fires_on_ordinary_data")
            if rate is not None and finding["outcome"] == "flag":
                lines.append(
                    f"        NOTE: this check fires on {rate:.0%} of ordinary real "
                    "datasets that have nothing to do with misconduct."
                )
            lines.append(f"        {finding['message']}")
            if show_details and finding["outcome"] == "flag":
                lines.extend(_detail_lines(finding.get("details", {})))
        lines.append("")

    lines.append("-" * 60)
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _detail_lines(details: dict[str, Any], limit: int = 6) -> list[str]:
    lines: list[str] = []
    for key, value in list(details.items())[:limit]:
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"          {key}:")
            for item in value[:3]:
                lines.append(f"            - {item}")
            if len(value) > 3:
                lines.append(f"            ... {len(value) - 3} more")
        else:
            lines.append(f"          {key}: {value}")
    return lines
