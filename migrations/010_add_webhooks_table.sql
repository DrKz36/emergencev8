-- Migration: Add webhooks table for external integrations
-- Created: 2025-10-24
-- Description: Enable webhook subscriptions for events (thread.created, message.sent, analysis.completed)

CREATE TABLE IF NOT EXISTS webhooks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,
    events TEXT NOT NULL,  -- JSON array of subscribed events
    active BOOLEAN NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    total_deliveries INTEGER NOT NULL DEFAULT 0,
    successful_deliveries INTEGER NOT NULL DEFAULT 0,
    failed_deliveries INTEGER NOT NULL DEFAULT 0
);

-- Index for querying webhooks by user
CREATE INDEX IF NOT EXISTS idx_webhooks_user_id ON webhooks(user_id);

-- Index for querying active webhooks
CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(active);

-- Table for webhook delivery logs (for debugging and retry)
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id TEXT PRIMARY KEY,
    webhook_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON payload sent
    status INTEGER NOT NULL,  -- HTTP status code (0 if failed to connect)
    response_body TEXT,  -- Response from webhook URL
    error TEXT,  -- Error message if delivery failed
    attempt INTEGER NOT NULL DEFAULT 1,  -- Retry attempt number (1, 2, 3)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
);

-- Index for querying deliveries by webhook
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook_id ON webhook_deliveries(webhook_id);

-- Index for querying deliveries by status (for retry queue)
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);

-- Index for querying deliveries by created_at (for cleanup)
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_created_at ON webhook_deliveries(created_at);
