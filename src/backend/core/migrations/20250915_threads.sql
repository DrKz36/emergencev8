-- 20250915_threads.sql
-- Schéma P1.5 "threads/messages/thread_docs" compatible V6 (id TEXT, created_at TEXT)
-- Idempotent (CREATE IF NOT EXISTS) + indexes requis par queries.py

PRAGMA foreign_keys = ON;

-- =========================
-- TABLE: users (optionnelle)
-- =========================
CREATE TABLE IF NOT EXISTS users (
  id         TEXT PRIMARY KEY,
  email      TEXT,
  created_at TEXT
);

-- =========================
-- TABLE: threads
-- =========================
CREATE TABLE IF NOT EXISTS threads (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  type       TEXT NOT NULL CHECK (type IN ('chat','debate')),
  title      TEXT,
  agent_id   TEXT,
  meta       JSON,
  archived   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Aide navigation: derniers threads actifs d’un user
CREATE INDEX IF NOT EXISTS idx_threads_user_updated
  ON threads (user_id, updated_at DESC);

-- Filtrage par type
CREATE INDEX IF NOT EXISTS idx_threads_user_type_updated
  ON threads (user_id, type, updated_at DESC);

-- =========================
-- TABLE: messages
-- =========================
-- Schéma cible V6 (sans session_id/timestamp obligatoires).
-- queries.add_message() gère aussi un legacy INT PK si présent, mais on crée ici en TEXT UUID.
CREATE TABLE IF NOT EXISTS messages (
  id         TEXT PRIMARY KEY,
  thread_id  TEXT NOT NULL,
  role       TEXT NOT NULL CHECK (role IN ('user','assistant','system','note')),
  content    TEXT NOT NULL,
  agent_id   TEXT,           -- nullable, compat agent catalogue si présent
  tokens     INTEGER,
  meta       JSON,
  created_at TEXT NOT NULL,
  FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
);

-- Accès chronologique par thread
CREATE INDEX IF NOT EXISTS idx_messages_thread_created
  ON messages (thread_id, created_at);

-- =========================
-- TABLE: thread_docs
-- =========================
-- Liaison d’un thread avec des documents (pondération + dernier usage)
CREATE TABLE IF NOT EXISTS thread_docs (
  thread_id    TEXT NOT NULL,
  doc_id       INTEGER NOT NULL,
  weight       REAL NOT NULL DEFAULT 1.0,
  last_used_at TEXT,
  PRIMARY KEY (thread_id, doc_id),
  FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
  FOREIGN KEY (doc_id)    REFERENCES documents(id) ON DELETE CASCADE
);

-- Consultation performante (last_used_at DESC)
CREATE INDEX IF NOT EXISTS idx_thread_docs_last_used
  ON thread_docs (thread_id, last_used_at DESC);

-- =========================
-- Vues (facultatif, non bloquant)
-- =========================
-- Exemple: vue des derniers messages par thread (facilite debug/export)
CREATE VIEW IF NOT EXISTS v_threads_last_msg AS
SELECT t.id AS thread_id, MAX(m.created_at) AS last_msg_at
FROM threads t
LEFT JOIN messages m ON m.thread_id = t.id
GROUP BY t.id;
