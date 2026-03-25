-- ============================================================
-- Ridgecrest Designs — Multi-Agent Marketing Automation Schema
-- ============================================================

-- Agent message bus (inter-agent communication)
CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,        -- 'all' for broadcast
    message_type VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending, processing, done, error
    priority INTEGER NOT NULL DEFAULT 5,              -- 1=critical, 5=normal, 10=low
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    error_detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_messages_to_status ON agent_messages(to_agent, status);
CREATE INDEX IF NOT EXISTS idx_agent_messages_created ON agent_messages(created_at DESC);

-- Campaigns (synced from Google Ads)
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    google_campaign_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',   -- ENABLED, PAUSED, REMOVED
    campaign_type VARCHAR(50) DEFAULT 'SEARCH',
    daily_budget_micros BIGINT DEFAULT 0,
    daily_budget_usd NUMERIC(10,2) GENERATED ALWAYS AS (daily_budget_micros / 1000000.0) STORED,
    bidding_strategy VARCHAR(50) DEFAULT 'MANUAL_CPC',
    target_cpa_micros BIGINT,
    service_category VARCHAR(80),         -- design_build, kitchen_remodel, etc.
    geo_targets TEXT[],
    platform VARCHAR(20) DEFAULT 'google_ads',  -- google_ads, meta, microsoft_ads
    managed_by VARCHAR(20) NOT NULL DEFAULT 'manual',  -- 'manual' = human-managed, 'claude_code' = Claude Code agency
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_synced_at TIMESTAMP WITH TIME ZONE
);

