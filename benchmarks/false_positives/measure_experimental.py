"""How often the experimental checks fire on ordinary real datasets.

These are not provably false positives: real data can legitimately hold a
derived column or a repeated block. But these datasets are ordinary published
teaching and research data with no connection to misconduct, so a high rate
here means the check is describing something common rather than something
wrong. The measured rates are shipped in
scripts/scifraudscan/reference/experimental_base_rates.csv and printed next to
every experimental flag.

    python benchmarks/false_positives/fetch_datasets.py
    python benchmarks/false_positives/measure_experimental.py
"""

from __future__ import annotations

import collections
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import pandas as pd
from scifraudscan.pipeline import scan

warnings.filterwarnings("ignore")
DATA = pathlib.Path(__file__).resolve().parent / "rdata"


def main() -> None:
    files = sorted(DATA.glob("*.csv"))
    if not files:
        raise SystemExit("no datasets; run fetch_datasets.py first")

    fired: collections.Counter[str] = collections.Counter()
    ran: collections.Counter[str] = collections.Counter()
    any_flag = 0

    for path in files:
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        if frame.empty or frame.select_dtypes("number").empty:
            continue
        binary = [c for c in frame.columns if frame[c].nunique(dropna=True) == 2]
        try:
            result = scan(
                frame,
                group_column=binary[0] if binary else None,
                include_experimental=True,
            )
        except Exception:
            continue
        flagged_here = False
        for section in result["sections"]:
            for finding in section["findings"]:
                if finding["outcome"] == "not_applicable":
                    continue
                ran[finding["check"]] += 1
                if finding["outcome"] == "flag":
                    fired[finding["check"]] += 1
                    flagged_here = True
        any_flag += flagged_here

    print(f"{len(files)} ordinary real datasets\n")
    print(f"  {'experimental check':<42}{'ran':>6}{'fired':>7}{'rate':>8}")
    print("  " + "-" * 63)
    for check, total in sorted(ran.items(), key=lambda kv: -fired[kv[0]] / max(kv[1], 1)):
        print(f"  {check:<42}{total:>6}{fired[check]:>7}{fired[check] / total:>7.0%}")
    print(
        f"\n  at least one experimental flag: {any_flag}/{len(files)}"
        f" = {any_flag / len(files):.0%} of ordinary datasets"
    )


if __name__ == "__main__":
    main()
