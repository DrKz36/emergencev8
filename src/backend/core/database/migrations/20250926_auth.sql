-- 20250926_auth.sql
-- Auth allowlist + sessions + audit log (JWT HS256)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS auth_allowlist (
  email TEXT PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('member','admin')) DEFAULT 'member',
  note TEXT,
  created_at TEXT NOT NULL,
  created_by TEXT,
  revoked_at TEXT,
  revoked_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_allowlist_active
  ON auth_allowlist (revoked_at);

CREATE TABLE IF NOT EXISTS auth_sessions (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',
  ip_address TEXT,
  user_agent TEXT,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  revoked_by TEXT,
  metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_email
  ON auth_sessions (email);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_active
  ON auth_sessions (email, expires_at)
  WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS auth_audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  email TEXT,
  actor TEXT,
  metadata JSON,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_created
  ON auth_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_audit_event
  ON auth_audit_log (event_type);