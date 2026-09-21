#!/usr/bin/env python3
"""Command-line entry point for SciFraudScan.

    python scripts/scan.py data.csv --group-column arm --time-column visit_date
    python scripts/scan.py --reported-stats table1.csv --format json
    python scripts/scan.py data.csv --checks duplication,structure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from scifraudscan._version import __version__
from scifraudscan.pipeline import CHECK_GROUPS, scan
from scifraudscan.report import render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scan.py",
        description="Screen research data and reported statistics for anomaly signals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Check groups: " + ", ".join(CHECK_GROUPS),
    )
    parser.add_argument(
        "--version", action="version", version=f"scifraudscan {__version__}"
    )
    parser.add_argument("data", nargs="?", type=Path, help="Dataset CSV to scan.")
    parser.add_argument(
        "--reported-stats", type=Path, help="CSV of statistics as reported in the paper."
    )
    parser.add_argument("--p-values", type=Path, help="CSV of p-values, one per row.")
    parser.add_argument(
        "--baseline-summary",
        type=Path,
        help="CSV of a published baseline table: study, var, n1..n4, m1..m4, s1..s4, p.",
    )
    parser.add_argument("--group-column", help="Treatment/arm column, enables the Carlisle check.")
    parser.add_argument(
        "--time-column", help="Time or sequence column, enables the ordered checks."
    )
    parser.add_argument("--checks", help="Comma-separated subset of check groups to run.")
    parser.add_argument(
        "--assumed-power",
        type=float,
        default=0.5,
        help="Power assumed by the excess-significance test (default: 0.5).",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path, help="Write the report here instead of stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not any([args.data, args.reported_stats, args.p_values, args.baseline_summary]):
        build_parser().error(
            "provide a dataset CSV, --reported-stats, --p-values, or --baseline-summary"
        )

    groups = [g.strip() for g in args.checks.split(",") if g.strip()] if args.checks else None
    try:
        result = scan(
            _read(args.data),
            groups=groups,
            reported_stats=_read(args.reported_stats),
            p_values=_read(args.p_values),
            baseline_summary=_read(args.baseline_summary),
            group_column=args.group_column,
            time_column=args.time_column,
            assumed_power=args.assumed_power,
        )
    except (ValueError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    rendered = (
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.format == "json"
        else render_text(result)
    )
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


def _read(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"no such file: {path}")
    return pd.read_csv(path)


if __name__ == "__main__":
    raise SystemExit(main())
