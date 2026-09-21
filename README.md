# SciFraudScan

A Claude skill for screening research data and reported statistics for
anomaly signals: impossible means and SDs, p-values that disagree with their
test statistics, duplicated or derived columns, digit preference, implausible
baseline balance, and p-hacking signatures across a literature.

SciFraudScan 是一个科研诚信筛查 skill，用于从科研数据和论文报告的统计量中发现
异常信号。所有检查只产生**需要进一步核查的线索**，不构成对任何人的学术不端指控。

## Install

Clone into your skills directory, then:

```bash
pip install -r requirements.txt
```

Claude loads `SKILL.md` and drives `scripts/scan.py` from there. It also works
as a plain CLI:

```bash
python scripts/scan.py examples/fabricated_trial.csv \
  --group-column arm --time-column enrol_day \
  --reported-stats examples/reported_stats.csv \
  --p-values examples/p_values.csv
```

## What it checks

| Group | Checks |
|---|---|
| `reported_stats` | GRIM, GRIMMER + variance bounds, p-value recomputation |
| `authenticity` | Benford first digit, terminal digit preference, repeated increments |
| `duplication` | Exact and near-duplicate rows, linear-transform and permutation duplicates, repeated value blocks |
| `structure` | Constant difference, constant ratio, near-perfect correlation, over-regularity |
| `randomization` | Carlisle baseline balance (two-sided and too-balanced tests) |
| `covariance` | Near-collinear pairs, near-singular covariance |
| `timeseries` | Serial autocorrelation, spectral periodicity |
| `pvalues` | Caliper test, p-curve shape, excess significance |

The reported-statistics checks need no raw data — only the numbers printed in
the paper — and are the only ones that can show a result is *impossible*
rather than merely unusual.

## There is no risk score

Every check returns `flag`, `clear`, or `not_applicable`, with the numbers
behind it. There is no 0-100 total, because an average over checks lets
passing checks dilute a real finding and implies a calibration that does not
exist. [`references/METHODOLOGY.md`](references/METHODOLOGY.md) explains each
check's assumptions, minimum data, thresholds and failure modes — read it
before repeating any result.

## Benchmark

`examples/clean_trial.csv` is honestly generated; `examples/fabricated_trial.csv`
is the same trial with five defects planted in it.

| | clean | fabricated |
|---|---|---|
| flagged | **0** | 14 |
| clear | 15 | 7 |
| not applicable | 1 | 1 |

```bash
pytest                                   # includes this as a regression test
python benchmarks/generate_examples.py   # regenerate from a fixed seed
```

This shows the checks fire on what they claim to detect and stay quiet on
honest data of the same shape. It is **not** a real-world false positive rate:
nothing here has been validated against a corpus of retracted papers.

## Limitations

Screening signals only. No image forensics, no text or reference checks, no
full SPRITE search. The p-value checks need a body of results, not one study.
Roughly 22 checks run without correction for multiple comparisons, so some
flags on honest data are expected — severity and the per-check failure modes
matter far more than the count.

## License

MIT
