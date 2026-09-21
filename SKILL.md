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
| A trial's baseline table (Table 1), per-arm n / mean / SD | `--baseline-summary` |

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
test,n,mean,sd,scale_min,scale_max,scale_step,stat,df1,df2,n1,n2,p
grim,20,3.46,,1,5,1,,,,,,
grimmer,30,4.50,2.80,1,5,1,,,,,,
t,,,,,,,2.35,18,,,,0.004
f,,,,,,,4.20,2,57,,,0.020
chi2,,,,,,,7.82,3,,,,0.050
u,,,,,,,2291.0,,,54,54,0.0000294
```

`test=u` is a Mann-Whitney U test and takes the two group sizes in `n1`/`n2`
instead of degrees of freedom. It does not matter whether the paper reports
U1, U2 or the smaller of the two — the test is symmetric. The check is
one-sided: ties shrink p and cannot be recovered from a published U, so only
a reported p *above* the largest reachable value is reported as inconsistent.

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

**Only the validated checks run by default**: `reported_stats` and
`baseline_p`. They have a measured false-positive rate of 0 in 7,307
statistics computed from real data, and GRIM agrees with the R reference
implementation on 6000/6000 cases.

Everything else — `authenticity`, `duplication`, `structure`, `randomization`,
`covariance`, `timeseries`, `pvalues`, `baseline_balance` — needs
`--experimental` or an explicit `--checks`. On 300 ordinary real datasets,
89% drew at least one experimental flag; terminal-digit preference fires on
87% of them, Benford on 74%. Each experimental flag prints its own rate.

**Do not pass `--experimental` by reflex.** If you do, treat a flag from a
check with a high base rate as a description of ordinary data unless something
else corroborates it, and always quote the rate alongside the finding.

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
- **Never report a clear result as reassurance.** These checks test whether
  numbers are consistent with each other. Fabricated data processed by
  software is internally consistent and clears all of them. "No reporting
  errors of this kind were found" is the strongest statement a clear result
  supports; "the data look sound" is not.

Load `references/METHODOLOGY.md` before interpreting anything: it gives each
check's assumptions, minimum data, thresholds and failure modes.

## What it cannot do

No image forensics, no text or reference checking, no full SPRITE search, no
statcheck prose parsing. The p-value checks need a body of results, not one
study.

Real-case validation covers the arithmetic checks on three cases from two
research groups. The data-side checks (duplication, digits, sequential) have
none. There is no known real-world false positive rate, so do not quote one.

The Carlisle uniformity test is badly underpowered below a few hundred
baseline variables — on 50 variables from known-fabricated trials it returns
`clear`. Do not read a `clear` from it as reassurance; say it was
underpowered.

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
