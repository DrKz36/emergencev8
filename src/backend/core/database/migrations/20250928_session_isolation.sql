-- 20250928_session_isolation.sql
-- Post-migration session isolation cleanup: populate session_id fields and seed admin account.
PRAGMA foreign_keys = ON;

-- Threads: ensure legacy rows get a session identifier (fallback to thread id).
UPDATE threads
   SET session_id = id
 WHERE session_id IS NULL OR session_id = '';
CREATE INDEX IF NOT EXISTS idx_threads_session_id ON threads(session_id);

-- Messages: align with parent thread session.
UPDATE messages
   SET session_id = (
       SELECT session_id FROM threads WHERE threads.id = messages.thread_id
   )
 WHERE session_id IS NULL OR session_id = '';
CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);

-- Thread documents: propagate session from owning thread.
UPDATE thread_docs
   SET session_id = (
       SELECT session_id FROM threads WHERE threads.id = thread_docs.thread_id
   )
 WHERE session_id IS NULL OR session_id = '';
CREATE INDEX IF NOT EXISTS idx_thread_docs_session ON thread_docs(session_id, thread_id);

-- Documents: default to the first associated thread's session.
UPDATE documents
   SET session_id = (
       SELECT session_id
         FROM thread_docs
        WHERE thread_docs.doc_id = documents.id
        LIMIT 1
   )
 WHERE session_id IS NULL OR session_id = '';
CREATE INDEX IF NOT EXISTS idx_documents_session_uploaded ON documents(session_id, uploaded_at DESC);

-- Document chunks: inherit from the parent document.
UPDATE document_chunks
   SET session_id = (
       SELECT session_id FROM documents WHERE documents.id = document_chunks.document_id
   )
 WHERE session_id IS NULL OR session_id = '';
CREATE INDEX IF NOT EXISTS idx_document_chunks_session ON document_chunks(session_id, document_id);

-- Seed the admin allowlist entry for the rollout.
INSERT OR IGNORE INTO auth_allowlist (
    email,
    role,
    note,
    created_at,
    created_by,
    password_hash,
    password_updated_at
) VALUES (
    'gonzalefernando@gmail.com',
    'admin',
    'migration-20250928',
    datetime('now'),
    'migration#20250928',
    '$2b$12$V52B.XATgcwdmKwm5YHJ.ujVD9O.avlSf2L0JWD5PiD22lkV.zkwS',
    datetime('now')
);
