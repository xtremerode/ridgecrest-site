-- ============================================================
-- Ridgecrest Admin Panel — Database Schema Extension
-- Run this against marketing_agent to add admin tables
-- ============================================================

-- Leads (project inquiry submissions)
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    city VARCHAR(100),
    service VARCHAR(100),          -- custom_home, whole_house_remodel, kitchen_remodel, bathroom_remodel, other
    budget VARCHAR(50),            -- 60k_150k, 150k_500k, 500k_1m, 1m_5m, 5m_plus
    source VARCHAR(50) DEFAULT 'inquiry_form',  -- google_ads, meta, microsoft_ads, organic, referral, direct, inquiry_form
    message TEXT,
    notes TEXT,
    status VARCHAR(30) DEFAULT 'new',  -- new, contacted, qualified, closed, dead
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_service ON leads(service);

-- Portfolio projects (metadata; HTML files are source of truth for now)
CREATE TABLE IF NOT EXISTS portfolio_projects (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    project_type VARCHAR(100),
    year INTEGER,
    description TEXT,
    sqft VARCHAR(50),
    duration VARCHAR(50),
    hero_img TEXT,
    gallery_imgs TEXT[],
    published BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Admin users
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'editor',  -- owner, admin, editor, viewer
    last_login TIMESTAMP WITH TIME ZONE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SEO settings per page
CREATE TABLE IF NOT EXISTS page_seo (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    meta_title TEXT,
    meta_desc TEXT,
    og_title TEXT,
    og_desc TEXT,
    og_image TEXT,
    canonical TEXT,
    robots VARCHAR(100) DEFAULT 'index, follow',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Redirects
CREATE TABLE IF NOT EXISTS redirects (
    id SERIAL PRIMARY KEY,
    from_path VARCHAR(500) UNIQUE NOT NULL,
    to_path VARCHAR(500) NOT NULL,
    redirect_type INTEGER DEFAULT 301,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
