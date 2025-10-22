-- Migration: Add 2FA/TOTP functionality
-- Date: 2025-10-22
-- Description: Add TOTP secret and backup codes to auth_allowlist for 2FA authentication
-- Phase P2 - Feature 9: Authentification 2FA (TOTP)

PRAGMA foreign_keys = ON;

-- Add totp_secret field to auth_allowlist (encrypted TOTP secret for 2FA)
ALTER TABLE auth_allowlist ADD COLUMN totp_secret TEXT DEFAULT NULL;

-- Add backup_codes field to auth_allowlist (JSON array of backup codes)
ALTER TABLE auth_allowlist ADD COLUMN backup_codes TEXT DEFAULT NULL;

-- Add totp_enabled_at timestamp (when 2FA was activated)
ALTER TABLE auth_allowlist ADD COLUMN totp_enabled_at TEXT DEFAULT NULL;

-- Create index for 2FA enabled users (for analytics/reporting)
CREATE INDEX IF NOT EXISTS idx_auth_allowlist_totp_enabled
ON auth_allowlist(totp_enabled_at)
WHERE totp_enabled_at IS NOT NULL;

-- Add audit log entries for 2FA events
-- (auth_audit_log table already exists, no changes needed)
-- Event types to log:
--   - '2fa_enabled' when user activates 2FA
--   - '2fa_disabled' when user deactivates 2FA
--   - '2fa_verified' when user successfully verifies TOTP code
--   - '2fa_failed' when TOTP verification fails
--   - 'backup_code_used' when backup code is consumed
