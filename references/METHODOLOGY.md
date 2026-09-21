# Methodology

What each check tests, what it needs to run, what makes it fire, and how it
fails. Read the "fails when" column before repeating any result to anyone.

## The three outcomes

Every check returns exactly one of:

| Outcome | Meaning |
|---|---|
| `flag` | A concrete anomaly, with a severity and the numbers behind it. |
| `clear` | The check ran and found nothing. |
| `not_applicable` | The check could not run, and the message says what was missing. |

`not_applicable` is a real answer, not a failure. Most checks here need more
data than a single small study provides, and a check that runs anyway on
insufficient data produces noise that looks like evidence.

## Why there is no overall score

An earlier version of this toolkit returned a 0-100 "Research Integrity
Score", computed as the mean of per-check scores. That number was removed
because:

- **It could be diluted.** Adding checks that pass lowers the score without
  changing any evidence. A dataset with one impossible reported mean and
  twenty passing checks scored as low risk.
- **The weights had no basis.** Averaging a GRIM failure (arithmetically
  impossible) with a Benford deviation (common in honest data) treats them as
  equivalent. They are not remotely equivalent.
- **The thresholds were invented.** "35 = Warning, 70 = High Risk" was not
  calibrated against anything.

Findings are reported individually with a severity, and the reader does the
weighing. A single GRIM failure matters more than nine moderate flags.

## Severity

| Severity | Meaning |
|---|---|
| `high` | Arithmetically impossible, or a pattern with no ordinary explanation. |
| `moderate` | Unusual enough to need an explanation from the authors. |
| `low` | Worth noting; frequently benign. |

Benford non-conformity is capped at `moderate` no matter how extreme,
because honest measurement data fails it routinely (see below).

## Reported statistics

These are the strongest checks in the toolkit, because they test arithmetic
rather than plausibility. A failure means the reported numbers cannot all be
true at once.

### GRIM

- **Source:** Brown & Heathers (2017), *Social Psychological and Personality
  Science* 8(4).
- **Tests:** whether a reported mean can arise from N integer responses. With
  N responses the total is an integer, so attainable means are exactly the
  multiples of 1/N, rounded to the reported precision.
- **Needs:** integer-valued (or fixed-step) measure, N, and the mean written
  at its reported precision.
- **Fires when:** no integer total rounds to the reported mean.
- **Fails when:** the measure is not really integer-valued; N differs from the
  N used for that mean (missing data per item is the usual cause); the mean is
  of a composite of several items — pass `scale_step` for that case.
- **Precision matters:** 3.40 and 3.4 are different claims. The toolkit reads
  decimals from the written string, not the parsed float.

### GRIMMER and variance bounds

- **Source:** Anaya (2016), for GRIMMER; the bounds argument is elementary.
- **Tests:** two things. First, whether the reported SD is inside the range
  attainable by N integers on the stated scale with that mean -- the maximum
  is reached by putting all mass at the two endpoints. Second, GRIMMER: for
  integer data the sum of squares is an integer with the same parity as the
  total, and the check is whether any such integer is consistent with the
  rounding intervals of both the reported mean and the reported SD.
- **Needs:** N, mean, SD, and scale minimum and maximum.
- **Not SPRITE.** SPRITE searches for an actual sample matching the reported
  statistics; this is the weaker deterministic test. It will miss cases SPRITE
  catches. It never returns a different answer on a re-run, which SPRITE can.

### Reported p-value consistency

- **Source:** the logic behind statcheck (Nuijten et al. 2016).
- **Tests:** recomputes p from the reported test statistic and df, and
  compares against the reported p at its written precision.
- **Fires when:** they disagree. Severity rises to `high` when the
  disagreement changes significance at α = .05 (a "decision error").
- **Deliberately lenient:** a t or r reported one-tailed is accepted as
  consistent. Reporting one-tailed is a choice, not an error, and treating it
  as one produced most of the false positives during development.
- **Fails when:** the statistic was reported rounded (t = 2.4 recomputes to a
  wide range of p); corrections such as Greenhouse-Geisser or Bonferroni were
  applied and not described in the table.

## Data authenticity

### Benford's law -- read this before using it

- **Source:** Nigrini (2012) for the MAD thresholds (0.012 marginal, 0.015
  non-conformity).
- **Tests:** first-digit distribution against log10(1 + 1/d).
- **Needs:** n >= 150 **and** a spread of at least 3 orders of magnitude, per
  column. Both are enforced; below them the check returns `not_applicable`.
- **This check is the easiest one here to misuse.** Benford's law describes
  data from multiplicative processes spanning many orders of magnitude --
  financial totals, populations, city sizes. Bounded physical and clinical
  measurements do not follow it even when completely honest. During
  development a Gamma-distributed clinical variable, generated honestly,
  failed at MAD = 0.030, p = 0.002. That is why the span requirement is strict
  and the severity is capped at `moderate`.
