-- Migration 20251028: Soft-delete threads (index + optimisation)
-- Objectif: Éviter perte définitive archives, permettre restauration
-- Date: 2025-10-28
-- Agent: Claude Code

-- Index pour accélérer requêtes "threads actifs" (archived=0)
-- Très utilisé dans get_threads() qui filtre archived=0 par défaut
CREATE INDEX IF NOT EXISTS idx_threads_archived_status
ON threads(archived, updated_at DESC);

-- Index partial pour threads archivés (pour futures features restauration)
CREATE INDEX IF NOT EXISTS idx_threads_archived_at
ON threads(archived_at DESC)
WHERE archived = 1;

-- Note: delete_thread() modifié pour soft-delete par défaut (queries.py ligne 1074)
-- Hard delete possible avec param hard_delete=True (admin uniquement)
