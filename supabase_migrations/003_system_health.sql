-- ============================================================
-- Ridgecrest Designs — System Health Table
-- Run this in your Supabase SQL Editor
-- ============================================================

CREATE TABLE public.system_health (
    id           BIGSERIAL PRIMARY KEY,
    component    VARCHAR(100) NOT NULL,
    status       VARCHAR(10)  NOT NULL,  -- ok | fail
    detail       TEXT,
    checked_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_health_component
    ON system_health (component, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_health_checked
    ON system_health (checked_at DESC);

-- RLS
ALTER TABLE system_health ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can read system_health"
    ON system_health FOR SELECT TO authenticated
    USING (has_role(auth.uid(), 'admin'::app_role));

CREATE POLICY "service_role_all" ON system_health
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
