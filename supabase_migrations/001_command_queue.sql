-- ============================================================
-- Ridgecrest Designs — Command Queue
-- Run this in your Supabase SQL Editor
-- ============================================================

-- Command queue: written by Lovable Command Center,
-- polled and executed by local command_executor.py every 30 seconds.

CREATE TABLE IF NOT EXISTS command_queue (
    id           BIGSERIAL PRIMARY KEY,
    command_type VARCHAR(50)  NOT NULL,
        -- pause_campaign | enable_campaign | pause_all | enable_all
    platform     VARCHAR(30)  NOT NULL DEFAULT 'all',
        -- google_ads | meta | microsoft_ads | all
    external_id  VARCHAR(100),
        -- platform-native campaign ID (null for bulk commands)
    params       JSONB        NOT NULL DEFAULT '{}',
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending',
        -- pending | processing | completed | failed
    result       TEXT,
    created_by   VARCHAR(100) NOT NULL DEFAULT 'command_center',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    executed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_command_queue_status
    ON command_queue (status, created_at);

-- Enable Row Level Security
ALTER TABLE command_queue ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (used by command_executor.py and edge function)
CREATE POLICY "service_role_all" ON command_queue
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users (Lovable frontend) to insert and read
CREATE POLICY "authenticated_insert" ON command_queue
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "authenticated_select" ON command_queue
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow anon to insert (for Lovable if using anon key)
CREATE POLICY "anon_insert" ON command_queue
    FOR INSERT
    TO anon
    WITH CHECK (true);

CREATE POLICY "anon_select" ON command_queue
    FOR SELECT
    TO anon
    USING (true);
