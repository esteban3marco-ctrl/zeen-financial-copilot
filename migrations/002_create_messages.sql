-- Migration 002: messages table with pgvector embedding support
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('human', 'ai', 'tool', 'system')),
    content         TEXT NOT NULL,
    tool_call_id    TEXT,
    tool_name       TEXT,
    tool_params     JSONB,
    -- 1536-dim embedding for OpenAI ada-002 or similar
    embedding       vector(1536),
    gate_decisions  JSONB,
    tokens_used     INT DEFAULT 0,
    model_used      TEXT,
    latency_ms      FLOAT DEFAULT 0.0,
    sequence_num    INT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_sequence ON messages(conversation_id, sequence_num);
-- pgvector IVFFlat index for approximate nearest-neighbor search
CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Helper function for semantic search
CREATE OR REPLACE FUNCTION search_messages(
    p_user_id TEXT,
    query_embedding vector(1536),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    role TEXT,
    session_id TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        m.id,
        m.content,
        m.role,
        m.session_id,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM messages m
    JOIN conversations c ON c.id = m.conversation_id
    WHERE c.user_id = p_user_id
      AND m.embedding IS NOT NULL
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
$$;
