# False-positive rates on real data

Measuring a false-positive rate normally needs a corpus known to be sound,
which is the hard part — "not retracted" is not the same as "correct".

This sidesteps it. Take **real raw data**, compute the summary statistics
yourself, and round them the way a paper would. The reporting is then correct
by construction, so **every flag is a demonstrable false positive**, with no
assumption about anybody's integrity involved. Real data also brings what
synthetic data cannot: genuine rounding granularity, genuine ties, genuine
correlation between variables.

Source: 300 datasets sampled from
[Rdatasets](https://vincentarelbundock.github.io/Rdatasets/), the example data
shipped with R packages — ordinary teaching and research data with no
connection to research misconduct.

```bash
python benchmarks/false_positives/fetch_datasets.py
python benchmarks/false_positives/measure_validated.py
python benchmarks/false_positives/measure_experimental.py
```

## Validated checks

| Check | Cases | False positives | Rate |
|---|---|---|---|
| GRIM | 2674 | 0 | **0.00%** |
| GRIMMER | 2674 | 0 | **0.00%** |
| Reported p (Student t) | 653 | 0 | **0.00%** |
| Reported p (Mann-Whitney U) | 653 | 0 | **0.00%** |
| Baseline p reachability | 653 | 0 | **0.00%** |

The Mann-Whitney and baseline rows matter most, because they run on real data
with real ties and on p-values computed from raw data but printed beside
rounded summaries — the two situations the one-sided logic was built for.

Getting to zero took two fixes, both found here:

- **Rounding convention.** GRIM compared rounded values using Python's
  `round`, which rounds half to even. At n = 80 a total of 274 gives 3.425 —
  3.42 under that rule, 3.43 under the round-half-away-from-zero that SPSS and
  Excel use. The test now asks whether a candidate total falls inside the
  reported value's rounding interval, accepting both boundaries.
- **Float precision.** GDP figures around 1e13 and an ISBN treated as a
  measurement produced 13 false positives, because a double cannot resolve
  half of the last decimal place at that magnitude. GRIM and GRIMMER now
  report such rows as unevaluable instead of guessing.

## Experimental checks

Not provably false positives — real data can legitimately hold a derived
column or a repeated block — but these are ordinary datasets, so a high rate
means the check is describing something common rather than something wrong.

| Check | Ran | Fired | Rate |
|---|---|---|---|
| Terminal Digit Preference | 189 | 164 | **87%** |
| Benford First Digit | 50 | 37 | **74%** |
| Repeated Value Blocks | 299 | 209 | 70% |
| Carlisle Baseline Balance | 112 | 71 | 63% |
| Covariance Structure | 288 | 164 | 57% |
| Near Duplicate Rows | 254 | 135 | 53% |
| Repeated Increments | 299 | 70 | 23% |
| Near-Perfect Correlation | 299 | 65 | 22% |
| Over-Regularity | 299 | 52 | 17% |
| Linear Transformation Duplicate | 299 | 36 | 12% |
| Constant Ratio | 299 | 34 | 11% |
| Constant Difference | 299 | 27 | 9% |
| Permutation Duplicate | 299 | 20 | 7% |
| Exact Duplicate Rows | 299 | 0 | 0% |

**89% of ordinary datasets draw at least one experimental flag.**

A check that fires on 87% of ordinary data carries almost no information when
it fires on yours. That is why these are off by default, and why every
experimental flag now prints its measured rate beside it — a severity means
nothing without a base rate.

Two caveats on these numbers. The Carlisle row is partly an artefact: the
harness hands it the first binary column of each dataset, and these are not
randomized trials, so imbalance is expected. And Benford ran on only 50
datasets, since most have no column spanning three orders of magnitude — but
firing on 74% of those is the misapplication warned about in
`references/METHODOLOGY.md`, now with a number attached.

The rates in the table are shipped as
`scripts/scifraudscan/reference/experimental_base_rates.csv`.
