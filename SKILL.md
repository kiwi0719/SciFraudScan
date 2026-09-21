---
name: scifraudscan
description: Screen research data and reported statistics for anomaly signals — GRIM/GRIMMER feasibility of reported means and SDs, statcheck-style p-value recomputation, duplication and derived columns, terminal-digit preference, Carlisle baseline balance, p-curve and caliper tests. Use when asked to check a dataset, paper, table or supplementary file for signs of fabrication, data manipulation, p-hacking, or reporting errors; when verifying whether a reported mean, SD or p-value is arithmetically possible; or when reviewing a submission's statistics.
---

# SciFraudScan

Statistical screening for research data anomalies. The Python in `scripts/`
does the computation; your job is deciding which checks apply, getting the
numbers out of the source material, and reading the results honestly.

## The one rule

**These checks produce screening signals, never conclusions about
misconduct.** Every flag has innocent explanations. Report what was found and
what would explain it innocently; do not characterize a person's conduct, and
do not describe a dataset as fabricated. If asked to draft an accusation or a
public post from these results, decline and offer the factual summary instead.

## Setup

```bash
pip install -r requirements.txt   # numpy, pandas, scipy
```

If installing is not possible, say so rather than computing any of these by
hand. GRIM, GRIMMER and p-value recomputation are exact arithmetic and you
will get them wrong.

## Workflow

### 1. Work out what you actually have

| You have | Run |
|---|---|
| Raw data (CSV/XLSX, supplementary file) | data checks — pass `--group-column` / `--time-column` when they exist |
| A paper's Table 1 / results text only | `--reported-stats` (GRIM, GRIMMER, p recomputation) |
| Many p-values from one literature or author | `--p-values` |

Reported-statistics checks are the highest-value ones and need no raw data at
all. A GRIM failure is arithmetic; nothing else here is that solid.

### 2. Identify columns yourself — do not guess flags

Read the data first (`df.head()`, `df.dtypes`) and pass columns explicitly.
There is no auto-detection: naming a column as the treatment arm when it is
not silently invalidates the Carlisle check.

- `--group-column`: the randomized arm / treatment allocation.
- `--time-column`: a real date or sequence. Do **not** pass a row number just
  to make the ordered checks run; without meaningful order they are noise.

### 3. Extract reported statistics from the paper

This is the part only you can do. Build a CSV with these columns:

```csv
test,n,mean,sd,scale_min,scale_max,scale_step,stat,df1,df2,p
grim,20,3.46,,1,5,1,,,,
grimmer,30,4.50,2.80,1,5,1,,,,
t,,,,,,,2.35,18,,0.004
f,,,,,,,4.20,2,57,0.020
chi2,,,,,,,7.82,3,,0.050
```

Rules that change the answer:

- **Write the mean and SD exactly as the paper prints them.** `3.40` and `3.4`
  are different claims and GRIM treats them differently. Never normalize.
- **N must be the N for that specific statistic**, not the study N. Per-item
  missingness is the most common cause of a false GRIM failure.
- GRIM applies only to integer-valued measures (Likert items, counts). For a
  mean of k averaged items set `scale_step` to `1/k`.
- Leave a cell empty rather than guessing.

### 4. Run

```bash
python scripts/scan.py DATA.csv --group-column arm --time-column visit_date
python scripts/scan.py --reported-stats table1.csv --format json
python scripts/scan.py DATA.csv --checks duplication,structure
python scripts/scan.py --p-values pvals.csv --assumed-power 0.8
```

Use `--format json` when you are going to interpret the output; the text
format is for a human reading it directly.

Check groups: `authenticity`, `duplication`, `structure`, `randomization`,
`covariance`, `timeseries`, `reported_stats`, `pvalues`.

### 5. Read the output

Every finding is `flag`, `clear`, or `not_applicable`. There is deliberately
no overall score — see `references/METHODOLOGY.md` for why.

When writing up:

- **Lead with the arithmetic.** GRIM, GRIMMER and p-value inconsistencies are
  the only findings that can be impossible rather than merely unusual.
- **Report `not_applicable` explicitly.** "Benford could not be run: no column
  spans 3 orders of magnitude" is information. Silently omitting it implies
  the check passed.
- **Give each flag its innocent explanation.** `references/METHODOLOGY.md` has
  a "fails when" note for every check; use it. A constant ratio between two
  columns usually means a unit conversion, not fraud.
- **Do not add up flags.** One GRIM failure outweighs nine moderate flags.
  Nine moderate flags on 22 checks is roughly what multiple comparisons
  predict on honest data.
- **Never restate a severity as a probability.** "high" means "no ordinary
  explanation", not "likely fraud".

Load `references/METHODOLOGY.md` before interpreting anything: it gives each
check's assumptions, minimum data, thresholds and failure modes.

## What it cannot do

No image forensics, no text or reference checking, no full SPRITE search, no
statcheck prose parsing. The p-value checks need a body of results, not one
study.

Real-case validation covers GRIM and GRIMMER on two papers from one lab. The
data-side checks have none. There is no known real-world false positive rate,
so do not quote one.

## Reproducing the benchmarks

`benchmarks/real_cases/` validates GRIM and GRIMMER against real published
papers, cell by cell, against the verdicts a published reanalysis reached —
including the cells it found consistent. Read a case's `SOURCE.md` if you want
to see what a careful write-up of this kind of finding looks like.

`examples/clean_trial.csv` is honestly generated and should raise zero flags.
`examples/fabricated_trial.csv` is the same trial with five planted defects.

```bash
python benchmarks/generate_examples.py   # regenerate from a fixed seed
pytest                                   # includes the clean-vs-fabricated regression
```

If a change makes the clean dataset flag, the change is wrong.
