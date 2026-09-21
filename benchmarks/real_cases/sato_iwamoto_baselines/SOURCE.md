# Sato / Iwamoto baseline tables — RETRACTED trials

## The trials

Yoshihiro Sato and co-authors published a large body of randomized trials of
bone health interventions. Following work by Mark Bolland, Alison Avenell,
Greg Gamble and Andrew Grey, **more than two dozen of these papers were
retracted**, making it one of the largest documented cases of fabricated
trial data.

Study identifiers in the data (`H2`, `H3`, `I1`, ...) are the reanalysis
authors' own labels, not journal identifiers.

## Where the data came from

`baseline_summary.csv` is the `SI_pvals_cont` dataset from the **reappraised**
R package, written by Mark Bolland — one of the authors of the original
reanalysis — and published on CRAN under the MIT licence.

- Package: <https://cran.r-project.org/package=reappraised> (v0.2, MIT)
- Dataset description, verbatim: "Sample from Sato/Iwamoto dataset of 500
  baseline variables in 41 trials"
- Primary reference: Bolland, M. J., Avenell, A., Gamble, G. D., & Grey, A.
  (2016). Systematic review and statistical analysis of the integrity of 33
  randomized controlled trials. *Neurology* 87(23), 2391-2402.
  doi:[10.1212/WNL.0000000000003387](https://doi.org/10.1212/WNL.0000000000003387)

It holds 50 baseline variables with per-arm n, mean and SD (2 to 4 arms), and
the p-value the paper printed where there was one. The file is a verbatim
export; no values were altered.

## Result 1: the reported baseline p-values — flagged

10 rows print a p-value next to their summary statistics. For each, we compute
every p-value obtainable from that same row: all four means and SDs at the
edges of their rounding intervals, under both Student's and Welch's t-test.

**5 of the 10 reported p-values lie outside that range**, so they cannot have
come from the numbers printed beside them:

| Study | Variable | Reported p | Reachable range |
|---|---|---|---|
| H3 | Intact side | 0.68 | 0.369 – 0.385 |
| H3 | Intact BGP (ng/mL) | 0.89 | 0.070 – 0.079 |
| H30 | Intact side | 0.89 | 0.001 – 0.434 |
| H30 | Ionized calcium (mEq/L) | 0.92 | 0.000 – 0.000 |
| H30 | Deoxypyridinoline | 0.74 | 0.416 – 0.691 |

The other 5 are reachable and are correctly not flagged, including cases with
a visible gap (H14, BMI: reported 0.84 against a range reaching 0.899). Those
5 are the false-positive controls.

The check follows the `pval_cont_check` logic in the reappraised package,
which compares a reported p against the minimum and maximum obtainable from
maximally rounded summary statistics.

## Result 2: the Carlisle uniformity test — does NOT fire

On these 50 variables the uniformity test returns **clear**:

| Statistic | Value | Expected under randomization |
|---|---|---|
| mean baseline p | 0.567 | 0.500 |
| proportion p > 0.8 | 30% | 20% |
| two-sided KS p | 0.366 | — |
| one-sided "too balanced" p | 0.184 | — |

The shift is in the fabrication direction but does not reach significance.
This is a **negative result on real fabricated data and it is recorded as
such**; no threshold was adjusted to make it fire.

Why it does not fire here:

- **This is a 10% sample.** Bolland et al. analysed roughly 500 baseline
  variables and reported that over half exceeded p = 0.8. 50 variables give
  far too little power for a shift of this size, and the sample is a
  package illustration, not a random draw from the full set.
- **The published method is not this test.** Bolland et al. compare the
  observed distribution against an *empirically simulated* reference that
  accounts for the rounding of published summary statistics, and summarise it
  by the area under the CDF — not a KS test against an exactly uniform
  reference. Rounding alone moves the distribution away from uniform
  (Bolland et al. 2020, *Anaesthesia* 75, doi:10.1111/anae.15165).

The honest conclusion is that our Carlisle check is usable for triage on large
baseline collections and is underpowered on small ones. The p-value
reachability check, which needs no distributional assumption at all, did the
work on this case.

## What this case does not establish

There is no genuine-trial control here. The reappraised package ships only
Sato/Iwamoto data, so the false-positive rate of these two checks against real
honest trials is untested. The 5 reachable p-values above are a control for
the reachability check within this dataset, and nothing more.
