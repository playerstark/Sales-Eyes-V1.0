-- Sales Eyes Intelligence Agent Schema
-- Creates tables for prospect intelligence research: search, extraction, identity resolution, verification

-- =========================================================
-- 1. intelligence_sessions
-- =========================================================
CREATE TABLE IF NOT EXISTS intelligence_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    research_session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    prospect_name       VARCHAR(255) NOT NULL,
    prospect_company    VARCHAR(255),

    status              VARCHAR(50) NOT NULL DEFAULT 'searching',  -- searching | extracting | resolving | verifying | completed | failed
    progress_percent    INTEGER NOT NULL DEFAULT 0,
    current_step        VARCHAR(100),

    config              JSONB DEFAULT '{}'::jsonb,  -- score_weights, thresholds, provider config snapshot
    error_message       TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intelligence_sessions_owner ON intelligence_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_sessions_status ON intelligence_sessions(status);


-- =========================================================
-- 2. research_queries
-- =========================================================
CREATE TABLE IF NOT EXISTS research_queries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES intelligence_sessions(id) ON DELETE CASCADE,

    query_text      TEXT NOT NULL,
    search_provider VARCHAR(50) NOT NULL,  -- duckduckgo, google, brave, etc.
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending | in_progress | completed | failed

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_queries_session ON research_queries(session_id);


-- =========================================================
-- 3. search_results
-- =========================================================
CREATE TABLE IF NOT EXISTS search_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id        UUID NOT NULL REFERENCES research_queries(id) ON DELETE CASCADE,

    result_index    INTEGER NOT NULL,  -- Position in result set
    title           VARCHAR(512),
    snippet         TEXT,
    url             VARCHAR(512) NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_results_query ON search_results(query_id);
CREATE INDEX IF NOT EXISTS idx_search_results_url ON search_results(url);


-- =========================================================
-- 4. sources
-- =========================================================
CREATE TABLE IF NOT EXISTS sources (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_result_id        UUID NOT NULL REFERENCES search_results(id) ON DELETE CASCADE,

    url                     VARCHAR(512) NOT NULL UNIQUE,
    title                   VARCHAR(512),
    domain                  VARCHAR(255),

    content_type            VARCHAR(100),
    raw_content             TEXT,
    extracted_text          TEXT,

    fetch_status            VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending | success | blocked | timeout | error
    fetch_error             VARCHAR(255),

    fetched_at              TIMESTAMPTZ,
    retention_expires_at    TIMESTAMPTZ,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);
CREATE INDEX IF NOT EXISTS idx_sources_retention ON sources(retention_expires_at);


