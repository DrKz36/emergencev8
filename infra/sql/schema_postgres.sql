-- Schema PostgreSQL pour ÉMERGENCE V8
-- Migration depuis SQLite vers Cloud SQL
-- Inclut pgvector pour embeddings (remplace Chroma)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Full-text search

-- ============================================
-- AUTH TABLES (migration depuis SQLite)
-- ============================================

CREATE TABLE auth_allowlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    password_hash VARCHAR(255),
    password_must_reset BOOLEAN DEFAULT FALSE,
    totp_secret VARCHAR(255),
    totp_enabled BOOLEAN DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

CREATE INDEX idx_auth_allowlist_email ON auth_allowlist(email);
CREATE INDEX idx_auth_allowlist_role ON auth_allowlist(role);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by VARCHAR(255),
    revoked_reason TEXT,
    FOREIGN KEY (email) REFERENCES auth_allowlist(email) ON DELETE CASCADE
);

CREATE INDEX idx_auth_sessions_email ON auth_sessions(email);
CREATE INDEX idx_auth_sessions_expires_at ON auth_sessions(expires_at);
CREATE INDEX idx_auth_sessions_revoked_at ON auth_sessions(revoked_at);

CREATE TABLE auth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    success BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_auth_audit_log_email ON auth_audit_log(email);
CREATE INDEX idx_auth_audit_log_timestamp ON auth_audit_log(timestamp);
CREATE INDEX idx_auth_audit_log_action ON auth_audit_log(action);

-- ============================================
-- SESSIONS/THREADS TABLES
-- ============================================

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,  -- Email or OAuth sub
    type VARCHAR(50) DEFAULT 'chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_data JSONB,
    metadata JSONB,
    summary TEXT,
    archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_type ON sessions(type);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_archived ON sessions(archived);

-- ============================================
-- MESSAGES TABLE
-- ============================================

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    agent_id VARCHAR(50),
    model VARCHAR(100),
    provider VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10, 6),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_agent_id ON messages(agent_id);
CREATE INDEX idx_messages_role ON messages(role);

-- ============================================
-- DOCUMENTS TABLE (avec pgvector pour RAG)
-- ============================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id UUID,
    filename VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    content_text TEXT,
    summary TEXT,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_session_id ON documents(session_id);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_filename ON documents(filename);

-- Document chunks avec embeddings (remplace Chroma)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 = 384 dimensions
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON document_chunks(chunk_index);

-- Index IVFFLAT pour recherche vectorielle rapide (pgvector)
-- lists = sqrt(nb_rows) recommandé, on commence avec 100 listes
CREATE INDEX idx_chunks_embedding_ivfflat
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Alternative: Index HNSW (meilleure précision mais plus lent à construire)
-- CREATE INDEX idx_chunks_embedding_hnsw
-- ON document_chunks
-- USING hnsw (embedding vector_cosine_ops);

-- ============================================
-- MEMORY TABLES (STM/LTM avec pgvector)
-- ============================================

CREATE TABLE memory_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id UUID,
    fact_text TEXT NOT NULL,
    fact_type VARCHAR(50) DEFAULT 'stm',  -- 'stm' ou 'ltm'
    embedding vector(384),
    importance_score DECIMAL(3, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    metadata JSONB,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX idx_memory_user_id ON memory_facts(user_id);
CREATE INDEX idx_memory_session_id ON memory_facts(session_id);
CREATE INDEX idx_memory_type ON memory_facts(fact_type);
CREATE INDEX idx_memory_created_at ON memory_facts(created_at);

CREATE INDEX idx_memory_embedding_ivfflat
ON memory_facts
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- COSTS TABLE (tracking LLM usage)
-- ============================================

CREATE TABLE costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id UUID,
    message_id UUID,
    agent_id VARCHAR(50),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
);

