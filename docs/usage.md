# Commands and saved files

Run these commands from the project folder with the virtual environment active.

## Portfolio analysis

```bash
python main.py --tickers AAPL,MSFT,GOOGL --weights 0.4,0.3,0.3 --benchmark SPY --start 2024-01-01 --end 2025-01-01
```

The end date is exclusive. Weights must be nonnegative and sum to 1. Without dates,
the CLI requests 50 years ending before today's New York session. Use `--years 10`
for a shorter lookback. `--initial-value` defaults to 10000. `--risk-free 0.04`
means 4% annually; the dashboard accepts `4` because that input is a percentage.

Successful runs write matching `data/snapshots/<run-id>/` and `reports/<run-id>/`
folders. Metadata records the source, returned dates, package versions, and a price
checksum. To use saved data instead:

```bash
python main.py --input data/snapshots/<run-id>/prices.csv --tickers AAPL,MSFT,GOOGL --weights 0.4,0.3,0.3 --benchmark SPY
```

Replace `<run-id>`. Offline mode uses every row; date arguments apply only to
downloads. Inputs need one header row, a Date column, and adjusted-close columns
for all assets and the benchmark. The original tutorial `data/raw/AAPL.csv` has a
different multirow header and is not supported directly.

## Research setup

```bash
python -m marketlens.build_study
python -m marketlens.record_validation
python -m streamlit run app.py
```

To reuse a snapshot, pass `--snapshot <folder>` to `build_study`. The snapshot must
have the fixed study dates and pass its checksum and calendar checks. Each build
writes new reports, imports them into `data/study/study.sqlite`, and updates
`config/study-runs.json` only after all three windows succeed. Old runs are kept.
A failed build may leave unused reports; it does not select them for the dashboard.

A fresh build cannot compare itself with the original archived runs unless they
are present locally. Validation labels that reference check Not available. Missing
independent price evidence is labeled Not verified. These are not passing checks;
they do not prevent the software suite and available accounting checks from running.
Actual failures or changed reference results make the validation command exit nonzero.

## SQL and charts

```bash
python -m marketlens.store_study reports/study/<run-id>
python -m marketlens.compare_periods <full-run-id> <first-five-year-run-id> <second-five-year-run-id>
python -m marketlens.plot_study <full-run-id> <first-five-year-run-id> <second-five-year-run-id>
```

Find selected IDs in `config/study-runs.json`. The SQL query selects explicit IDs,
so extra runs in the database do not change the comparison. The chart is saved as
`reports/study/strategy-rankings.html`; its JavaScript libraries load from a CDN.

## Validation

```bash
python -m unittest discover -s tests -v
python -m marketlens.record_validation
```

The first command runs tests without market-data downloads. The second also checks
the selected real study exports and writes `reports/validation/latest.json` for
the dashboard. Refresh the receipt after changing checked code, SQL, configuration,
or data. The dashboard does not execute tests for visitors.

Data, databases, reports, and raw source responses are local and excluded from Git.
Use the same price snapshot to compare code versions; new downloads can contain
provider revisions. Paths in the original run records identify that machine's
recorded runs; a new build creates its own IDs.
