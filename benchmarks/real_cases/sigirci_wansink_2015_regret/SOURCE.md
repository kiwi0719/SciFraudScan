# Sigirci & Wansink (2015), "Low prices and high regret" — RETRACTED

## The paper

Sigirci, Ö., & Wansink, B. (2015). Low prices and high regret: how pricing
influences regret at all-you-can-eat buffets. *BMC Nutrition* 1(1), 36.
doi:[10.1186/s40795-015-0030-x](https://doi.org/10.1186/s40795-015-0030-x)

## Editorial outcome: retracted

Retraction Note published 15 September 2017,
doi:[10.1186/s40795-017-0195-6](https://doi.org/10.1186/s40795-017-0195-6)
([PMC7050918](https://pmc.ncbi.nlm.nih.gov/articles/PMC7050918/)).

Stated reason: "concerns have been raised after publication with respect to
the analysis of the data reported." The notice states explicitly that **the
authors do not agree with this retraction.**

## The reanalysis these expected verdicts come from

van der Zee, T., Anaya, J., & Brown, N. J. L. (2017). Statistical heartburn:
an attempt to digest four pizza publications from the Cornell Food and Brand
Lab. *BMC Nutrition* 3:54.
doi:[10.1186/s40795-017-0167-x](https://doi.org/10.1186/s40795-017-0167-x)
([PMC7050813](https://pmc.ncbi.nlm.nih.gov/articles/PMC7050813/), CC BY 4.0)

This paper is Article 4 in their numbering. The expected verdicts in
`reported_stats.csv` are taken from their Appendix, section
*Article 4: "Low prices and high regret"*, heading **Granularity errors**.

## Where the numbers came from

`reported_stats.csv` reproduces Table 2 of the retracted paper: 5 Likert items
× 6 groups (buffet price $4/$8 × 1/2/3 pieces of pizza), 30 cells with a mean
and an SD each.

Two independent sources were cross-checked against each other before anything
was written down, and they agree on every cell:

1. The means and SDs as typed from the published table by the reanalysis
   authors, in their own repository:
   <https://github.com/OmnesRes/pizzapizza> (`Python/paper4_table2.txt`).
2. The individual values quoted in the published Appendix.

Per-cell sample sizes `[18, 18, 7, 17, 19, 10]` are taken from the reanalysis
authors' code (`Python/master.py`), which sets them explicitly for this table.

Note that these Ns sum to 89, not the 95 diners the paper reports — one of the
inconsistencies the reanalysis identified. The Ns are used here as printed,
which is also what the reanalysis did.

## What is checked, and what is not

- **Means** are checked with GRIM against the published mean verdicts: 10 of
  the 30 are reported as impossible.
- **SDs** are checked with GRIMMER, but **only for cells whose mean is itself
  attainable**. When a mean is already impossible there is no valid total, so
  GRIMMER cannot say anything independent about the SD, and comparing it to
  the published SD verdict would be meaningless. That leaves 20 of the 30
  cells, 8 of which the reanalysis reports as having impossible SDs.
- The reanalysis also reports inconsistent F statistics, degrees of freedom
  exceeding the sample size, and disagreements between Tables 2 and 3. Those
  are outside what this toolkit currently checks and are not tested here.

## Result

30/30 means and 20/20 SDs match the published verdicts.
