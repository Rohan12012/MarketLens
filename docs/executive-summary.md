# MarketLens: concentration and rebalancing

## Question and scope

For a hypothetical investment research team: how do portfolio concentration and
rebalancing frequency change historical returns and risk?

The study uses AAPL, MSFT, and GOOGL from 2016 through 2025. It compares equal
weights with an 80% AAPL / 10% MSFT / 10% GOOGL allocation, using buy-and-hold,
monthly, and daily rebalancing. Each starts with $10,000. Four cost assumptions
and three time windows produce 72 cases. SPY is the reference benchmark.

## Main findings

At 10 basis points per dollar bought or sold:

| Window | Highest-return strategy, both allocations |
| --- | --- |
| 2016–2020 | Buy-and-hold |
| 2021–2025 | Monthly rebalancing |
| 2016–2025 | Monthly rebalancing |

The zero-cost assumption changes the second five-year result: daily rebalancing
leads at zero cost, while monthly leads at 5, 10, and 25 basis points.

Equal weighting does not always produce the smaller maximum drawdown. Under
monthly rebalancing at 10 basis points, equal-weight drawdown is -29.62% versus
-34.09% for the concentrated allocation in 2016–2020. In 2021–2025 the ordering
reverses: -35.23% versus -31.87%.

For the equal-weight daily strategy over the full period, $641.20 in fees reduces
ending value by $1,566.89 relative to the zero-cost case. The difference reflects
fees and their effect on later investment returns.

## Implication for the research team

Present period, allocation, and cost assumptions alongside any strategy ranking.
Selecting a rule solely from the full-period return would hide a different ranking
in the first five years. These results support sensitivity analysis, not a claim
that one strategy is universally preferable.

## Evidence and limits

Python tracks holdings, turnover, and fees. SQLite stores each run and scenario;
SQL joins identify zero-cost baselines, and window functions rank strategies.
Saved snapshots, file hashes, trade logs, and automated tests support reproduction.
All 2,514 observed dates match the reference exchange calendar.

Independent price verification remains open. A fixed 12-point sample was prepared,
but the secondary-source probe returned HTML instead of price data. No sample is
marked independently verified. Current stock selection also introduces hindsight
and survivorship bias. The three companies share sector exposure; equal weighting
is not broad diversification. Trading assumptions exclude taxes and real execution
conditions. Historical outcomes do not establish future returns or statistical
significance.

See [findings](findings.md), [methods](analysis-brief.md),
[date audit](data-quality.md), and [price-verification status](price-verification.md).
