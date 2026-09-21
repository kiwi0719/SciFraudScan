# Real published cases

Validation against real papers whose statistics have already been examined in
the peer-reviewed literature. These are not new allegations: every value here
is a printed number from a published table, and every expected verdict is the
verdict a published forensic reanalysis already reached. The test asks one
question — does this toolkit reproduce a result the literature has already
established?

Cases are named because the papers, the reanalysis and the editorial outcomes
are all public record, and because an anonymized case cannot be checked by
anyone reading this.

## What each case directory holds

- `reported_stats.csv` — the statistics exactly as the paper printed them,
  with the sample size for each cell, plus a `published_*_verdict` column
  giving the published reanalysis's conclusion for that cell.
- `SOURCE.md` — the paper, the reanalysis, the editorial outcome, where every
  number came from, and what the reanalysis does and does not claim.

`tests/test_real_cases.py` checks our verdict against the published verdict
cell by cell. Both agreeing and disagreeing cells matter: the cells the
reanalysis found *consistent* are the false-positive controls.

## Scope and fairness

- A statistical inconsistency is not a finding of misconduct, and none of the
  sources cited here claim otherwise. Wherever the authors disputed an
  editorial outcome, `SOURCE.md` says so.
- Editorial status is recorded exactly: a correction is recorded as a
  correction, a retraction as a retraction. They are not the same thing.
- Cases are included because their numbers are public and already analyzed,
  not as a judgement about the people involved.