-- =========================================================
-- 5. extracted_entities
-- =========================================================
CREATE TABLE IF NOT EXISTS extracted_entities (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_result_id                UUID NOT NULL REFERENCES search_results(id) ON DELETE CASCADE,

    entity_type                     VARCHAR(50) NOT NULL,  -- person | company | organization

    full_name                       VARCHAR(255),
    first_name                      VARCHAR(100),
    last_name                       VARCHAR(100),

    current_title                   VARCHAR(255),
    current_company                 VARCHAR(255),
    location                        VARCHAR(255),

    email                           VARCHAR(255),
    phone                           VARCHAR(50),
    linkedin_url                    VARCHAR(512),

    employment_history              JSONB DEFAULT '[]'::jsonb,
    education                       JSONB DEFAULT '[]'::jsonb,
    skills                          TEXT[] DEFAULT '{}',

    projects                        JSONB DEFAULT '[]'::jsonb,
    publications                    JSONB DEFAULT '[]'::jsonb,
    social_profiles                 JSONB DEFAULT '{}'::jsonb,

    extraction_method               VARCHAR(50) NOT NULL,  -- deterministic | llm
    extraction_confidence           REAL,
    raw_extraction_data             JSONB DEFAULT '{}'::jsonb,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_extracted_entities_search_result ON extracted_entities(search_result_id);
CREATE INDEX IF NOT EXISTS idx_extracted_entities_name ON extracted_entities(full_name);


-- =========================================================
-- 6. candidate_identities
-- =========================================================
CREATE TABLE IF NOT EXISTS candidate_identities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES intelligence_sessions(id) ON DELETE CASCADE,

    canonical_full_name     VARCHAR(255) NOT NULL,
    canonical_company       VARCHAR(255),
    canonical_title         VARCHAR(255),
    canonical_location      VARCHAR(255),

    merged_data             JSONB DEFAULT '{}'::jsonb,

    verification_status     VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending | verified | rejected | uncertain
    human_decision          VARCHAR(50),  -- accept | reject | manual_correction
    manual_corrections      JSONB DEFAULT '{}'::jsonb,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_candidate_identities_session ON candidate_identities(session_id);
CREATE INDEX IF NOT EXISTS idx_candidate_identities_status ON candidate_identities(verification_status);
CREATE INDEX IF NOT EXISTS idx_candidate_identities_name ON candidate_identities(canonical_full_name);


-- =========================================================
-- 7. identity_scores
-- =========================================================
CREATE TABLE IF NOT EXISTS identity_scores (
    id                                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id                            UUID NOT NULL UNIQUE REFERENCES candidate_identities(id) ON DELETE CASCADE,

    overall_confidence                      DECIMAL(3,2) NOT NULL,

    name_match_score                        DECIMAL(3,2),
    company_match_score                     DECIMAL(3,2),
    title_match_score                       DECIMAL(3,2),
    location_match_score                    DECIMAL(3,2),
    employment_history_consistency_score    DECIMAL(3,2),
    cross_source_agreement_score            DECIMAL(3,2),

    scoring_details                         JSONB DEFAULT '{}'::jsonb,

    created_at                              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_identity_scores_candidate ON identity_scores(candidate_id);


-- =========================================================
-- 8. evidence
-- =========================================================
CREATE TABLE IF NOT EXISTS evidence (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id            UUID NOT NULL REFERENCES candidate_identities(id) ON DELETE CASCADE,
    extracted_entity_id     UUID NOT NULL REFERENCES extracted_entities(id) ON DELETE CASCADE,

    fact_type               VARCHAR(100) NOT NULL,  -- name | title | company | location | email | etc.
    fact_value              TEXT NOT NULL,

    source_url              VARCHAR(512) NOT NULL,
    source_snippet          TEXT,
    confidence_in_fact      DECIMAL(3,2),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_candidate ON evidence(candidate_id);
CREATE INDEX IF NOT EXISTS idx_evidence_entity ON evidence(extracted_entity_id);
CREATE INDEX IF NOT EXISTS idx_evidence_fact_type ON evidence(fact_type);


-- =========================================================
-- 9. conflicts
-- =========================================================
CREATE TABLE IF NOT EXISTS conflicts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id    UUID NOT NULL REFERENCES candidate_identities(id) ON DELETE CASCADE,

    conflict_type   VARCHAR(100) NOT NULL,  -- title | company | location | employment_gap | etc.
    field_name      VARCHAR(100) NOT NULL,

    value_a         TEXT NOT NULL,
    value_b         TEXT NOT NULL,
    source_a_url    VARCHAR(512) NOT NULL,
    source_b_url    VARCHAR(512) NOT NULL,

    resolution      VARCHAR(50),  -- manual | ignored | reconciled
    resolved_value  TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_candidate ON conflicts(candidate_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_type ON conflicts(conflict_type);


-- =========================================================
-- 10. verified_profiles
-- =========================================================
CREATE TABLE IF NOT EXISTS verified_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id            UUID NOT NULL UNIQUE REFERENCES candidate_identities(id) ON DELETE CASCADE,
    session_id              UUID NOT NULL REFERENCES intelligence_sessions(id) ON DELETE CASCADE,

    verified_facts          JSONB NOT NULL,
    labeled_inferences      JSONB DEFAULT '[]'::jsonb,
    evidence_summary        JSONB DEFAULT '[]'::jsonb,

    overall_confidence      DECIMAL(3,2) NOT NULL,
    verified_by_user_id     UUID REFERENCES users(id) ON DELETE SET NULL,

    verified_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verified_profiles_candidate ON verified_profiles(candidate_id);
CREATE INDEX IF NOT EXISTS idx_verified_profiles_session ON verified_profiles(session_id);


-- =========================================================
-- Updated Auto-Touch Triggers
-- =========================================================
CREATE TRIGGER trg_intelligence_sessions_updated_at BEFORE UPDATE ON intelligence_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_research_queries_updated_at BEFORE UPDATE ON research_queries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_identity_scores_updated_at BEFORE UPDATE ON identity_scores
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
