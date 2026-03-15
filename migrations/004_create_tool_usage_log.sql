-- Migration 004: tool_usage_log audit table
CREATE TABLE IF NOT EXISTS tool_usage_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    tool_name           TEXT NOT NULL,
    tool_params         JSONB NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL CHECK (status IN ('success','error','timeout','denied')),
    execution_time_ms   FLOAT NOT NULL DEFAULT 0.0,
    sandbox_used        BOOL NOT NULL DEFAULT false,
    error_message       TEXT,
    pre_gate_action     TEXT CHECK (pre_gate_action IN ('allow','deny','modify')),
    post_gate_action    TEXT CHECK (post_gate_action IN ('allow','deny','modify')),
    result_size_bytes   INT DEFAULT 0,
    secrets_redacted    INT DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_usage_user ON tool_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_session ON tool_usage_log(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage_log(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_created ON tool_usage_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_status ON tool_usage_log(status);
