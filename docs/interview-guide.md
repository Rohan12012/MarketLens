# Explaining MarketLens in an interview

Use this as a checklist, not a script to memorize. Describe only the parts you can
explain and reproduce. Do not imply a real client, trading account, measured business
impact, or independent implementation of code you cannot yet defend.

## A short walkthrough

1. State the question: how do concentration and rebalancing affect returns and risk?
2. Describe the fixed design: three stocks, two allocations, three strategies, four
   cost rates, and three windows. Explain why choices were fixed before the comparison.
3. Show one finding: the highest-return strategy changes between the two five-year
   windows, and the second window's ranking changes when costs are introduced.
4. Open the SQL query. Explain the baseline join and the ranking partitions.
5. Show the Validation tab. Distinguish software tests, accounting reconciliation,
   a calendar check, and the unfinished independent price check.
6. Finish with the limitations, including retrospective selection and model execution.

## Questions to work through

**What is one row in each table?**
`study_runs` has one row per completed run. `study_results` has one row per run,
allocation, strategy, and cost rate. Its composite primary key prevents duplicate cases.

**Why does the cost query need several join conditions?**
A baseline must match the same run, allocation, and strategy, with cost set to zero.
Leaving out a condition can pair the wrong cases or multiply rows.

**What does DENSE_RANK do here?**
It ranks strategies within each run, allocation, and cost rate. Equal returns share
a rank. Rank 1 means the highest return in that group, not statistical superiority.

**Why can fees paid differ from the ending-value reduction?**
Fees remove capital that would otherwise remain invested. Subsequent gains or
losses affect that capital, so their final impact differs from the sum of fees.

**How does monthly rebalancing avoid retroactive returns?**
The old holdings earn that day's return. Trades happen at the modeled close, and
new holdings affect the next observation. No final-date rebalance is charged.

**How was the analysis checked?**
Small synthetic cases have hand-calculated answers. SQL tests execute real queries
on temporary databases. Actual export checks reconcile holdings, values, and fees.
The calendar audit compares date sets in both directions. None verifies market
prices against another source; that separate check is still open.

**Why use Python and SQL?**
Python calculates returns and simulates changing holdings. SQL stores runs and
performs scenario comparisons. The price calculations are not implemented in SQL;
do not describe the project as a SQL-only pipeline.

**What would improve the study?**
An accessible independent price source, broader predeclared asset selections,
more realistic execution assumptions, historical risk-free rates, and uncertainty
analysis. These are remaining work, not completed features.

## Before listing the project on a resume

Be able to calculate one return, explain one rebalance, run the SQL comparison,
and trace a number from the dashboard to an export and its source snapshot.
A smaller explanation you understand is stronger than an ambitious claim you cannot defend.
