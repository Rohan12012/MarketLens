# Study dataset

Prices for the concentration and rebalancing study have been downloaded. The
first full-period comparison is recorded in [the run record](study-run.md).

| Field | Value |
| --- | --- |
| Source | Yahoo Finance via yfinance |
| Symbols | AAPL, MSFT, GOOGL, SPY |
| Requested start | 2016-01-01 |
| Requested end (exclusive) | 2026-01-01 |
| First returned date | 2016-01-04 |
| Last returned date | 2025-12-31 |
| Price rows | 2,514 |
| Missing cells | 0 |
| Retrieved at (UTC) | 2026-11-06T01:14:15.571361+00:00 |

Local snapshot: `data/study/20261106T011415Z-bbbd01c9`. It contains `prices.csv` and `metadata.json` and is
excluded from Git.

SHA-256 of `prices.csv`:

```text
343c17ae977585c7b1d60c455a5fb4dde3c9f9a44f5f8fe26b318dee74d6232d
```

Checks passed for positive finite prices, missing cells, duplicate dates, and date
order. The file checksum matches the metadata. A separate [calendar audit](data-quality.md)
also found no missing or unexpected sessions. Individual prices have not been
verified against another source.
The requested start is a calendar boundary; the first returned observation is the
first row available in this request.

To fetch another copy:

```bash
python -m marketlens.prepare_study_data
```

Each download creates a new snapshot. Provider revisions can change prices and the
checksum, so use this exact saved file for all comparisons in the study.
