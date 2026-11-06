# Release check: MarketLens 1.0.0

A source-only copy was tested in a newly created virtual environment, installed
from `requirements-lock.txt`. Generated datasets, reports, and the development
virtual environment were not copied into that source checkout.

| Check | Observed result |
| --- | --- |
| Python | Python 3.13.3 |
| Platform | macOS-15.7.4-arm64-arm-64bit-Mach-O |
| Automated tests | 88 run, exit code 0 |
| Dependency check | No broken requirements found. |
| Completed at (UTC) | 2026-11-06T02:59:21.678279+00:00 |

This is a macOS clean-environment check, not a claim that every operating system
or hosted deployment has been tested. GitHub Actions is configured to run the
locked dependency set and tests on Ubuntu; its actual remote run must be checked
separately. Browser layout has been exercised through Streamlit's testing API,
not a recorded manual visual review.

Local evidence: `reports/release/clean-environment.json` and
`reports/release/clean-environment-tests.log`. The dashboard's Validation tab has
a separate, refreshable record of the working source and selected study exports.

The real-data study has 72 selected cases, with 2,514 sessions in its full-period
snapshot. Checks cover dates, SQL case coverage, holdings/return/fee reconciliation,
and equality of rebuilt summaries with the original runs.

Independent price verification is unresolved: 0 of the fixed 12 sampled prices
have been verified against a comparable second source. A source probe returned
HTML rather than price data. This is shown as Not verified, not Passed.

The source archive excludes data, databases, reports, secrets, and environments.
A fresh user builds the local research database using the commands in README.md.
No hosted deployment was created for this release.
