-- Migration 009: Add consolidation tracking to threads table
-- This migration adds consolidated_at to track when archived threads were consolidated to LTM

-- Add consolidated_at column to track when thread memory was consolidated
ALTER TABLE threads ADD COLUMN consolidated_at TEXT;

-- Create index for consolidated_at to optimize queries for unconsolidated threads
CREATE INDEX IF NOT EXISTS idx_threads_consolidated_at
ON threads(consolidated_at);

-- Create index for archived+unconsolidated threads (for batch processing)
CREATE INDEX IF NOT EXISTS idx_threads_archived_unconsolidated
ON threads(archived, consolidated_at)
WHERE archived = 1 AND consolidated_at IS NULL;
