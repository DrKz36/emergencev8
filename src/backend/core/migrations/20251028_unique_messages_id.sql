-- Migration 20251028: Contrainte UNIQUE sur messages(id, thread_id)
-- Objectif: Éviter duplication messages (fix bug double envoi REST+WS)
-- Date: 2025-10-28
-- Agent: Claude Code

-- Protection anti-duplication: index unique sur (id, thread_id)
-- SQLite ne supporte pas ALTER TABLE ADD CONSTRAINT UNIQUE directement,
-- donc on utilise CREATE UNIQUE INDEX

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_id_thread_unique
ON messages(id, thread_id);

-- Note: Cette contrainte empêche INSERT de doublons même si custom message_id fourni
-- Complète la protection applicative ajoutée dans queries.py (ligne 1177-1189)
