-- ============================================================
-- Ridgecrest Designs — Chat Messages
-- Run this in your Supabase SQL Editor
-- ============================================================
--
-- Powers the Command Center chat interface.
-- The Lovable frontend writes user messages; chat_agent.py
-- picks them up, processes with Claude, and writes responses back.
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL    PRIMARY KEY,
    session_id  UUID         NOT NULL,
    role        VARCHAR(20)  NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT         NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'processing', 'done')),
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_messages_pending
    ON chat_messages (status, created_at)
    WHERE role = 'user' AND status = 'pending';

-- Enable Row Level Security
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Service role has full access (used by chat_agent.py via edge function)
CREATE POLICY "service_role_all" ON chat_messages
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Authenticated users can read and insert
CREATE POLICY "authenticated_all" ON chat_messages
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

-- Anon can insert (user messages from Lovable) and read
CREATE POLICY "anon_insert" ON chat_messages
    FOR INSERT TO anon
    WITH CHECK (true);

CREATE POLICY "anon_select" ON chat_messages
    FOR SELECT TO anon
    USING (true);
