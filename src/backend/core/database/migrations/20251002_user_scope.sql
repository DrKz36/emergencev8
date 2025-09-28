-- 20251002_user_scope.sql
-- Introduce user_id columns for multi-session persistence
ALTER TABLE threads ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE thread_docs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_threads_user_type_updated ON threads(user_id, type, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_thread_docs_user ON thread_docs(user_id, thread_id, doc_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_uploaded ON documents(user_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user ON document_chunks(user_id, document_id);

UPDATE threads SET user_id = COALESCE(user_id, session_id);
UPDATE messages SET user_id = COALESCE(user_id, session_id);
UPDATE thread_docs SET user_id = COALESCE(user_id, session_id);
UPDATE documents SET user_id = COALESCE(user_id, session_id);
UPDATE document_chunks SET user_id = COALESCE(user_id, session_id);
UPDATE auth_sessions SET user_id = COALESCE(user_id, id);
