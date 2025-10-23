-- 20251024_auth_sessions_user_id.sql
-- Ensure auth_sessions has a user_id column for multi-session tracking

ALTER TABLE auth_sessions ADD COLUMN user_id TEXT;
