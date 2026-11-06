PRAGMA foreign_keys = ON;

-- One row per completed study run. Keep its settings with the results.
CREATE TABLE IF NOT EXISTS study_runs (
    run_id TEXT PRIMARY KEY,
    prices_sha256 TEXT NOT NULL,
    summary_sha256 TEXT NOT NULL,
    settings_json TEXT NOT NULL,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL
);

-- One row per allocation, strategy, and assumed cost rate within a run.
CREATE TABLE IF NOT EXISTS study_results (
    run_id TEXT NOT NULL REFERENCES study_runs(run_id),
    allocation TEXT NOT NULL,
    strategy TEXT NOT NULL CHECK (strategy IN ('Buy-and-hold', 'Monthly', 'Daily')),
    cost_bps INTEGER NOT NULL CHECK (cost_bps >= 0),
    initial_value REAL NOT NULL CHECK (initial_value > 0),
    ending_value REAL NOT NULL CHECK (ending_value > 0),
    total_return REAL NOT NULL,
    volatility REAL NOT NULL CHECK (volatility >= 0),
    max_drawdown REAL NOT NULL CHECK (max_drawdown BETWEEN -1 AND 0),
    total_cost REAL NOT NULL CHECK (total_cost >= 0),
    turnover REAL NOT NULL CHECK (turnover >= 0),
    PRIMARY KEY (run_id, allocation, strategy, cost_bps)
);
