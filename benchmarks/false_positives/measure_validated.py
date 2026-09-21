"""False-positive rate of the validated checks, on statistics from real data.

Measuring a false-positive rate normally needs data known to be sound, which
is exactly what is hard to get. This sidesteps that: take real raw data,
compute the summary statistics yourself, and round them the way a paper
would. The reporting is then correct by construction, so **every flag is a
demonstrable false positive** — no assumption about anyone's integrity is
involved.

    python benchmarks/false_positives/fetch_datasets.py
    python benchmarks/false_positives/measure_validated.py
"""

from __future__ import annotations

import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import numpy as np
import pandas as pd
from scifraudscan.detectors.randomization import reported_baseline_p_check
from scifraudscan.detectors.reported_stats import (
    grim_consistent,
    grimmer_consistent,
    mann_whitney_p_upper_bound,
    p_from_statistic,
)
from scipy import stats

warnings.filterwarnings("ignore")
DATA = pathlib.Path(__file__).resolve().parent / "rdata"


def main() -> None:
    rng = np.random.default_rng(3)
    files = sorted(DATA.glob("*.csv"))
    if not files:
        raise SystemExit("no datasets; run fetch_datasets.py first")

    counts = {name: [0, 0] for name in ("GRIM", "GRIMMER", "t", "U")}  # [cases, flags]
    baseline_rows: list[dict[str, object]] = []

    for path in files:
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        numeric = frame.select_dtypes("number").dropna(axis=1, how="all")
        if numeric.empty:
            continue

        for column in numeric.columns:
            values = numeric[column].dropna().to_numpy(float)
            if len(values) < 10 or not np.array_equal(values, np.rint(values)):
                continue
            if len(np.unique(values)) < 3:
                continue
            for _ in range(2):
                n = int(rng.integers(10, min(len(values), 200) + 1))
                sample = rng.choice(values, n, replace=False)
                places = int(rng.integers(1, 3))
                mean = f"{sample.mean():.{places}f}"
                sd = f"{sample.std(ddof=1):.{places}f}"
                counts["GRIM"][0] += 1
                if not grim_consistent(n, float(mean), places):
                    counts["GRIM"][1] += 1
                counts["GRIMMER"][0] += 1
                if not grimmer_consistent(n, float(mean), float(sd), places, places):
                    counts["GRIMMER"][1] += 1

        binary = [
            c for c in frame.columns
            if frame[c].nunique(dropna=True) == 2 and frame[c].notna().sum() > 20
        ]
        if not binary:
            continue
        group = binary[0]
        levels = frame[group].dropna().unique()[:2]
        for column in list(numeric.columns)[:6]:
            a = frame.loc[frame[group] == levels[0], column].dropna().to_numpy(float)
            b = frame.loc[frame[group] == levels[1], column].dropna().to_numpy(float)
            if len(a) < 8 or len(b) < 8 or (np.std(a) == 0 and np.std(b) == 0):
                continue
            places = int(rng.integers(1, 3))

            student = stats.ttest_ind(a, b, equal_var=True)
            if np.isfinite(student.statistic):
                counts["t"][0] += 1
                reported = float(f"{student.pvalue:.3f}")
                computed = p_from_statistic(
                    "t", float(student.statistic), len(a) + len(b) - 2, None
                )
                consistent = computed is not None and (
                    round(computed, 3) == round(reported, 3)
                    or round(computed / 2, 3) == round(reported, 3)
                )
                if not consistent:
                    counts["t"][1] += 1

            # real data, so this exercises the tie logic on genuine ties
            whitney = stats.mannwhitneyu(a, b, alternative="two-sided")
            if np.isfinite(whitney.pvalue):
                counts["U"][0] += 1
                reported = float(f"{whitney.pvalue:.4g}")
                bound = mann_whitney_p_upper_bound(
                    float(whitney.statistic), len(a), len(b)
                )
                if bound is not None and reported > bound + 0.005:
                    counts["U"][1] += 1

            # rounded summaries printed beside the p actually computed from raw data
            baseline_rows.append(
                {
                    "study": path.stem[:24],
                    "var": str(column)[:24],
                    "n1": len(a),
                    "n2": len(b),
                    "m1": f"{a.mean():.{places}f}",
                    "s1": f"{a.std(ddof=1):.{places}f}",
                    "m2": f"{b.mean():.{places}f}",
                    "s2": f"{b.std(ddof=1):.{places}f}",
                    "p": f"{stats.ttest_ind(a, b, equal_var=False).pvalue:.3f}",
                }
            )

    baseline = reported_baseline_p_check(pd.DataFrame(baseline_rows))
    counts["baseline p"] = [
        baseline.details.get("n_checked", 0),
        baseline.details.get("unreachable_count", 0),
    ]

    print(f"{len(files)} real datasets\n")
    print(f"  {'check':<34}{'cases':>7}{'flags':>9}{'FP rate':>10}")
    print("  " + "-" * 60)
    for name, (cases, flags) in counts.items():
        rate = f"{flags / cases:.2%}" if cases else "n/a"
        print(f"  {name:<34}{cases:>7}{flags:>9}{rate:>10}")


if __name__ == "__main__":
    main()
