-- Migration 005: Row Level Security policies
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_usage_log ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (for backend API)
-- These policies apply to authenticated users via Supabase Auth JWT

CREATE POLICY "Users see own conversations"
    ON conversations FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users insert own conversations"
    ON conversations FOR INSERT
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "Users update own conversations"
    ON conversations FOR UPDATE
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users see own messages"
    ON messages FOR SELECT
    USING (session_id IN (
        SELECT session_id FROM conversations WHERE user_id = auth.uid()::text
    ));

CREATE POLICY "Users insert own messages"
    ON messages FOR INSERT
    WITH CHECK (session_id IN (
        SELECT session_id FROM conversations WHERE user_id = auth.uid()::text
    ));

CREATE POLICY "Users see own profile"
    ON user_profiles FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users update own profile"
    ON user_profiles FOR UPDATE
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users see own tool usage"
    ON tool_usage_log FOR SELECT
    USING (user_id = auth.uid()::text);
