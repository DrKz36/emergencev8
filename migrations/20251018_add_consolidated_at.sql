-- Migration Sprint 2: Ajout colonne consolidated_at pour tracking consolidation LTM
-- Date: 2025-10-18
-- Objectif: Tracker quels threads archivés ont été consolidés en ChromaDB

-- Ajouter colonne consolidated_at (timestamp ISO8601)
ALTER TABLE threads ADD COLUMN consolidated_at TEXT;

-- Index pour requêtes de threads non consolidés (WHERE archived=1 AND consolidated_at IS NULL)
-- Note: SQLite supporte les index partiels depuis version 3.8.0
CREATE INDEX IF NOT EXISTS idx_threads_archived_not_consolidated
ON threads(archived, consolidated_at)
WHERE archived = 1 AND consolidated_at IS NULL;

-- Note: consolidated_at restera NULL tant que le thread n'a pas été consolidé
-- Sera rempli avec datetime.now(timezone.utc).isoformat() lors de la consolidation
