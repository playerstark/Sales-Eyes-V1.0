-- Sales Eyes V1.0 — Database Initialization
-- Runs automatically on first container start (docker-entrypoint-initdb.d)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- for fast text search later (Day 9)

-- =========================================================
-- 1. users
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 2. companies  (scraped/researched target companies)
-- =========================================================
CREATE TABLE IF NOT EXISTS companies (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,
    website_url       VARCHAR(512),
    industry          VARCHAR(255),
    company_size      VARCHAR(100),
    tech_stack        JSONB DEFAULT '[]'::jsonb,
    scraped_content   TEXT,
    news_data         JSONB DEFAULT '[]'::jsonb,
    intelligence_data JSONB DEFAULT '{}'::jsonb,   -- Company Intelligence Agent output (Day 3)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 3. prospects  (individual contacts at a company)
-- =========================================================
CREATE TABLE IF NOT EXISTS prospects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    full_name       VARCHAR(255) NOT NULL,
    title           VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    linkedin_url    VARCHAR(512),
    status          VARCHAR(50) NOT NULL DEFAULT 'new',  -- new, researched, contacted, meeting_scheduled, won, lost
    tags            TEXT[] DEFAULT '{}',
    pain_points     JSONB DEFAULT '[]'::jsonb,   -- Pain Point Detection Agent output (Day 4)
    opportunities   JSONB DEFAULT '[]'::jsonb,   -- Opportunity Matching Agent output (Day 4)
    sales_strategy  JSONB DEFAULT '{}'::jsonb,   -- Sales Strategy Agent output (Day 4)
    generated_scripts JSONB DEFAULT '[]'::jsonb, -- Script Engine outputs (Day 6)
    outreach_templates JSONB DEFAULT '[]'::jsonb,-- Outreach Generator outputs (Day 7)
    meeting_notes   JSONB DEFAULT '[]'::jsonb,   -- CRM Notes Generator outputs (Day 8)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 4. document_profiles  (uploaded sales materials -> extracted voice profile)
-- =========================================================
CREATE TABLE IF NOT EXISTS document_profiles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name         VARCHAR(255) NOT NULL,
    file_type         VARCHAR(20) NOT NULL,   -- pdf, docx, txt
    raw_text          TEXT,
    voice_profile      JSONB DEFAULT '{}'::jsonb, -- tone, methodology, talking points, USPs (Day 5)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 5. user_settings  (product info, API keys, preferences)
-- =========================================================
CREATE TABLE IF NOT EXISTS user_settings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    product_name        VARCHAR(255),
    product_features     JSONB DEFAULT '[]'::jsonb,
    default_script_mode VARCHAR(50) DEFAULT 'blended',  -- framework | user_voice | blended
    default_framework   VARCHAR(50) DEFAULT 'spin',      -- spin | challenger | sandler
    news_api_key        VARCHAR(255),
    llm_api_key         VARCHAR(255),
    deepseek_api_key    VARCHAR(255),
    deepseek_endpoint   VARCHAR(512),
    newsapi_endpoint    VARCHAR(512),
    preferences         JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 6. research_sessions  (research pipeline for a prospect)
-- =========================================================
CREATE TABLE IF NOT EXISTS research_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prospect_input      TEXT NOT NULL,
    status              VARCHAR(50) NOT NULL DEFAULT 'planning',  -- planning | executing | completed | failed
    plan                JSONB DEFAULT '[]'::jsonb,  -- array of plan steps
    findings            JSONB DEFAULT '[]'::jsonb,  -- array of findings (populated as agents run)
    selected_finding_ids UUID[] DEFAULT '{}',  -- which findings the user selected
    methodology         VARCHAR(100),  -- SPIN, Challenger, Sandler, or custom
    generated_output    TEXT,  -- final script/email
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 7. plan_steps  (individual agent tasks in a research session)
-- =========================================================
CREATE TABLE IF NOT EXISTS plan_steps (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    step_order          INTEGER NOT NULL,
    agent_type          VARCHAR(100) NOT NULL,  -- Company Intelligence, Pain Point Detection, etc.
    description         TEXT NOT NULL,
    status              VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending | in_progress | completed | failed
    result              JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 8. findings  (individual research findings with confidence/relevancy)
-- =========================================================
CREATE TABLE IF NOT EXISTS findings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    plan_step_id        UUID REFERENCES plan_steps(id) ON DELETE SET NULL,
    finding_type        VARCHAR(100) NOT NULL,  -- company_info, pain_point, opportunity, etc.
    source_link         VARCHAR(512),
    source_header       VARCHAR(255),
    summary             TEXT NOT NULL,
    confidence_score    DECIMAL(3,2),  -- 0.0 to 1.0
    relevancy_score     DECIMAL(3,2),  -- 0.0 to 1.0
    raw_data            JSONB,
    is_selected         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- Indexes
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_companies_owner        ON companies(owner_id);
CREATE INDEX IF NOT EXISTS idx_prospects_owner        ON prospects(owner_id);
CREATE INDEX IF NOT EXISTS idx_prospects_company      ON prospects(company_id);
CREATE INDEX IF NOT EXISTS idx_prospects_status       ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_name_trgm    ON prospects USING gin (full_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm    ON companies USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_document_profiles_owner ON document_profiles(owner_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_owner ON research_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_plan_steps_session     ON plan_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_session       ON findings(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_plan_step     ON findings(plan_step_id);

-- =========================================================
-- updated_at auto-touch trigger
-- =========================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_prospects_updated_at BEFORE UPDATE ON prospects
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_research_sessions_updated_at BEFORE UPDATE ON research_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_plan_steps_updated_at BEFORE UPDATE ON plan_steps
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
