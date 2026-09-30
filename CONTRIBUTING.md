# Contributing

## Ground rules

- **A change that makes `examples/clean_trial.csv` flag is wrong.** The
  benchmark in `tests/test_benchmark.py` enforces it. A false flag lands on a
  real person; a missed one only leaves a question open.
- **No thresholds moved to make a case fire.** Any change to a threshold, a
  rounding rule or a reference distribution comes with the false-positive
  numbers before and after (`benchmarks/false_positives/`), or a note on why
  there cannot be any.
- **A check is experimental until it has a measured base rate.** New checks go
  into `EXPERIMENTAL_GROUPS` and get a row in
  `scripts/scifraudscan/reference/experimental_base_rates.csv`. Moving one to
  `VALIDATED_GROUPS` needs real-case validation in `benchmarks/real_cases/`.
- **No aggregate score.** Every check returns `flag`, `clear` or
  `not_applicable`. A PR that adds a total, a probability of fraud or a ranking
  of people will not be merged.
- **A check that cannot run says why.** Return `not_applicable` with the
  missing input in the reason; never drop it silently.
- **Real cases only from the published record.** Anything added to
  `benchmarks/real_cases/` needs a `SOURCE.md` with DOIs, the editorial
  outcome and where every number came from. No unpublished allegations, no
  data you were given in confidence.
- Every check cites the method it implements in `references/METHODOLOGY.md`,
  and gets a matching entry in `references/METHODOLOGY.zh-CN.md`.

## Workflow

1. Open an issue first for anything bigger than a fix.
2. Branch from `main`, one change per PR.
3. Install the dev dependencies and run everything CI runs:

   ```bash
   make dev
   make check     # ruff, pytest, examples drift
   ```

4. If you changed `benchmarks/generate_examples.py`, run `make examples` and
   commit the regenerated `examples/`.
5. If you changed behaviour that `SKILL.md` describes, update `SKILL.md` in the
   same PR. It is what Claude reads; a stale sentence there is a bug.
6. Add a line to `CHANGELOG.md` under *Unreleased*.

## Docs in two languages

`README.md` and `references/METHODOLOGY.md` each have a `.zh-CN.md` sibling. A
PR that changes one changes the other, or says in the description that the
translation is pending. `SKILL.md`, code, comments and tool output stay in
English.

## Releasing

Bump `scripts/scifraudscan/_version.py`, `version` and `date-released` in
`CITATION.cff`, the Status table in both READMEs, and move *Unreleased* in
`CHANGELOG.md` under the new version. Tag `vX.Y.Z`; the release workflow
attaches `scifraudscan.zip` for Claude.ai upload.

## Branch rules

`main` is protected by two rulesets, the same as jev-edge:

- **main-merge-gate**: every change lands through a pull request, and the
  `ci-ok` (ci.yml) and `CodeQL` (security.yml) checks must pass. Maintainers
  may bypass only by merging a PR, never by pushing.
- **main-protect**: `main` cannot be deleted or force-pushed.
