-- Restrict the comparison to the three recorded runs so repeated imports do not
-- add extra observations. Rank strategies separately for each cost assumption.
WITH ranked AS (
    SELECT result.*,
           DENSE_RANK() OVER (
               PARTITION BY run_id, allocation, cost_bps
               ORDER BY total_return DESC
           ) AS return_rank
    FROM study_results AS result
    WHERE run_id IN (:full_run, :first_run, :second_run)
)
SELECT run.first_date,
       run.last_date,
       scenario.run_id,
       scenario.allocation,
       scenario.strategy,
       scenario.cost_bps,
       scenario.total_return,
       scenario.return_rank,
       scenario.volatility,
       scenario.max_drawdown,
       scenario.ending_value,
       scenario.total_cost,
       scenario.turnover,
       baseline.ending_value - scenario.ending_value AS ending_value_reduction
FROM ranked AS scenario
JOIN study_runs AS run ON run.run_id = scenario.run_id
JOIN study_results AS baseline
  ON baseline.run_id = scenario.run_id
 AND baseline.allocation = scenario.allocation
 AND baseline.strategy = scenario.strategy
 AND baseline.cost_bps = 0
ORDER BY run.first_date, run.last_date, scenario.allocation,
         scenario.cost_bps, scenario.return_rank, scenario.strategy;