- **Never run it on pooled columns.** Mixing variables with different units
  produces a digit distribution with no expected shape.

### Terminal digit preference

- **Tests:** the final recorded digit against a uniform distribution, per
  column, with a chi-square test and Cramér's V as the effect size.
- **Needs:** n >= 100 per column.
- **Fires when:** p < .01 **and** V >= 0.10. Both are required: with large n,
  trivial deviations reach significance.
- **Trailing zeros count.** In a column recorded to one decimal, 54.0 ends in
  0, not 4. Stripping the zero -- which an earlier version did -- depletes
  digit 0 and inflates digit 9, which by itself looks exactly like digit
  preference. This was a real bug caught by the benchmark.
- **Fails when:** the instrument itself rounds (many devices report to the
  nearest 5); the variable is a count with a natural mode.

### Repeated increments

- **Tests:** the proportion of distinct first differences.
- **Needs:** n >= 20, and a non-integer-valued column. Integer measures repeat
  their increments for ordinary reasons and are skipped.

## Duplication

The most actionable family after the arithmetic checks. Two columns holding
the same multiset, or one an exact linear rescaling of the other, does not
arise from independent measurement.

| Check | Fires when | Ordinary explanation to rule out |
|---|---|---|
| Exact duplicate rows | Any row repeats in full | Merge artefact; repeated-measures data in long format |
| Near duplicate rows | Cosine >= 0.999 over >= 4 standardized numeric columns | Genuinely similar subjects; few columns (hence the minimum) |
| Linear transformation | R² >= 0.9999 for y = ax + b | Unit conversion; a derived score stored alongside its source |
| Permutation duplicate | Two columns hold the same multiset in a different order | Two orderings of one variable |
| Repeated value blocks | A run of 6 consecutive values reappears elsewhere | Genuinely repeating short sequences in coarse data |

## Structural relationships

Constant difference, constant ratio and near-perfect correlation (|r| >= 0.999)
all indicate that one column was computed from another. This is frequently
legitimate. The finding is that the two columns are **not independent
evidence**, which matters when both are analysed as measurements.

Over-regularity measures the variability of consecutive steps relative to the
spread of the series, so the verdict does not change with the unit of
measurement. Row counters and ID sequences are excluded: they have constant
steps by construction.

## Randomization -- Carlisle baseline balance

- **Source:** Carlisle (2017), *Anaesthesia* 72(8).
- **Tests:** under real randomization, baseline comparisons between arms give
  p-values uniform on [0, 1]. Fabricated data tends to be *too* balanced,
  pushing them toward 1.
- **Two entry points:** `carlisle_method` works from raw participant rows;
  `baseline_summary_check` works from a published baseline table (per-arm n,
  mean and SD). The second is the case that actually arises when screening a
  paper, and is how Carlisle and Bolland apply the method.
- **Needs:** a group column and at least 5 usable baseline variables.
  High-cardinality categoricals (IDs) are excluded.
- **Two tests are run:** a two-sided KS test against uniform, and a one-sided
  KS test for the too-balanced direction. The one-sided test has more power
  against fabrication and is usually the one that fires.
- **The central caveat:** the uniformity result assumes independent baseline
  variables. Real baseline tables are correlated -- height with weight, age
  with comorbidity -- which makes the test anti-conservative. A flag here is a
  reason to look, never a result to report on its own.
- **Rounding alone breaks uniformity.** Published summary statistics are
  rounded, which distorts the p-value distribution away from exactly uniform
  (Bolland et al. 2020). The reference implementation compares against an
  empirically simulated distribution instead; this one does not, which makes
  it cruder.
- **Badly underpowered on small collections.** With 8 variables the test
  missed a deliberately fabricated dataset during development. On 50 real
  baseline variables from the retracted Sato/Iwamoto trials it returns
  `clear`, with mean p = 0.567 against the 0.500 expected — the shift is in
  the fabrication direction but nowhere near significance. Bolland et al.
  needed roughly 500 variables. **A `clear` from this check is close to
  uninformative unless the collection is large.**

### Reported baseline p-value consistency

- **Source:** the `pval_cont_check` logic in Bolland's `reappraised` package.
- **Tests:** whether the p-value printed next to a baseline row is reachable
  from the n, mean and SD printed in that same row. The reachable range is
  the minimum and maximum over every combination of the means and SDs at the
  edges of their rounding intervals, under both Student's and Welch's t-test,
  and the reported p is compared using its own rounding interval.
