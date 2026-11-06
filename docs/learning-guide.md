# Understanding MarketLens

1. Start with `main.py --help`. The CLI converts your settings into a data request.
2. Read `marketlens/data.py`. Trace one download through adjusted-close extraction,
   validation, and snapshot preservation. A DataFrame is a labeled table.
3. Read `marketlens/analytics.py`. First calculate a two-day return manually, then
   compare it with `test_known_portfolio_arithmetic`. Fixture numbers are invented
   solely for testing; they are not market results.
4. Understand rebalancing: the model restores target weights each day. Buy-and-hold
   weights drift when assets earn different returns. These produce different results.
5. Trace report exports in `main.py`, then run the same snapshot offline.
6. Read `app.py`. Its form collects settings, calls the same analytics functions, and
   displays tables/charts. The UI does not contain a second set of financial formulas.
7. Run the tests. Try changing a fixture value and predicting which assertion fails.

## Professional review checklist

- Check date coverage, requested symbols, missing values, and price adjustment convention.
- Read settings.json before interpreting a report: weights, benchmark, capital, and rate matter.
- Use identical snapshots when comparing code versions.
- Avoid describing this historical model as your actual investment performance.
- Commit code and documentation; avoid committing environments and generated datasets.

## Optional SQL exercise

Import a generated `daily_returns.csv` into SQLite as `daily_returns` using a CSV-aware
importer. The columns are Date, Portfolio, Benchmark. The example in `analysis.sql`
computes average daily returns, daily benchmark-relative differences, and negative-day
counts. It does not calculate compounded total returns. SQL is an optional exercise;
the application itself uses pandas rather than a database.
