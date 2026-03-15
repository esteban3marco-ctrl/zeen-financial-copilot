-- Migration 003: user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 TEXT NOT NULL UNIQUE,
    display_name            TEXT,
    email                   TEXT,
    role                    TEXT NOT NULL DEFAULT 'basic'
                                CHECK (role IN ('anonymous','basic','premium','advisor','admin')),
    compliance_jurisdiction TEXT NOT NULL DEFAULT 'US',
    portfolio_size_tier     TEXT CHECK (portfolio_size_tier IN (
                                'micro','small','medium','large','institutional'
                            )),
    risk_tolerance          TEXT CHECK (risk_tolerance IN (
                                'conservative','moderate','aggressive'
                            )),
    authorized_topics       TEXT[] NOT NULL DEFAULT ARRAY[
                                'budgeting','expense_tracking','general_finance',
                                'market_data','portfolio_view'
                            ],
    preferences             JSONB NOT NULL DEFAULT '{}',
    total_sessions          INT NOT NULL DEFAULT 0,
    total_messages          INT NOT NULL DEFAULT 0,
    last_active_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role);

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RPC for atomic session count increment
CREATE OR REPLACE FUNCTION increment_user_sessions(
    p_user_id TEXT,
    p_last_active TIMESTAMPTZ DEFAULT now()
)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE user_profiles
    SET total_sessions = total_sessions + 1,
        last_active_at = p_last_active,
        updated_at = now()
    WHERE user_id = p_user_id;
$$;
