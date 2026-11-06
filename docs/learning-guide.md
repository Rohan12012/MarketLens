# Reading the code

Start with `python main.py --help` to see the inputs. Then follow a run through
these files:

1. `marketlens/data.py` downloads prices, checks them, and finds the shared date
   range. Notice what happens when one asset has a shorter history.
2. `marketlens/analytics.py` calculates daily returns and the dashboard's metrics.
   Work through `test_known_portfolio_arithmetic` by hand to check the formulas.
3. `main.py` saves the snapshot, reports, and settings. Run from that snapshot a
   second time to check that the inputs produce the same result.
4. `app.py` collects settings and displays the calculations. Read it after the
   data and analytics code; most of it is presentation.
5. `marketlens/simulation.py` tracks holdings for the study. Buy-and-hold keeps
   model units fixed. Rebalancing changes units after a return has been earned.
6. `marketlens/study.py` applies the fixed allocations and cost rates to those
   strategies. The study plan is in `analysis-brief.md`.

## Questions worth working through

- Why are there fewer returns than price observations?
- How do prices become dollar holdings, weights, and portfolio returns?
- Why does a loss on the first return day count toward drawdown?
- Which observation earns the return after a month-end trade?
- Do holdings plus fees equal the value before a rebalance?
- Why can a current listing directory miss companies that traded in the past?

Tests use synthetic numbers chosen so the answers can be calculated manually.
They check the code's behavior, not the accuracy of Yahoo's prices. Before using
a report, check its date coverage and settings. Compare code versions using the
same saved data rather than downloading again.

## SQL

Study reports are stored in SQLite by `marketlens/store_study.py`.
`study-schema.sql` defines two tables: one row per run in `study_runs`, and one
row per allocation/strategy/cost case in `study_results`.

`analysis.sql` joins the results table to itself. It matches each scenario to the
zero-cost case from the same run, allocation, and strategy. The difference in
ending values includes fees and their effect on subsequent returns; it is not
just the sum of fees. Parameters are bound separately from SQL text.

Run the SQL tests with:

```bash
python -m unittest discover -s tests -p test_store_study.py -v
```

These tests create a temporary SQLite database and execute the real query. They
also check repeat imports and rollback when a database constraint fails.
