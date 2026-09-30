# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-10-01

### Upgrade notes

- **`summary.groups_run` lists only the groups that actually ran.** It used to
  list every selected group, including ones skipped for lack of input, so a
  dataset-only run claimed `reported_stats` and `baseline_p` had run. Skipped
  groups and the reason are in the new `summary.groups_skipped`.
- **A group named in `--checks` whose input is missing** now reports
  `not_applicable` with the missing input. It used to be dropped, and the run
  printed "Nothing was run" with exit code 0.

### Added

- `.tsv` and `.xlsx` input (Excel needs `openpyxl`). `SKILL.md` already
  promised XLSX; the CLI only read CSV.
- Text reports list the groups that were not run and why.
- `inputs.baseline_summary_rows` in the JSON report.
- Simplified Chinese docs: `README.zh-CN.md`, `references/METHODOLOGY.zh-CN.md`.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `Makefile`
  (`make check`, `make package`), CI, issue and PR templates.

### Fixed

- README benchmark table: the fabricated example raises 12 flags / 9 clear,
  not 14 / 7, since the 0.4.0 recalibration.
- README sample output showed version 0.2.0.
- `CITATION.cff` version.

## [0.4.0] - 2026-09-21

Recalibrated experimental checks against Rdatasets, empirical reference for
Carlisle balance of published baseline tables, Mann-Whitney U consistency,
real-case benchmarks.