- **Needs:** a two-arm row with n, mean, SD and a printed p-value.
- **Why it is worth more than the uniformity test:** it assumes nothing about
  the distribution of p-values across variables, so it works on a single
  table and cannot be blunted by correlated baseline variables. On the
  Sato/Iwamoto case it flagged 5 of 10 printed p-values where the uniformity
  test found nothing.
- **Fails when:** the paper used a test other than a t-test (Mann-Whitney,
  or a test adjusted for covariates or clustering), or the p came from a
  different subgroup than the row's n implies. Being generous about rounding
  and about which form of the t-test was used keeps ordinary choices from
  being flagged, but a different test entirely will still show up.

## Covariance structure

Reports near-collinear pairs (|r| > 0.98) and a singular or near-singular
covariance matrix (condition number > 1e8). Low correlation between variables
is **not** flagged: uncorrelated variables are the normal case, and an earlier
version that scored them as suspicious was simply wrong.

## Sequential structure

Both checks refuse to run without an explicit time or sequence column. Row
order in a CSV is otherwise an artefact of how the file was assembled, and
testing it produces findings about the export process, not the data.

- **Serial autocorrelation:** |lag-1| > 0.9, needing n >= 30.
- **Spectral periodicity:** a single frequency holding more than 50% of
  spectral power after linear detrending, needing n >= 32.
- **Fails when:** the data is a genuine time series, where strong
  autocorrelation and seasonality are expected. These checks are for variables
  that should *not* have sequential structure.

## P-value distribution

All three need a body of results -- a literature, a lab, an author's output.
On one study's handful of p-values they have no power, and each returns
`not_applicable` below its minimum.

### Caliper test (just-significant clustering)

- **Tests:** counts in [.045, .050) against [.050, .055). Under any smooth
  distribution of true effects the two narrow windows should be roughly equal.
- **Needs:** 10 p-values inside the combined window.
- **Fires when:** a one-sided binomial test gives p < .05 for a surplus on the
  significant side.
- **Why a caliper and not a rate:** an earlier version scored the share of
  significant p-values in [.045, .05), which rises with the true effect size
  and flagged honest literatures.

### P-curve shape

- **Source:** Simonsohn, Nelson & Simmons (2014), *JEP: General* 143(2).
- **Tests:** among significant results, the split below vs above p = .025. Real
  effects produce right skew (a surplus below .025); p-hacking produces left
  skew.
- **Needs:** 20 significant p-values.
- **Fails when:** the studies are heterogeneous in power, or selected by an
  unclear rule. P-curve assumes the set was defined before the p-values were
  seen.

### Excess significance

- **Source:** Ioannidis & Trikalinos (2007), *Clinical Trials* 4(3).
- **Tests:** observed count of significant results against the count expected
  at an assumed power.
- **Needs:** 20 p-values.
- **The assumption drives the result.** The default assumed power of 0.5 is a
  convention, not a measurement. Set `--assumed-power` from the actual design
  where you can. Every output carries this caveat.

## Known gaps

- **Real-case validation covers GRIM and GRIMMER only, on two papers.**
  `benchmarks/real_cases/` reproduces the per-cell verdicts of a published
  reanalysis of one retracted and one corrected paper (58 cells, full
  agreement, roughly half of them consistent-value controls). That validates
  the arithmetic checks against real reported statistics. It does not
  generalize to a false positive rate across the literature.
- **The data-side checks have no real-case validation.** Duplication, digit
  preference, Carlisle balance and the sequential checks are tested only
  against synthetic data with planted defects, which shows they fire on what
  they claim to detect and stay quiet on honest data of the same shape, and
  nothing more.
- No SPRITE, no full statcheck (which parses prose, not tables), no image
  forensics, no text or reference checks.
- Multiple comparisons across ~22 checks are not corrected for. Running enough
  checks on honest data will eventually produce a flag; this is why severity
  and the explanations above matter more than the count.

## References

- Anaya, J. (2016). The GRIMMER test. *PeerJ Preprints* 4:e2400v1.
- Brown, N. J. L., & Heathers, J. A. J. (2017). The GRIM test. *SPPS* 8(4), 363-369.
- Carlisle, J. B. (2017). Data fabrication in randomised controlled trials. *Anaesthesia* 72(8), 944-952.
- Ioannidis, J. P. A., & Trikalinos, T. A. (2007). An exploratory test for an excess of significant findings. *Clinical Trials* 4(3), 245-253.
- Nigrini, M. J. (2012). *Benford's Law*. Wiley.
- Nuijten, M. B., et al. (2016). The prevalence of statistical reporting errors in psychology. *Behavior Research Methods* 48, 1205-1226.
- Simonsohn, U., Nelson, L. D., & Simmons, J. P. (2014). P-curve: a key to the file-drawer. *JEP: General* 143(2), 534-547.
