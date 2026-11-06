# Concentration and rebalancing: first findings

## What was compared

AAPL, MSFT, and GOOGL in two starting allocations: equal weight, and 80% AAPL with
10% in each other stock. Each allocation was run as buy-and-hold, monthly
rebalancing, and daily rebalancing at 0, 5, 10, and 25 basis points per dollar
traded. Each window starts at $10,000. There are 72 cases across three windows.

Prices are Yahoo Finance adjusted closes from the saved study snapshot. The
comparison tables below come from `docs/study-comparison.sql`, which uses joins
and `DENSE_RANK()` to rank strategies separately within each run, allocation,
and cost rate. The report illustrates the 10-basis-point cases, then checks the
ranking across every tested rate. Returns shown are **total period returns**,
not annualized returns.

## Explore the rankings

A chart of the SQL results is saved locally at
`reports/study/strategy-rankings.html`. Open it with:

```bash
open reports/study/strategy-rankings.html
```

Choose a cost rate to see how strategy rankings change. Hover over a point for
its total return, maximum drawdown, and fees. Rank 1 is highest return; rank gaps
do not measure return differences. The three windows overlap and are separate
comparisons, not a continuous portfolio path.

The HTML contains the result data and loads the chart libraries from a CDN, so
viewing it may require an internet connection. To regenerate it from SQLite:

```bash
python -m marketlens.plot_study \
  20261106T011618Z-d2aba2dd \
  20261106T012503Z-1669ce24 \
  20261106T012508Z-d9f464da
```

## 1. The best-returning strategy changed with the period

At 10 basis points per dollar traded:

| Period | Allocation | Buy-and-hold | Monthly | Daily |
| --- | --- | ---: | ---: | ---: |
| 2016–2020 | Equal weight | 306.45% | 296.53% | 294.20% |
| 2016–2020 | Concentrated | 402.59% | 400.28% | 397.90% |
| 2021–2025 | Equal weight | 170.91% | 176.48% | 175.05% |
| 2021–2025 | Concentrated | 132.34% | 134.94% | 134.25% |
| 2016–2025 | Equal weight | 894.31% | 974.02% | 962.14% |
| 2016–2025 | Concentrated | 999.46% | 1047.87% | 1039.00% |

Buy-and-hold led both allocations in 2016–2020, but monthly rebalancing led both
in 2021–2025 and over the full ten years at this rate. The full-period result alone
would conceal the first five years' ranking. That ranking change is a reason to
report subperiods rather than select one strategy from the ten-year result.

Across all four cost rates, buy-and-hold led 2016–2020 and monthly led the full
period. For 2021–2025, daily had the highest return at zero cost; monthly led at
5, 10, and 25 basis points. The cost assumption changes that conclusion.

## 2. Equal weighting did not always produce a smaller drawdown

For monthly rebalancing at 10 basis points:

| Period | Equal-weight maximum drawdown | Concentrated maximum drawdown |
| --- | ---: | ---: |
| 2016–2020 | -29.62% | -34.09% |
| 2021–2025 | -35.23% | -31.87% |
| 2016–2025 | -35.23% | -34.09% |

Equal weighting had the smaller maximum drawdown in the first five-year window.
The concentrated allocation had the smaller drawdown in the second window and
the full period. These are observed outcomes for the selected stocks, not proof
that concentration reduces risk. All three stocks share sector exposure, and
maximum drawdown is only one risk measure.

## 3. Fees changed more than the dollar amount paid

Over the full period, at 10 basis points:

| Allocation | Strategy | Fees paid | Ending value below zero-cost case |
| --- | --- | ---: | ---: |
| Equal weight | Monthly | $159.70 | $381.69 |
| Equal weight | Daily | $641.20 | $1,566.89 |
| Concentrated | Monthly | $99.88 | $234.25 |
| Concentrated | Daily | $407.28 | $948.22 |

Daily rebalancing paid more fees than monthly for both allocations. The reduction
in ending value is larger than fees paid in these cases because fees also left
less money invested for subsequent returns. These columns measure different things;
ending-value reduction should not be labeled as commissions paid.

## What the results support

For the hypothetical research team, the useful conclusion is that allocation,
trading frequency, time window, and cost assumptions should be considered together.
The ten-year winner was not the winner in every subperiod. A zero-cost ranking
also did not always survive the addition of costs.

This does not establish an optimal allocation or trading rule. It is a historical
comparison of two fixed allocations in three retrospectively selected companies.
The table does not show that any strategy delivered risk-adjusted alpha versus SPY.

## Limits and remaining checks

- Provider prices have not been checked against an independent source. The
  [calendar audit](data-quality.md) found all 2,514 expected sessions, but that
  checks dates rather than price accuracy.
- Current stock selection introduces survivorship and hindsight bias. An equal
  allocation in these three companies is not a broadly diversified portfolio.
- Trades use adjusted closes and fractional model units. Actual fills, spreads,
  taxes, market impact, and delays are not reconstructed.
- Cost rates are hypothetical. Starting purchases and final liquidation are excluded.
- The two five-year windows restart from the target allocation. Their returns must
  not be chained to reconstruct a full-period strategy with drifting holdings.
- Sharpe calculations use a fixed 0% risk-free rate, not a historical rate series.
- These are descriptive comparisons. No statistical significance or future
  performance claim has been established.

## Reproduce the SQL output

After the three recorded reports have been imported into SQLite:

```bash
python -m marketlens.compare_periods \
  20261106T011618Z-d2aba2dd \
  20261106T012503Z-1669ce24 \
  20261106T012508Z-d9f464da
```

The command writes all 72 rows to `reports/study/period-comparison.csv` and prints
the 18 cases at 10 basis points. It selects explicit run IDs so repeated runs do
not silently enter the comparison. It checks that all three runs use the same
price snapshot and the planned windows.

See [the study plan](analysis-brief.md), [data record](study-data.md),
[full-period run](study-run.md), and [subperiod record](study-subperiods.md).
