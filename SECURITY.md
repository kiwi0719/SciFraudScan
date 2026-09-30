# Security policy

## Supported versions

Only the latest minor release gets fixes. There are no backports.

## Reporting a vulnerability

Report privately through GitHub:
[**Report a vulnerability**](https://github.com/kiwi0719/SciFraudScan/security/advisories/new).
Do not open a public issue for it.

Include the version (`python scripts/scan.py --version`) and the smallest
input that reproduces it. Never attach data you are not allowed to share.

You should get a first reply within 7 days.

## What counts

- an input file that makes the scanner execute code, read or write files
  outside what it was given, or hang indefinitely
- anything that makes a report state something the checks did not find: a
  flag printed as clear, a check that did not run reported as run, a version
  string that does not match the code
- `SKILL.md` wording that leads Claude to present a screening signal as a
  finding of misconduct

## What does not count

A check that flags honest data, or misses a known problem, is a correctness
issue: open a public issue with the numbers. **Do not include the identity of
the authors of the data** in a public issue; describe the numbers only.
