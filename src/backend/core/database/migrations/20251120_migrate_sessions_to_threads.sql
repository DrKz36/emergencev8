-- 20251120_migrate_sessions_to_threads.sql
-- Migration legacy sessions -> threads/messages
-- 1. Create threads for sessions that don't have one (using session_id as thread_id)
-- 2. Extract messages from session_data JSON and insert into messages
-- 3. Drop sessions table

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    session_data TEXT,
    metadata TEXT,
    summary TEXT
);

PRAGMA foreign_keys = ON;

-- 1. Backfill threads from sessions
INSERT OR IGNORE INTO threads (
    id,
    session_id,
    user_id,
    type,
    title,
    created_at,
    updated_at,
    meta
)
SELECT
    id,                 -- thread_id = session_id
    id,                 -- session_id
    user_id,
    'chat',             -- default type
    'Legacy Session',   -- default title
    created_at,
    updated_at,
    json_object('source', 'migration_sessions')
FROM sessions
WHERE id NOT IN (SELECT session_id FROM threads);

-- 2. Backfill messages from sessions.session_data
-- We use a recursive CTE or json_each if available. Assuming json_each is available.
-- Note: This relies on SQLite JSON1 extension which is standard in modern SQLite.

INSERT OR IGNORE INTO messages (
    id,
    thread_id,
    session_id,
    user_id,
    role,
    content,
    created_at,
    tokens
)
SELECT
    COALESCE(json_extract(value, '$.id'), lower(hex(randomblob(16)))), -- Generate ID if missing
    sessions.id, -- thread_id = session_id
    sessions.id, -- session_id
    sessions.user_id,
    COALESCE(json_extract(value, '$.role'), 'user'),
    COALESCE(json_extract(value, '$.content'), json_extract(value, '$.message'), ''),
    COALESCE(json_extract(value, '$.timestamp'), json_extract(value, '$.created_at'), sessions.created_at),
    json_extract(value, '$.tokens')
FROM sessions, json_each(sessions.session_data)
WHERE sessions.id IN (SELECT id FROM threads WHERE meta->>'source' = 'migration_sessions');

-- 3. Drop legacy sessions table
DROP TABLE IF EXISTS sessions;
