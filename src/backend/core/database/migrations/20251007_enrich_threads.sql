-- 20251007_enrich_threads.sql — Enrichissement métadonnées threads
-- Ajoute last_message_at, message_count, archival_reason pour améliorer l'accessibilité mémoire

PRAGMA foreign_keys = ON;

-- Ajouter colonnes si elles n'existent pas
ALTER TABLE threads ADD COLUMN last_message_at TEXT;
ALTER TABLE threads ADD COLUMN message_count INTEGER DEFAULT 0;
ALTER TABLE threads ADD COLUMN archival_reason TEXT;

-- Créer index pour optimiser les requêtes temporelles
CREATE INDEX IF NOT EXISTS idx_threads_last_message
  ON threads (user_id, last_message_at DESC);

CREATE INDEX IF NOT EXISTS idx_threads_archived_date
  ON threads (archived, last_message_at DESC);

-- Vue enrichie combinant threads + stats messages
CREATE VIEW IF NOT EXISTS v_threads_enriched AS
SELECT
  t.id,
  t.user_id,
  t.type,
  t.title,
  t.agent_id,
  t.meta,
  t.archived,
  t.archival_reason,
  t.created_at,
  t.updated_at,
  t.last_message_at,
  t.message_count,
  COUNT(DISTINCT m.id) as computed_message_count,
  MAX(m.created_at) as computed_last_message_at,
  SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) as user_message_count,
  SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) as assistant_message_count
FROM threads t
LEFT JOIN messages m ON m.thread_id = t.id
GROUP BY t.id;

-- Fonction de mise à jour automatique (trigger)
-- Note: SQLite nécessite des triggers pour auto-update
CREATE TRIGGER IF NOT EXISTS update_thread_message_stats_insert
AFTER INSERT ON messages
FOR EACH ROW
BEGIN
  UPDATE threads
  SET
    last_message_at = NEW.created_at,
    message_count = message_count + 1,
    updated_at = NEW.created_at
  WHERE id = NEW.thread_id;
END;

CREATE TRIGGER IF NOT EXISTS update_thread_message_stats_delete
AFTER DELETE ON messages
FOR EACH ROW
BEGIN
  UPDATE threads
  SET
    message_count = COALESCE(message_count - 1, 0),
    last_message_at = (
      SELECT MAX(created_at) FROM messages WHERE thread_id = OLD.thread_id
    ),
    updated_at = datetime('now')
  WHERE id = OLD.thread_id;
END;

-- Initialiser les données existantes
UPDATE threads
SET
  last_message_at = (
    SELECT MAX(m.created_at) FROM messages m WHERE m.thread_id = threads.id
  ),
  message_count = (
    SELECT COUNT(*) FROM messages m WHERE m.thread_id = threads.id
  )
WHERE last_message_at IS NULL OR message_count = 0;
