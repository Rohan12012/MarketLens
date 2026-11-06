# Calculation notes

## Daily returns and rebalancing

For an adjusted close price P, the simple return on observation t is:

```text
r[t] = P[t] / P[t-1] - 1
portfolio_return[t] = sum(weight[i] * asset_return[i, t])
value[t] = value[t-1] * (1 + portfolio_return[t])
```

There is no return for the first price observation. A panel with 252 price rows
therefore provides 251 daily returns.

Weights are constant across observations. This models rebalancing to the target
allocation each day, without transaction costs. In a buy-and-hold portfolio,
weights drift with prices; its results would generally differ.

The benchmark is compounded over the same dates, starting with the same capital.
Provider-adjusted closes account for splits and dividends. Dividends are not added
separately. This is a return approximation, not a reconstruction of brokerage cash
flows or trade executions.

## Metrics

Let N be the number of daily returns and W the final wealth divided by initial
wealth. Annualization uses 252 trading days.

| Metric | Calculation |
| --- | --- |
| Total return | W − 1 |
| Annualized return | W^(252/N) − 1 |
| Annualized volatility | Sample standard deviation of daily returns × sqrt(252) |
| Sharpe ratio | Mean daily excess return × 252 / annualized volatility |
| Drawdown | Current wealth / highest wealth so far − 1 |
| Maximum drawdown | Most negative drawdown in the sample |
| Asset correlation | Pearson correlation between daily asset return series |

The annual risk-free rate is converted to a daily rate as
`(1 + annual_rate) ** (1/252) - 1` before computing excess returns.
Volatility uses the sample standard deviation (`ddof=1`). Sharpe is undefined when
volatility is zero or numerically negligible. Correlation is undefined for a
constant return series.

Initial capital is included in the running peak. A loss on the first return day
therefore counts toward drawdown. Maximum drawdown is reported as a negative value.
CSV return metrics use decimals: `0.05` means 5%. Sharpe and correlation are unitless.

## Data checks and reproducibility

The price panel must have at least three observations, unique ticker columns,
and valid dates in ascending order without duplicates. All prices must be finite
and positive. For downloads, leading and trailing gaps from unequal histories remain
in the full-history export. Each security is validated between its first and last
returned observations. The comparison starts at the latest first-available date and
ends at the earliest last-available date, with at least three shared observations.
Internal gaps remain errors; prices are never forward-filled. First available means
the first returned price within the requested window, not a verified IPO date.

A snapshot preserves the returned adjusted closes. Its metadata records the source,
requested download dates, actual observation dates, retrieval timestamp, package
versions, and a SHA-256 checksum. Report settings record weights, benchmark, initial
capital, risk-free rate, and rebalancing assumptions. A checksum can reveal a changed
CSV; it does not establish that the original prices were correct.

Offline input uses the fully aligned prices.csv, not the gap-bearing
available_history.csv export. It is expected to use adjusted closes in one currency. The CSV alone
cannot verify those conventions. An offline run uses the entire supplied file and
records its path as the source; it does not retrieve the original provider metadata.

The tests check arithmetic and software behavior with synthetic inputs. They do
not establish provider accuracy or investment suitability.
