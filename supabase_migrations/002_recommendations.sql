-- ============================================================
-- Ridgecrest Designs — Recommendations Table
-- Run this in your Supabase SQL Editor
-- ============================================================

CREATE TABLE public.recommendations (
    id              BIGSERIAL PRIMARY KEY,
    campaign_id     INTEGER,
    campaign_name   VARCHAR(255),
    platform        VARCHAR(30),
    action_type     VARCHAR(50) NOT NULL,
        -- budget_increase | budget_decrease | bid_increase | blitz |
        -- pause_campaign | shift_budget | daypart | review
    recommendation  TEXT NOT NULL,       -- one-line human-readable action
    reasoning       TEXT NOT NULL,       -- why this is recommended
    expected_impact TEXT,                -- estimated outcome
    risk_level      VARCHAR(20) NOT NULL DEFAULT 'medium',
        -- low | medium | high
    current_value   JSONB DEFAULT '{}',  -- e.g. {"daily_budget_usd": 45.00}
    proposed_value  JSONB DEFAULT '{}',  -- e.g. {"daily_budget_usd": 75.00}
    data_snapshot   JSONB DEFAULT '{}',  -- metrics that drove this recommendation
    guardrail_override BOOLEAN DEFAULT FALSE,
        -- true when action exceeds normal automated limits — requires human approval
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending | approved | dismissed | expired | executed | failed
    expires_at      TIMESTAMPTZ NOT NULL,
    email_sent      BOOLEAN DEFAULT FALSE,
    email_sent_at   TIMESTAMPTZ,
    approved_at     TIMESTAMPTZ,
    dismissed_at    TIMESTAMPTZ,
    executed_at     TIMESTAMPTZ,
    execution_result TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(50) NOT NULL DEFAULT 'recommendation_agent'
);

CREATE INDEX IF NOT EXISTS idx_recommendations_status
    ON recommendations (status, expires_at);

CREATE INDEX IF NOT EXISTS idx_recommendations_created
    ON recommendations (created_at DESC);

-- RLS
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can manage recommendations"
    ON recommendations FOR ALL TO authenticated
    USING (has_role(auth.uid(), 'admin'::app_role))
    WITH CHECK (has_role(auth.uid(), 'admin'::app_role));

CREATE POLICY "service_role_all" ON recommendations
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
