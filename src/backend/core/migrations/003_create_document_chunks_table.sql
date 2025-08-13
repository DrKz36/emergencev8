-- Migration to create the document_chunks table.
-- This table stores the individual text chunks for each processed document,
-- which is essential for the Retrieval-Augmented Generation (RAG) system.

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata TEXT, -- JSON object for extra info
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);

