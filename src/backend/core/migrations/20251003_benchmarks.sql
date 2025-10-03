-- 20251003_benchmarks.sql
-- Introduces persistence tables for benchmark matrices and runs.

CREATE TABLE IF NOT EXISTS benchmark_matrices (
    id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    edge_mode_enabled INTEGER NOT NULL DEFAULT 0,
    context TEXT,
    runs_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    average_cost REAL NOT NULL DEFAULT 0,
    median_latency_ms REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id TEXT PRIMARY KEY,
    matrix_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    agent_topology TEXT NOT NULL,
    orchestration_mode TEXT NOT NULL,
    memory_mode TEXT NOT NULL,
    success INTEGER NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    error_message TEXT,
    executor_details TEXT,
    config_metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(matrix_id) REFERENCES benchmark_matrices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_matrix ON benchmark_runs(matrix_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_runs_scenario ON benchmark_runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_matrices_scenario ON benchmark_matrices(scenario_id);
