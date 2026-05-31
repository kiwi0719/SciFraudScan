# SciFraudScan

SciFraudScan is an open-source research integrity screening toolkit for detecting statistical anomaly signals in scientific datasets, reported results, and p-value patterns. It helps reviewers, journals, institutions, and researchers prioritize suspicious cases for deeper audit.

SciFraudScan 是一个开源科研诚信筛查工具，用于从科研数据、论文报告统计量和 p 值分布中发现统计异常信号。它可以帮助审稿人、期刊、科研机构和研究者优先定位需要进一步核查的可疑数据。

## First release scope

This initial version focuses on the highest-yield checks:

- Data duplication: exact duplicate rows, near duplicates, linear-transformation duplicates, permutation duplicates, and partial repeated numeric windows.
- Data authenticity: Benford Law, terminal-digit preference, and entropy/compression-style low-complexity checks.
- Structural anomalies: constant differences, constant ratios, near-perfect correlations, and over-regularity.
- Reported statistics validation: GRIM, SPRITE, and consistency checks for reported `t`, `F`, and chi-square p-values.
- P-value anomalies: suspicious clustering just below 0.05, p-curve shape, and excess significance.
- Randomization, covariance, and time-series checks: Carlisle-style baseline p-value uniformity, covariance matrix structure, autocorrelation, and spectral periodicity.

## External engines

SciFraudScan uses mature open-source statistical libraries where they are directly usable from Python:

- `benford-py` for Benford first-digit and MAD calculations.
- `pysprite` for GRIM and SPRITE feasibility checks.
- `scipy.stats` for entropy, distribution tests, correlations, and p-value recomputation.
- `scipy.signal` for periodogram-based spectral analysis.
- `statsmodels` for autocorrelation analysis.

Checks without a mature Python-native research-integrity package, such as duplicate detection, constant difference/ratio detection, linear-transformation duplication, over-regularity, Carlisle-style aggregation, covariance structure flags, and p-value clustering, are implemented inside this project.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Quick start

```bash
riskscan scan examples/suspicious_dataset.csv --format text
riskscan scan examples/suspicious_dataset.csv --format json
```

With reported statistics and p-values:

```bash
riskscan scan examples/suspicious_dataset.csv \
  --reported-stats examples/reported_stats.csv \
  --p-values examples/p_values.csv \
  --group-column group \
  --time-column visit_date \
  --format text
```

Run the local web interface:

```bash
scifraudscan-web
```

Then open `http://127.0.0.1:8765`.

## Input formats

Main data should be a CSV file. Numeric columns are used for statistical checks; non-numeric columns are retained for exact row duplicate checks.

Reported statistics CSV supports these rows:

```csv
test,n,mean,sd,scale_min,scale_max,scale_step,stat,df1,df2,p
grim,20,3.45,,1,5,1,,,,,
sprite,20,3.45,0.76,1,5,1,,,,,
t,,,,,, ,2.35,18,,0.030
f,,,,,,,4.20,2,57,0.020
chi2,,,,,,,7.82,3,,0.050
```

P-value CSV may contain a `p` column, or it may be a one-column file.

`--group-column` enables Carlisle-style randomization checks across baseline variables. `--time-column` sorts rows before autocorrelation and spectral checks.

## Risk score

The CLI returns a `Research Integrity Score` from 0 to 100. Higher means more statistical warning signals. This score is a triage aid, not proof of misconduct.

Text and web reports include specific abnormal indicators, such as the affected column pair, transformed relationship, p-value mismatch row, terminal digit distribution, high-correlation rate, or repeated window location.

## Development

```bash
pytest
ruff check .
```

## License

MIT
