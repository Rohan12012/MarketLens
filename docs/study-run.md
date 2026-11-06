# First full-period study run

The 24 full-period cases have been run on the saved study snapshot. The [five-year checks](study-subperiods.md) and [first findings report](findings.md)
are also available.

| Item | Value |
| --- | --- |
| Input snapshot | `data/study/20261106T011415Z-bbbd01c9/` |
| Reports | `reports/study/20261106T011618Z-d2aba2dd/` |
| Returned dates | January 4, 2016–December 31, 2025 |
| Price rows | 2,514 |
| Starting value per case | $10,000 |
| Cases | 24 |

The report folder contains `summary.csv`, `benchmark_metrics.csv`, and
`settings.json`. Each case also has holdings, weights, portfolio values, daily
returns, and a rebalance log. Return fields in CSVs are decimals; `0.10` means 10%.
Turnover is a fraction, not a dollar amount. Fees and portfolio values are dollars.

The settings record the input checksum, source metadata, allocations, cost rates,
package versions, and hashes of the calculation code and study brief. Input prices
are checked against the snapshot checksum before a run. Generated data and reports
remain local and are excluded from Git.

## Checks on this run

- All 24 allocation, strategy, and cost combinations are present and unique.
- Buy-and-hold ending values match a separate starting-weight/price-ratio calculation.
- Zero-cost daily ending values match the original analytics calculation.
- At each rebalance, new holdings plus fees equal the value before trading.
- Sales minus purchases equals the fee paid from portfolio capital.

These are accounting checks, not independent verification of provider prices.
No claim about which strategy is preferable is made from this run alone.

## Repeat the run

From the project folder:

```bash
python -m marketlens.run_study data/study/20261106T011415Z-bbbd01c9
```

The command uses no network access and writes a new report folder each time.
It does not overwrite the original results.

## Query the results with SQL

```bash
python -m marketlens.store_study reports/study/20261106T011618Z-d2aba2dd
```

The import stores all 24 cases in `data/study/study.sqlite`. Repeating an unchanged
import does not duplicate rows. The query in `docs/analysis.sql` shows the six
10-basis-point cases beside their zero-cost baselines. It reports ending value,
fees paid, and the reduction in ending value. These last two amounts can differ
because paid fees also change subsequent investment returns.