CREATE INDEX idx_costs_user_id ON costs(user_id);
CREATE INDEX idx_costs_session_id ON costs(session_id);
CREATE INDEX idx_costs_created_at ON costs(created_at);
CREATE INDEX idx_costs_provider ON costs(provider);
CREATE INDEX idx_costs_agent_id ON costs(agent_id);

-- ============================================
-- DEBATES TABLE
-- ============================================

CREATE TABLE debates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id UUID,
    topic TEXT NOT NULL,
    agents JSONB NOT NULL,  -- Liste agents participants
    max_rounds INTEGER DEFAULT 3,
    current_round INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX idx_debates_user_id ON debates(user_id);
CREATE INDEX idx_debates_session_id ON debates(session_id);
CREATE INDEX idx_debates_status ON debates(status);

-- ============================================
-- API USAGE TABLE (monitoring)
-- ============================================

CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id VARCHAR(255),
    endpoint VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB
);

CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint);

-- ============================================
-- BENCHMARKS TABLE
-- ============================================

CREATE TABLE benchmark_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    benchmark_name VARCHAR(100) NOT NULL,
    scenario_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    result JSONB,
    metrics JSONB,
    error_message TEXT
);

CREATE INDEX idx_benchmark_runs_user_id ON benchmark_runs(user_id);
CREATE INDEX idx_benchmark_runs_status ON benchmark_runs(status);
CREATE INDEX idx_benchmark_runs_started_at ON benchmark_runs(started_at);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers pour updated_at
CREATE TRIGGER update_sessions_updated_at
BEFORE UPDATE ON sessions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_auth_allowlist_updated_at
BEFORE UPDATE ON auth_allowlist
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Fonction pour recherche vectorielle avec score
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(384),
    search_user_id VARCHAR(255),
    limit_count INTEGER DEFAULT 5,
    similarity_threshold DECIMAL DEFAULT 0.7
)
RETURNS TABLE(
    chunk_id UUID,
    document_id UUID,
    filename VARCHAR(500),
    content TEXT,
    similarity DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id AS chunk_id,
        dc.document_id,
        d.filename,
        dc.content,
        (1 - (dc.embedding <=> query_embedding))::DECIMAL AS similarity
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    WHERE d.user_id = search_user_id
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VIEWS UTILES
-- ============================================

-- Vue: Sessions avec compteurs messages/coûts
CREATE VIEW sessions_with_stats AS
SELECT
    s.id,
    s.user_id,
    s.type,
    s.created_at,
    s.updated_at,
    s.archived,
    COUNT(DISTINCT m.id) AS message_count,
    COALESCE(SUM(c.cost_usd), 0) AS total_cost_usd,
    MAX(m.created_at) AS last_message_at
FROM sessions s
LEFT JOIN messages m ON m.session_id = s.id
LEFT JOIN costs c ON c.session_id = s.id
GROUP BY s.id;

-- Vue: Coûts agrégés par user/jour
CREATE VIEW daily_costs_by_user AS
SELECT
    user_id,
    DATE(created_at) AS date,
    provider,
    agent_id,
    SUM(tokens_input) AS total_tokens_input,
    SUM(tokens_output) AS total_tokens_output,
    SUM(cost_usd) AS total_cost_usd,
    COUNT(*) AS request_count
FROM costs
GROUP BY user_id, DATE(created_at), provider, agent_id;

-- ============================================
-- PERMISSIONS (pour user application)
-- ============================================

-- Grant permissions au user emergence-app
GRANT CONNECT ON DATABASE emergence TO "emergence-app";
GRANT USAGE ON SCHEMA public TO "emergence-app";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "emergence-app";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "emergence-app";
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO "emergence-app";

-- Permissions futures tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "emergence-app";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO "emergence-app";

-- ============================================
-- CONFIGURATION OPTIMISATIONS
-- ============================================

-- Vacuum auto plus agressif (déjà configuré via Terraform flags)
-- shared_buffers, effective_cache_size, etc. configurés côté instance

COMMENT ON DATABASE emergence IS 'ÉMERGENCE V8 - Multi-agent AI platform with pgvector for RAG';
