# Just, Sigirci & Wansink (2014), "Lower buffet prices..." — CORRECTED, not retracted

## The paper

Just, D. R., Sigirci, Ö., & Wansink, B. (2014). Lower buffet prices lead to
less taste satisfaction. *Journal of Sensory Studies* 29(5), 362-370.
doi:[10.1111/joss.12117](https://doi.org/10.1111/joss.12117)

## Editorial outcome: correction

This paper was **not retracted**. The Journal of Sensory Studies issued a
lengthy correction in August 2017 which changed values in four tables, and
which concluded: "The overall findings of the paper remain unchanged by our
reanalysis."

It is included here because its reported statistics were examined in detail
and the per-cell verdicts are public — not as an example of a retraction. Of
the four papers in the reanalysis below, the retracted one is
`../sigirci_wansink_2015_regret/`.

## The reanalysis these expected verdicts come from

van der Zee, T., Anaya, J., & Brown, N. J. L. (2017). Statistical heartburn:
an attempt to digest four pizza publications from the Cornell Food and Brand
Lab. *BMC Nutrition* 3:54.
doi:[10.1186/s40795-017-0167-x](https://doi.org/10.1186/s40795-017-0167-x)
([PMC7050813](https://pmc.ncbi.nlm.nih.gov/articles/PMC7050813/), CC BY 4.0)

This paper is Article 1 in their numbering. Expected verdicts come from their
Appendix, section *Article 1*, heading **Granularity errors**.

## Where the numbers came from

Means and SDs are from Tables 1 and 2 of the original paper, as typed by the
reanalysis authors in <https://github.com/OmnesRes/pizzapizza>
(`Python/paper1_table1.txt`, `Python/paper1_table2.txt`), cross-checked
against the values quoted in the published Appendix.

Sample sizes follow the reanalysis, which derived them from Article 2 because
Table 2 of this paper does not state them:

- Table 1: N = 62 ($4), N = 60 ($8)
- Table 2, rows 1-4: N = 62 ($4), N = 60 ($8)
- Table 2, rows 5-7 (middle slice): N = 41 ($4), N = 26 ($8)
- Table 2, rows 8-10 (last slice): N = 47 ($4), N = 38 ($8)

Item labels are given only where the Appendix names them; unnamed rows are
recorded by their table position rather than guessed at.

Age, height and weight rows are excluded, as the reanalysis excluded them:
it is unclear whether those were recorded as whole numbers, and GRIM only
applies to integer-valued measures.

The two gender rows are percentages rather than means, so GRIM is applied with
`scale_step = 100`: a percentage of 62 diners moves in steps of 100/62, not
1/62. Getting this wrong makes both gender cells look consistent.

## Result

28/28 cells match the published verdicts — 13 impossible values (12 means,
including the two percentages, and 1 SD) and 15 consistent controls.

The SD case is the interesting one: Table 2, row 7, $8 column reports mean
7.81 with SD 1.22 at N = 26. The mean is attainable (203/26 = 7.8077 rounds to
7.81); it is the SD that is impossible, which only GRIMMER detects.
