-- Migration: Add oauth_sub column to auth_allowlist for Google OAuth support
-- Date: 2025-10-20
-- Purpose: Support Google OAuth subject identifier in auth_allowlist

-- Add oauth_sub column to auth_allowlist (nullable for backward compatibility)
ALTER TABLE auth_allowlist ADD COLUMN oauth_sub TEXT;

-- Create index for faster OAuth sub lookups
CREATE INDEX IF NOT EXISTS idx_auth_allowlist_oauth_sub ON auth_allowlist(oauth_sub)
WHERE oauth_sub IS NOT NULL;