-- Ad Groups
CREATE TABLE IF NOT EXISTS ad_groups (
    id SERIAL PRIMARY KEY,
    google_ad_group_id VARCHAR(50) UNIQUE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',
    cpc_bid_micros BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ad_groups_campaign ON ad_groups(campaign_id);

-- Keywords
CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    google_keyword_id VARCHAR(50) UNIQUE,
    ad_group_id INTEGER REFERENCES ad_groups(id) ON DELETE CASCADE,
    keyword_text VARCHAR(255) NOT NULL,
    match_type VARCHAR(20) NOT NULL DEFAULT 'EXACT',  -- EXACT, PHRASE, BROAD
    status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',
    cpc_bid_micros BIGINT DEFAULT 0,
    quality_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_keywords_ad_group ON keywords(ad_group_id);

-- Ads / Creatives
CREATE TABLE IF NOT EXISTS ads (
    id SERIAL PRIMARY KEY,
    google_ad_id VARCHAR(50) UNIQUE,
    ad_group_id INTEGER REFERENCES ad_groups(id) ON DELETE CASCADE,
    ad_type VARCHAR(50) DEFAULT 'RESPONSIVE_SEARCH_AD',
    status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',
    headlines JSONB,       -- array of headline strings
    descriptions JSONB,    -- array of description strings
    final_urls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Claude-generated creative metadata
    ai_generated BOOLEAN DEFAULT FALSE,
    creative_notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_ads_ad_group ON ads(ad_group_id);

-- Performance metrics (daily snapshots per entity)
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    entity_type VARCHAR(20) NOT NULL,   -- campaign, ad_group, keyword, ad
    entity_id INTEGER NOT NULL,
    google_entity_id VARCHAR(50),
    -- Core metrics
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions NUMERIC(10,2) DEFAULT 0,
    cost_micros BIGINT DEFAULT 0,
    cost_usd NUMERIC(10,4) GENERATED ALWAYS AS (cost_micros / 1000000.0) STORED,
    -- Derived metrics (stored for speed)
    ctr NUMERIC(8,4),
    cpc_avg_micros BIGINT,
    cpa_micros BIGINT,
    conversion_rate NUMERIC(8,4),
    impression_share NUMERIC(8,4),
    -- Quality
    avg_position NUMERIC(6,2),
    quality_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (metric_date, entity_type, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_perf_date_type ON performance_metrics(metric_date, entity_type);
CREATE INDEX IF NOT EXISTS idx_perf_entity ON performance_metrics(entity_type, entity_id);

-- Optimization actions log
CREATE TABLE IF NOT EXISTS optimization_actions (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    action_type VARCHAR(80) NOT NULL,     -- bid_increase, bid_decrease, pause_keyword, etc.
    entity_type VARCHAR(20),
    entity_id INTEGER,
    google_entity_id VARCHAR(50),
    before_value JSONB,
    after_value JSONB,
    reason TEXT,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    result TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_opt_actions_created ON optimization_actions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_opt_actions_entity ON optimization_actions(entity_type, entity_id);

-- Budget tracking
CREATE TABLE IF NOT EXISTS budget_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    day_of_week VARCHAR(10),              -- friday, saturday, sunday, monday
    is_active_day BOOLEAN,
    total_spend_usd NUMERIC(10,2) DEFAULT 0,
    daily_cap_usd NUMERIC(10,2) DEFAULT 125.00,
    remaining_usd NUMERIC(10,2),
    campaign_breakdown JSONB,
    pacing_status VARCHAR(20),            -- under, on_track, over
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- Negative keywords library
CREATE TABLE IF NOT EXISTS negative_keywords (
    id SERIAL PRIMARY KEY,
    keyword_text VARCHAR(255) NOT NULL,
    match_type VARCHAR(20) DEFAULT 'BROAD',
    scope VARCHAR(20) DEFAULT 'account',  -- account, campaign, ad_group
    campaign_id INTEGER REFERENCES campaigns(id),
    ad_group_id INTEGER REFERENCES ad_groups(id),
    reason TEXT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(keyword_text, match_type, scope, campaign_id, ad_group_id)
);

-- Search term analysis
CREATE TABLE IF NOT EXISTS search_terms (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    search_term VARCHAR(500) NOT NULL,
    campaign_id INTEGER REFERENCES campaigns(id),
    ad_group_id INTEGER REFERENCES ad_groups(id),
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions NUMERIC(10,2) DEFAULT 0,
    cost_micros BIGINT DEFAULT 0,
    classification VARCHAR(20) DEFAULT 'unreviewed',  -- good, bad, negative, unreviewed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(report_date, search_term, campaign_id)
);

-- AI-generated reports
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,    -- daily, weekly, alert, creative_brief
    platform VARCHAR(20) DEFAULT 'google_ads',  -- google_ads, meta, microsoft_ads, all
    period_start DATE,
    period_end DATE,
    title TEXT,
    summary TEXT,
    body_markdown TEXT,
    metrics_snapshot JSONB,
    recommendations JSONB,
    created_by VARCHAR(50) DEFAULT 'reporting_agent',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_type_date ON reports(report_type, created_at DESC);

-- Creative briefs and variants (Claude-generated)
CREATE TABLE IF NOT EXISTS creative_briefs (
    id SERIAL PRIMARY KEY,
    ad_group_id INTEGER REFERENCES ad_groups(id),
    service_category VARCHAR(80),
    headlines JSONB,        -- array of headline options
    descriptions JSONB,     -- array of description options
    callout_extensions JSONB,
    sitelink_extensions JSONB,
    messaging_angle TEXT,
    status VARCHAR(20) DEFAULT 'draft',   -- draft, approved, deployed, retired
    performance_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE
);

-- System health / agent heartbeats
CREATE TABLE IF NOT EXISTS agent_heartbeats (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'alive',  -- alive, error, idle
    last_run_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_success_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB DEFAULT '{}',
    UNIQUE(agent_name)
);

-- Geo performance (zip/city level)
CREATE TABLE IF NOT EXISTS geo_performance (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    location_type VARCHAR(20),    -- zip, city
    location_value VARCHAR(50),
    campaign_id INTEGER REFERENCES campaigns(id),
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions NUMERIC(10,2) DEFAULT 0,
    cost_micros BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(metric_date, location_type, location_value, campaign_id)
);

-- Seed the negative keywords library with quality-signal exclusions
INSERT INTO negative_keywords (keyword_text, match_type, scope, reason) VALUES
    ('cheap', 'BROAD', 'account', 'Price-sensitive — filters low-budget prospects'),
    ('affordable', 'BROAD', 'account', 'Budget-focused — not aligned with premium positioning'),
    ('low cost', 'PHRASE', 'account', 'Budget-focused'),
    ('discount', 'BROAD', 'account', 'Discount seekers not target audience'),
    ('free', 'BROAD', 'account', 'Free services not offered'),
    ('diy', 'BROAD', 'account', 'Do-it-yourself intent — not a buyer'),
    ('how to', 'PHRASE', 'account', 'Informational, not transactional'),
    ('rent', 'BROAD', 'account', 'Renters do not make renovation decisions'),
    ('apartment', 'BROAD', 'account', 'Apartment context — low relevance'),
    ('condo', 'BROAD', 'account', 'Typically lower budget projects'),
    ('handyman', 'BROAD', 'account', 'Small jobs — not premium design-build'),
    ('repair', 'BROAD', 'account', 'Repair intent — too small scope'),
    ('fix', 'BROAD', 'account', 'Repair / fix intent'),
    ('template', 'BROAD', 'account', 'Non-custom intent'),
    ('jobs', 'BROAD', 'account', 'Employment seekers'),
    ('hiring', 'BROAD', 'account', 'Employment seekers'),
    ('salary', 'BROAD', 'account', 'Employment seekers'),
    ('school', 'BROAD', 'account', 'Educational intent'),
    ('course', 'BROAD', 'account', 'Educational intent'),
    ('software', 'BROAD', 'account', 'Wrong context — software products'),
    ('app', 'BROAD', 'account', 'Wrong context — software app intent')
ON CONFLICT DO NOTHING;

-- Seed initial budget parameters
INSERT INTO budget_snapshots (snapshot_date, day_of_week, is_active_day, total_spend_usd, daily_cap_usd, remaining_usd, pacing_status)
VALUES (CURRENT_DATE, to_char(CURRENT_DATE, 'day'),
    TRIM(to_char(CURRENT_DATE, 'day')) IN ('friday','saturday','sunday','monday'),
    0, 125.00, 125.00, 'under')
ON CONFLICT (snapshot_date) DO NOTHING;

-- Seed agent heartbeat rows
INSERT INTO agent_heartbeats (agent_name, status) VALUES
    ('orchestrator', 'idle'),
    ('performance_analyst', 'idle'),
    ('bid_budget_optimizer', 'idle'),
    ('creative_agent', 'idle'),
    ('reporting_agent', 'idle'),
    ('recommendation_agent', 'idle'),
    ('health_agent', 'idle')
ON CONFLICT (agent_name) DO NOTHING;
