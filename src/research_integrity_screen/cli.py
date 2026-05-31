from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from research_integrity_screen.pipeline import scan_dataframe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="riskscan")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan a research dataset CSV for anomaly signals.")
    scan.add_argument("data", type=Path, help="CSV dataset to scan.")
    scan.add_argument("--reported-stats", type=Path, help="CSV with reported GRIM/SPRITE/statcheck rows.")
    scan.add_argument("--p-values", type=Path, help="CSV containing p-values.")
    scan.add_argument("--group-column", help="Treatment/group column for Carlisle-style baseline checks.")
    scan.add_argument("--time-column", help="Time/order column for time-series checks.")
    scan.add_argument("--format", choices=["text", "json"], default="text")
    scan.add_argument("--output", type=Path, help="Optional output report path.")

    args = parser.parse_args(argv)
    if args.command == "scan":
        report = _run_scan(args)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else _text(report)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    return 1


def _run_scan(args: argparse.Namespace) -> dict[str, Any]:
    df = pd.read_csv(args.data)
    reported_stats = pd.read_csv(args.reported_stats) if args.reported_stats else None
    p_values = pd.read_csv(args.p_values) if args.p_values else None
    return scan_dataframe(
        df,
        reported_stats=reported_stats,
        p_values=p_values,
        group_column=args.group_column,
        time_column=args.time_column,
    )


def _text(report: dict[str, Any]) -> str:
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
        lines.append("")
    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    raise SystemExit(main())
