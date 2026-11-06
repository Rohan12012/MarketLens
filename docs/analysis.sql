-- Compare each cost scenario with the same allocation and strategy at zero cost.
-- Bind :run_id to a stored run and :cost_bps to the rate to inspect.
SELECT scenario.allocation,
       scenario.strategy,
       scenario.cost_bps,
       ROUND(scenario.ending_value, 2) AS ending_value,
       ROUND(scenario.total_cost, 2) AS fees_paid,
       ROUND(baseline.ending_value - scenario.ending_value, 2) AS ending_value_reduction
FROM study_results AS scenario
JOIN study_results AS baseline
  ON baseline.run_id = scenario.run_id
 AND baseline.allocation = scenario.allocation
 AND baseline.strategy = scenario.strategy
 AND baseline.cost_bps = 0
WHERE scenario.run_id = :run_id
  AND scenario.cost_bps = :cost_bps
ORDER BY scenario.allocation, scenario.strategy;
