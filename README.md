# SciFraudScan

[![CI](https://github.com/kiwi0719/SciFraudScan/actions/workflows/ci.yml/badge.svg)](https://github.com/kiwi0719/SciFraudScan/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

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

Every report carries the version that produced it, so a finding can be traced
back to a build:

```
$ python scripts/scan.py --reported-stats table1.csv
SciFraudScan 0.2.0
============================================================

Input: 0 rows, 0 columns, 30 reported-statistic rows
Result: 2 flagged, 0 clear, 1 not applicable (highest severity: high)

Reported statistics
------------------------------------------------------------
[FLAG] GRIM (high)
        10 of 30 reported means cannot arise from N responses on the stated scale.
          failures:
            - {'row': 0, 'n': 18, 'reported_mean': 2.63, 'decimals': 2, 'reason': 'no set of n responses rounds to this mean'}
            ... 9 more
[FLAG] SD Feasibility (GRIMMER / variance bounds) (high)
        8 of 20 testable mean/SD pairs are impossible; an SD is testable only
        where the mean itself is attainable.
[n/a]  Reported p-value Consistency
        No row supplied a test statistic, its df and a reported p-value.

------------------------------------------------------------
These are statistical screening signals, not findings of misconduct. Every flag
has innocent explanations and must be checked against the study's methods
before it means anything.
```

That is real output, from the retracted paper in `benchmarks/real_cases/`.

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
honest data of the same shape.

### Real published cases

`benchmarks/real_cases/` validates the reported-statistics checks against real
papers whose numbers have already been examined in the peer-reviewed
literature, cell by cell, against the verdicts that reanalysis reached:

| Case | Status | What is checked | Result |
|---|---|---|---|
| Sigirci & Wansink (2015), *BMC Nutrition* | **Retracted** 2017 | GRIM / GRIMMER, 30 means + 20 SDs | 30/30, 20/20 match published verdicts |
| Just, Sigirci & Wansink (2014), *J Sensory Studies* | Corrected 2017 | GRIM / GRIMMER, 28 cells | 28/28 match published verdicts |
| Sato / Iwamoto trials | **Retracted** (20+ papers) | Baseline tables, 50 variables | 5 of 10 printed p-values unreachable; balance test **does not fire** |

The Wansink verdicts come from [van der Zee, Anaya & Brown (2017)](https://doi.org/10.1186/s40795-017-0167-x),
cross-checked against the reanalysis authors'
[own repository](https://github.com/OmnesRes/pizzapizza). The Sato/Iwamoto
baseline data is the `SI_pvals_cont` dataset from Mark Bolland's MIT-licensed
[reappraised](https://cran.r-project.org/package=reappraised) package. About
half of all these cells are values that should *not* be flagged, so the
false-positive side is tested too. Each case's `SOURCE.md` records the DOIs,
the editorial outcome, and where every number came from.

**The Sato case includes a negative result and it is kept.** On those 50
baseline variables the balance test returns `clear` (mean p = 0.567 against
0.516 in real published trials; Monte-Carlo p = 0.13). A 10% sample is too
small for the test to have power. No threshold was moved to make it fire; the
p-value reachability check, which assumes nothing about the distribution,
carried that case instead.

Chasing that negative result turned up a worse problem, since fixed:
**baseline p-values from published, rounded summary statistics are not
uniformly distributed even when the trial is honest.** In Carlisle's corpus of
29,789 real baseline variables, 13.1% exceed 0.95 against 5% under a uniform
null. Tested against uniform, honest collections of 500 baseline variables
were flagged **100% of the time**. Published tables are now compared against
that empirical distribution instead, which holds the false positive rate near
1% while still detecting a genuinely too-balanced collection 99% of the time.
See [`scripts/scifraudscan/reference/README.md`](scripts/scifraudscan/reference/README.md).

Still narrow: the arithmetic checks are validated on three real cases from two
research groups. Duplication, digit preference and the sequential checks have
no real-case validation, and there is no general false positive rate.

## Limitations

Screening signals only. No image forensics, no text or reference checks, no
full SPRITE search. The p-value checks need a body of results, not one study.
Roughly 22 checks run without correction for multiple comparisons, so some
flags on honest data are expected — severity and the per-check failure modes
matter far more than the count.

## Citing this

`CITATION.cff` has the metadata. If you use it in published work, cite the
original methods too — they are listed with their sources in
[`references/METHODOLOGY.md`](references/METHODOLOGY.md). This is an
implementation of other people's statistics.

## License

MIT
