-- Migration 001: Initial Schema
-- Crée les tables fondamentales pour le fonctionnement de l'application.

-- Table pour stocker les sessions de chat et de débat.
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    history TEXT, -- JSON array of messages
    metadata TEXT, -- JSON object for themes, concepts, etc.
    summary TEXT,
    vivacity_score REAL DEFAULT 1.0,
    total_cost REAL DEFAULT 0.0
);

-- Table pour les messages individuels (non utilisée pour l'instant mais bon à avoir)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    agent TEXT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    cost REAL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
);

-- Table pour suivre les documents uploadés.
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    status TEXT NOT NULL, -- e.g., 'uploaded', 'processing', 'ready', 'error'
    character_count INTEGER,
    uploaded_at TEXT DEFAULT (datetime('now')),
    error_message TEXT
);

-- Tables pour le Knowledge Graph (simplifié)
CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
    node_id TEXT PRIMARY KEY,
    type TEXT NOT NULL, -- e.g., 'concept', 'entity'
    data TEXT, -- JSON object with node properties
    vivacity REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now')),
    last_updated TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    data TEXT, -- JSON object with edge properties
    FOREIGN KEY (source_id) REFERENCES knowledge_graph_nodes (node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES knowledge_graph_nodes (node_id) ON DELETE CASCADE
);
