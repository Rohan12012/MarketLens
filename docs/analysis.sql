-- Run after importing a generated daily_returns.csv as daily_returns.
-- Returns are decimals, and these are arithmetic DAILY averages.
SELECT COUNT(*) AS trading_observations,
       AVG(CAST(Portfolio AS REAL)) AS average_daily_portfolio_return,
       AVG(CAST(Benchmark AS REAL)) AS average_daily_benchmark_return,
       AVG(CAST(Portfolio AS REAL) - CAST(Benchmark AS REAL)) AS average_daily_active_return,
       SUM(CASE WHEN CAST(Portfolio AS REAL) < 0 THEN 1 ELSE 0 END) AS negative_days
FROM daily_returns;
