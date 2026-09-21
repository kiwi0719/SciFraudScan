# Cross-implementation check

`scrutiny_grim_grimmer.csv` holds 800 (n, mean, SD) triples together with the
verdicts of **scrutiny 0.6.1**, the R reference implementation of GRIM and
GRIMMER by Lukas Jung (<https://cran.r-project.org/package=scrutiny>, MIT).

The point is independence. Every other test here was written by the same
person as the code it tests. These verdicts come from someone else's
implementation of the same published methods, so agreeing with them is
evidence the arithmetic is right, not just self-consistent.

`tests/test_crosscheck.py` runs against this file and needs no R.

## Results over the full 6000-case comparison

| Check | Compared | Disagreements | Cases where we reject and scrutiny does not |
|---|---|---|---|
| GRIM | 6000 | **0** | 0 |
| GRIMMER | 6000 | 154 (2.6%) | **0** |

**GRIM agrees exactly.** Getting there required a fix: the first version
compared rounded values using Python's `round`, which is round-half-to-even.
At n = 80 a total of 274 gives 3.425 — 3.42 under that rule and 3.43 under the
round-half-away-from-zero that SPSS and Excel use. 12 of 10,000 random triples
came out differently against pysprite because of it, and in the dangerous
direction: means called impossible that are reachable. The test now asks
whether a candidate total falls inside the reported value's rounding interval,
accepting both boundaries, which is the convention Brown & Heathers and
van der Zee et al. describe.

**GRIMMER is weaker than the reference.** Ours implements the basic test: the
sum of squares must be an integer with the same parity as the total, and must
be consistent with the rounding intervals of the reported mean and SD.
scrutiny implements the published refinements and rejects 2.6% more pairs.
Every disagreement is in that direction — there is no case where we call a
pair impossible and scrutiny does not — so the cost is sensitivity, not false
positives.

**If you need GRIMMER at full strength, use scrutiny.** This is noted in the
README and in `references/METHODOLOGY.md`.

## Reproducing

Needs R with `scrutiny` installed. The generator that produced this file is
not committed; it drew 6000 random triples, recorded both implementations'
verdicts, and sampled 800 for the fixture.
