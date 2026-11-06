# How the numbers are calculated

## Returns

For adjusted close prices P:

```text
asset_return[t] = P[t] / P[t-1] - 1
portfolio_return[t] = sum(weight[i] * asset_return[i, t])
value[t] = value[t-1] * (1 + portfolio_return[t])
```

The weighted-return formula above describes the dashboard's daily rebalanced,
zero-cost model. Buy-and-hold and monthly strategies instead track dollar holdings
as weights drift. There is no return for the first price, so 252 price observations
produce 251 returns.

The benchmark uses the same dates and starting capital. Prices already include
provider adjustments for splits and dividends; dividends are not added again.
These calculations approximate investment returns rather than reconstructing
brokerage trades and cash flows.

## Metrics

Let N be the number of returns and W be final value divided by starting value.
Annualization assumes 252 trading days.

| Metric | Formula |
| --- | --- |
| Total return | W − 1 |
| Annualized return | W^(252/N) − 1 |
| Annualized volatility | Sample standard deviation of daily returns × sqrt(252) |
| Sharpe ratio | Mean daily excess return × 252 / annualized volatility |
| Drawdown | Value / highest value so far − 1 |
| Maximum drawdown | Lowest drawdown in the period |
| Asset correlation | Pearson correlation of daily asset returns |

The daily risk-free rate is `(1 + annual_rate) ** (1/252) - 1`.
Volatility uses `ddof=1`, the sample standard deviation. Sharpe is undefined when
volatility is zero or negligible. Correlation is undefined for constant returns.

Starting capital counts as the first peak, so an immediate loss counts toward
drawdown. Drawdowns are negative. Return metrics in CSVs are decimals: `0.05`
means 5%. Sharpe and correlation have no units.

## Dates and missing prices

The aligned price table needs at least three rows, unique ticker columns, and
valid dates in ascending order without duplicates. Prices must be positive and
finite. Downloads keep each asset's full history, including gaps outside its
available dates. Each asset is checked between its first and last returned prices.

The portfolio comparison starts at the latest first-available date and ends at
the earliest last-available date. Gaps inside that period are errors; prices are
not forward-filled. First available means the earliest price returned in the
requested window. It is not a verified IPO date.

## Saved data

Snapshots keep the adjusted prices and metadata: source, requested dates, returned
dates, retrieval time, package versions, and a SHA-256 checksum of `prices.csv`.
Report settings record the weights, capital, benchmark, risk-free rate, and
rebalancing rule. The checksum can detect a changed file, not an incorrect price.

Offline mode reads the aligned `prices.csv`, not `available_history.csv`, which
may contain gaps. It uses every supplied row and records the input path as its
source; it does not recover the original provider metadata. The file is expected
to contain adjusted closes in one currency, but its numbers alone cannot verify
those conventions.

## Study strategies

The dashboard and CLI still use daily rebalancing without fees. The separate
study code adds buy-and-hold, monthly rebalancing, trade logs, and cost scenarios.
Fees are paid from capital and included in strategy returns. Trading schedules,
turnover definitions, and cost assumptions are recorded in
[the study plan](analysis-brief.md).
