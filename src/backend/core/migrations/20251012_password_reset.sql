-- Migration: Add password reset functionality
-- Date: 2025-10-12
-- Description: Add password_must_reset field to auth_allowlist and create password_reset_tokens table

-- Add password_must_reset field to auth_allowlist (for onboarding flow)
ALTER TABLE auth_allowlist ADD COLUMN password_must_reset INTEGER DEFAULT 1;

-- Create password_reset_tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT,
    FOREIGN KEY (email) REFERENCES auth_allowlist(email) ON DELETE CASCADE
);

-- Create indexes for password_reset_tokens
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email
ON password_reset_tokens(email);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at
ON password_reset_tokens(expires_at);

-- Set password_must_reset to 0 for existing users who already have a password
UPDATE auth_allowlist
SET password_must_reset = 0
WHERE password_hash IS NOT NULL AND password_hash != '';

-- Exempt admin users from password reset requirement
UPDATE auth_allowlist
SET password_must_reset = 0
WHERE role = 'admin';
