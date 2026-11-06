# Concentration and rebalancing study

## Question

Does rebalancing change the returns and risk of a concentrated portfolio?
The intended reader is a hypothetical investment research team. There is no
external client or claimed business outcome.

## Setup

| Setting | Choice |
| --- | --- |
| Assets, in weight order | AAPL, MSFT, GOOGL |
| Benchmark | SPY |
| Starting capital | $10,000 |
| Full period | January 1, 2016 to January 1, 2026, end exclusive |
| Equal-weight allocation | One-third in each asset |
| Concentrated allocation | 80% AAPL, 10% MSFT, 10% GOOGL |
| Rebalancing | Buy-and-hold, monthly, daily |
| Cost rates | 0, 5, 10, 25 basis points per dollar bought or sold |

These choices are fixed before running the comparison. Every case uses the same
prices, dates, initial capital, and benchmark. Investigate missing prices rather
than filling or silently dropping them.

Run the full period and two separate checks: 2016–2020 and 2021–2025. Restart each
window with $10,000 and the same starting allocations. That gives 24 cases per
window: two allocations, three strategies, and four cost rates.

## Trading rules

Allocate at the first shared adjusted close and allow fractional model holdings.
The first return runs from that close to the next observation.

Buy-and-hold makes no further trades. Daily rebalancing restores target weights
after each day's return. Monthly rebalancing does so at the last shared trading
observation of each calendar month. New holdings earn the next period's return;
they do not change a return already earned. Skip rebalancing at the final date.

Adjusted closes are model execution prices. Actual trade prices could differ.

## Turnover and costs

Gross traded value is purchases plus sales, counted in dollars. One-way turnover
is half that amount divided by portfolio value immediately before trading and
fees. Sum event turnover for the period. Count scheduled rebalance checks even
when weights have not drifted; those checks have zero turnover.

Charge the cost rate on gross traded value. Ten basis points is 0.1%, so $500 of
purchases and sales costs $0.50 at that rate. Fees come out of portfolio capital.
New holdings must reach target weights after fees, and their value plus the fee
must equal the value before trading.

Exclude the starting purchase and any final liquidation from both turnover and
costs. Buy-and-hold therefore has zero recurring turnover and identical results
at every cost rate. The rates are hypothetical trading frictions, not measured
brokerage fees. Do not add another commission or spread charge. Taxes, market
impact, and execution delays are outside the model.

## What to compare

Report total return, annualized volatility, maximum drawdown, cumulative turnover,
rebalance count, and total dollar fees. Performance metrics use returns after
costs; keep zero-cost results for comparison.

Use 252 trading days for annualization and a fixed 0% annual risk-free rate for
Sharpe. This simplifies the comparison; historical interest rates were not always
zero. SPY is a buy-and-hold benchmark without recurring fees on the same dates.
A difference from SPY's total return is not risk-adjusted alpha.

## Limits

These companies were selected retrospectively and share technology-sector exposure.
Equal weights reduce dependence on one company but do not establish broad market
diversification. Findings may depend on the assets and dates, and current selections
introduce survivorship and hindsight bias. Results do not establish future returns
or how the strategies would perform across other stocks.

## Current status

The dashboard still uses its original daily model without costs. Separate strategy
functions in `marketlens/simulation.py` support buy-and-hold, monthly, and daily
rebalancing. Monthly and daily runs log trades, turnover, and fees. Their tests use
synthetic prices with known answers, including a zero-cost check against the
original daily calculation.

`marketlens/study.py` runs all 24 cases for a supplied price window and returns a
summary, detailed simulations, and benchmark metrics. The fixed dataset has been downloaded and checked; see [the data record](study-data.md).
The full-period run is complete; see [the run record](study-run.md). Both
[subperiod checks](study-subperiods.md) are also complete and stored in SQLite.
The SQL period comparison and [first findings report](findings.md) are complete.
Independent price checks and broader robustness work remain open.

The final report should explain the data, methods, findings, and limits, with
tables and charts traceable to a saved snapshot.
