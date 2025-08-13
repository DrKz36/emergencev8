-- Migration to create the cost_logs table for tracking API expenses.
-- This table is essential for the dashboard functionality.

CREATE TABLE IF NOT EXISTS cost_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    feature TEXT NOT NULL CHECK(feature IN ('chat', 'debate', 'document_processing', 'system')), -- 'chat', 'debate', etc.
    agent TEXT NOT NULL, -- 'neo', 'nexus', 'anima', 'user', 'system'
    model_name TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Indexes to speed up dashboard queries
CREATE INDEX IF NOT EXISTS idx_cost_logs_session_id ON cost_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_logs_timestamp ON cost_logs(timestamp);

