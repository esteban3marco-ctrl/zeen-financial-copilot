CREATE TABLE IF NOT EXISTS gate_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    gate TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS gate_audit_log_session_id_idx ON gate_audit_log(session_id);
CREATE INDEX IF NOT EXISTS gate_audit_log_user_id_idx ON gate_audit_log(user_id);
CREATE INDEX IF NOT EXISTS gate_audit_log_gate_action_idx ON gate_audit_log(gate, action);

ALTER TABLE gate_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own audit log" ON gate_audit_log
    FOR SELECT USING (auth.uid()::text = user_id);
