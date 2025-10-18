-- Migration: Ajouter conversation_id canonique
-- Date: 2025-10-18
-- Sprint 1: Clarification Session vs Conversation
--
-- Objectif: Séparer clairement Session WebSocket (éphémère) et Conversation (persistante)

-- Étape 1: Ajouter colonne conversation_id
ALTER TABLE threads ADD COLUMN conversation_id TEXT;

-- Étape 2: Initialiser avec id existant (rétrocompatibilité)
-- Toutes les conversations existantes gardent leur ID comme conversation_id
UPDATE threads SET conversation_id = id WHERE conversation_id IS NULL;

-- Étape 3: Index pour performance requêtes par utilisateur + conversation
CREATE INDEX IF NOT EXISTS idx_threads_user_conversation
ON threads(user_id, conversation_id);

-- Étape 4: Index composite pour requêtes fréquentes (user + type + conversation)
CREATE INDEX IF NOT EXISTS idx_threads_user_type_conversation
ON threads(user_id, type, conversation_id);

-- Validation post-migration
-- SELECT COUNT(*) FROM threads WHERE conversation_id IS NULL;
-- Expected: 0
