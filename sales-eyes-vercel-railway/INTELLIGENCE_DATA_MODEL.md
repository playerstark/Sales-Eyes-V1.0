# Prospect Intelligence Agent — Data Model Documentation

## Overview

The Prospect Intelligence Agent extends the Sales Stalker research pipeline with identity resolution capabilities. It researches a prospect using public web sources, extracts and reconciles information across sources, detects contradictions, and requires human verification before feeding results into the sales-script generation engine.

## Table Structure

### 1. **intelligence_sessions** (entry point)
Tracks one prospect intelligence research lifecycle.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `owner_id` | UUID FK | User who initiated research |
| `research_session_id` | UUID FK | (Optional) Links to existing research_sessions for CRM integration |
| `prospect_name` | VARCHAR(255) | Initial prospect name input |
| `prospect_company` | VARCHAR(255) | Company (if known) |
| `status` | VARCHAR(50) | searching → extracting → resolving → verifying → completed \| failed |
| `progress_percent` | INTEGER | 0-100, for UI progress bar |
| `current_step` | VARCHAR(100) | Human-readable step description |
| `config` | JSONB | Snapshot of scoring weights, thresholds, provider config at research time |
| `error_message` | TEXT | Error details if status = failed |
| `created_at`, `updated_at` | TIMESTAMPTZ | Timestamps |

**Relationships:** 1:N with ResearchQuery, CandidateIdentity

---

### 2. **research_queries** (search execution)
Each search executed during the intelligence phase.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `session_id` | UUID FK | Parent intelligence_session |
| `query_text` | TEXT | The search query string |
| `search_provider` | VARCHAR(50) | duckduckgo, google, brave, etc. |
| `status` | VARCHAR(50) | pending → in_progress → completed \| failed |
| `created_at`, `updated_at` | TIMESTAMPTZ | Timestamps |

**Example queries:**
- "John Doe VP Sales TechCorp"
- "site:linkedin.com John Doe"
- "John Doe TechCorp company news"

**Relationships:** 1:N with SearchResult

---

### 3. **search_results** (raw search results)
Individual results from a search query (deduped by URL via source table).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `query_id` | UUID FK | Parent query |
| `result_index` | INTEGER | Position in result set (e.g., 0-9 for first 10 results) |
| `title` | VARCHAR(512) | Result title from search engine |
| `snippet` | TEXT | Search result snippet |
| `url` | VARCHAR(512) | Full URL (indexed for dedup lookups) |
| `created_at` | TIMESTAMPTZ | Timestamp |

**Relationships:** 1:1 with Source, 1:N with ExtractedEntity

---

### 4. **sources** (normalized page content)
One per unique URL; prevents re-fetching. Stores raw and extracted content.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `search_result_id` | UUID FK | Parent search_result |
| `url` | VARCHAR(512) | UNIQUE; deduplication key |
| `title`, `domain` | VARCHAR(512), VARCHAR(255) | Metadata |
| `content_type` | VARCHAR(100) | text/html, application/pdf, etc. |
| `raw_content` | TEXT | Full HTML/text fetched from page |
| `extracted_text` | TEXT | Cleaned text (deterministic extraction) |
| `fetch_status` | VARCHAR(50) | pending → success \| blocked \| timeout \| error |
| `fetch_error` | VARCHAR(255) | Error message if fetch failed |
| `fetched_at` | TIMESTAMPTZ | When page was fetched |
| `retention_expires_at` | TIMESTAMPTZ | When to delete raw_content (GDPR) |
| `created_at` | TIMESTAMPTZ | Timestamp |

**Retention Policy:**
- `retention_expires_at` calculated at fetch time: NOW + config.DATA_RETENTION_DAYS
- Scheduled job purges data matching `retention_expires_at < NOW()`
- Never store passwords, financial credentials, or sensitive PII

**Relationships:** 1:1 with SearchResult, 1:N with ExtractedEntity

---

### 5. **extracted_entities** (raw entity extraction)
Entities extracted from a source before identity resolution.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `search_result_id` | UUID FK | Source of extraction |
| `entity_type` | VARCHAR(50) | person \| company \| organization |
| `full_name` | VARCHAR(255) | Extracted (may be null/"Unknown" if unverified) |
| `first_name`, `last_name` | VARCHAR(100) | Split components |
| `current_title` | VARCHAR(255) | Job title |
| `current_company` | VARCHAR(255) | Company name |
| `location` | VARCHAR(255) | Geographic location |
| `email`, `phone` | VARCHAR(255), VARCHAR(50) | Contact info |
| `linkedin_url` | VARCHAR(512) | LinkedIn profile link |
| `employment_history` | JSONB | [{company, title, start_date, end_date, duration}, ...] |
| `education` | JSONB | [{school, degree, field, year}, ...] |
| `skills` | TEXT[] | Array of skill tags |
| `projects` | JSONB | [{name, description, url}, ...] |
| `publications` | JSONB | [{title, url, date}, ...] |
| `social_profiles` | JSONB | {github, twitter, etc.} |
| `extraction_method` | VARCHAR(50) | deterministic \| llm |
| `extraction_confidence` | REAL | 0.0-1.0; how confident in extraction |
| `raw_extraction_data` | JSONB | Full LLM response or parser debug info |
| `created_at` | TIMESTAMPTZ | Timestamp |

**Design Principle:** Never fabricate. Use `null` for missing, "Unknown" for explicitly missing, `[]` for empty lists.

**Relationships:** 1:N with CandidateIdentity (via Evidence), 1:1 with Source

---

### 6. **candidate_identities** (reconciled profile)
A reconciled person profile merged from multiple extracted entities.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `session_id` | UUID FK | Parent intelligence_session |
| `canonical_full_name` | VARCHAR(255) | Best-guess name across sources |
| `canonical_company` | VARCHAR(255) | Best-guess company |
| `canonical_title` | VARCHAR(255) | Best-guess title |
| `canonical_location` | VARCHAR(255) | Best-guess location |
| `merged_data` | JSONB | Full merged profile (all fields) |
| `verification_status` | VARCHAR(50) | pending → verified \| rejected \| uncertain |
| `human_decision` | VARCHAR(50) | accept \| reject \| manual_correction |
| `manual_corrections` | JSONB | Overrides to merged_data by human |
| `created_at`, `verified_at` | TIMESTAMPTZ | Timestamps |

**Workflow:**
1. Created during identity resolution phase
2. Identity score computed (separate table)
3. Conflicts detected and surfaced (separate table)
4. User reviews candidate + sources (frontend)
5. User clicks accept/reject → human_decision set, verification_status updated
6. If verified → VerifiedProfile created with final approved data

**Relationships:** 1:1 with IdentityScore, 1:N with Conflict, 1:N with Evidence, 1:1 with VerifiedProfile

---

### 7. **identity_scores** (confidence breakdown)
Evidence-based confidence scoring with full transparency.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `candidate_id` | UUID FK | Unique per candidate |
| `overall_confidence` | DECIMAL(3,2) | 0.00-1.00 |
| `name_match_score` | DECIMAL(3,2) | How much extracted names agree |
| `company_match_score` | DECIMAL(3,2) | How much extracted companies agree |
| `title_match_score` | DECIMAL(3,2) | How much extracted titles agree |
| `location_match_score` | DECIMAL(3,2) | How much extracted locations agree |
| `employment_history_consistency_score` | DECIMAL(3,2) | Timeline consistency across sources |
| `cross_source_agreement_score` | DECIMAL(3,2) | Overall agreement metric |
| `scoring_details` | JSONB | `{name_match: {method, evidence, value}, ...}` |
| `created_at`, `updated_at` | TIMESTAMPTZ | Timestamps |

**No Magic Numbers:**
- All weights are configurable via `intelligence_sessions.config`
- Scoring details include evidence (e.g., "2/3 sources say 'VP'; 1/3 says 'Director'")
- Frontend displays each component score for transparency

**Relationships:** 1:1 with CandidateIdentity

---

### 8. **evidence** (fact-source linkage)
Links each fact to its source (evidence graph edges).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `candidate_id` | UUID FK | Which candidate this fact supports |
| `extracted_entity_id` | UUID FK | Which source/extraction |
| `fact_type` | VARCHAR(100) | name \| title \| company \| location \| email \| etc. |
| `fact_value` | TEXT | The actual extracted value |
| `source_url` | VARCHAR(512) | Full source URL (for user to verify) |
| `source_snippet` | TEXT | Quote/context from page |
| `confidence_in_fact` | DECIMAL(3,2) | 0.00-1.00 confidence in this specific fact |
| `created_at` | TIMESTAMPTZ | Timestamp |

**Usage:**
- Frontend queries: "Show me all evidence for 'current_company'"
- User clicks evidence → opens source URL + highlights snippet
- Builds trust in AI output by showing reasoning

**Relationships:** N:N junction between CandidateIdentity and ExtractedEntity

---

### 9. **conflicts** (contradictions)
Detected contradictions between sources.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `candidate_id` | UUID FK | Which candidate has conflict |
| `conflict_type` | VARCHAR(100) | title \| company \| location \| employment_gap \| etc. |
| `field_name` | VARCHAR(100) | The field name (e.g., "current_title") |
| `value_a`, `value_b` | TEXT | The two conflicting values |
| `source_a_url`, `source_b_url` | VARCHAR(512) | Where each value came from |
| `resolution` | VARCHAR(50) | manual \| ignored \| reconciled |
| `resolved_value` | TEXT | What human/system chose |
| `created_at` | TIMESTAMPTZ | Timestamp |

**Example:**
- `conflict_type="title"`, `value_a="VP Sales"`, `value_b="Director, Sales"`
- `source_a_url="linkedin.com/in/john..."`, `source_b_url="company-website.com/team"`

**Frontend UX:**
- Conflict badge on candidate card
- Expanded view shows side-by-side values with source links
- Manual resolution UI: pick A, pick B, or enter custom value

**Relationships:** 1:N with CandidateIdentity

---

### 10. **verified_profiles** (final approved intelligence)
Human-approved final intelligence profile, ready for sales-script generation.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `candidate_id` | UUID FK | Unique per candidate |
| `session_id` | UUID FK | Parent intelligence_session |
| `verified_facts` | JSONB | {full_name, company, title, location, contact_info, ...} |
| `labeled_inferences` | JSONB | [{inference, confidence, reasoning}, ...] |
| `evidence_summary` | JSONB | [{fact, sources[], confidence}, ...] |
| `overall_confidence` | DECIMAL(3,2) | Final confidence 0.00-1.00 |
| `verified_by_user_id` | UUID FK | User who approved |
| `verified_at`, `created_at` | TIMESTAMPTZ | Timestamps |

**Structure Example:**
```json
{
  "verified_facts": {
    "full_name": "John Doe",
    "current_company": "TechCorp Inc.",
    "current_title": "VP Sales",
    "location": "San Francisco, CA",
    "email": "john.doe@techcorp.com"
  },
  "labeled_inferences": [
    {
      "inference": "Likely responsible for sales strategy and team management",
      "confidence": 0.85,
      "reasoning": "VP title + LinkedIn management experience + company size"
    }
  ],
  "evidence_summary": [
    {
      "fact": "current_title = VP Sales",
      "sources": ["linkedin.com/in/johndoe", "techcorp.com/team"],
      "confidence": 0.95
    }
  ]
}
```

**Handoff to Sales Script Engine:**
- Script generation should only use `verified_facts` as ground truth
- Can reference `labeled_inferences` but must label them as such
- Must cite evidence for transparency

**Relationships:** 1:1 with CandidateIdentity, N:1 with IntelligenceSession

---

## Data Flow

```
1. User initiates research
   ↓
2. IntelligenceSession created
   ↓
3. Search Phase: ResearchQuery → SearchResult → Source (content fetching)
   ↓
4. Extraction Phase: ExtractedEntity extracted from Source
   ↓
5. Resolution Phase: CandidateIdentity merged from ExtractedEntities
                    Evidence links facts to sources
                    Conflict detects contradictions
                    IdentityScore computed
   ↓
6. Verification Phase (human gate): User reviews candidate
   ↓
7. If approved: VerifiedProfile created
   ↓
8. Handoff: Pass VerifiedProfile to sales-script generation engine
```

---

## Indexes & Query Patterns

### Hot Paths
```sql
-- List candidates for a session
SELECT * FROM candidate_identities 
WHERE session_id = $1 
ORDER BY created_at DESC;

-- Get candidate with all evidence & conflicts
SELECT * FROM candidate_identities c
LEFT JOIN evidence e ON c.id = e.candidate_id
LEFT JOIN conflicts co ON c.id = co.candidate_id
LEFT JOIN identity_scores ics ON c.id = ics.candidate_id
WHERE c.id = $1;

-- Check if URL already fetched (dedup)
SELECT id FROM sources WHERE url = $1;

-- Find overdue retention records
SELECT id FROM sources 
WHERE retention_expires_at < NOW() AND retention_expires_at IS NOT NULL;

-- Session progress
SELECT 
  COUNT(DISTINCT rq.id) as queries_count,
  COUNT(DISTINCT ci.id) as candidates_count,
  COUNT(DISTINCT vp.id) as verified_count
FROM intelligence_sessions s
LEFT JOIN research_queries rq ON s.id = rq.session_id
LEFT JOIN candidate_identities ci ON s.id = ci.session_id
LEFT JOIN verified_profiles vp ON s.id = vp.session_id
WHERE s.id = $1;
```

---

## Cascading Deletes

When `intelligence_sessions` is deleted:
- All `research_queries` → `search_results` → `sources` → `extracted_entities` deleted
- All `candidate_identities` → `identity_scores`, `evidence`, `conflicts`, `verified_profiles` deleted
- **User data fully expunged** (privacy by design)

---

## Future Extensions

### (Day 4+) Company Intelligence Agent
- `companies` table already exists; extend with `intelligence_data` JSONB
- Similar pattern: IntelligenceSession → Candidate → VerifiedProfile

### (Day 5+) CRM Integration
- `verified_profiles.prospect_id` FK to `prospects` table
- Link final intelligence to CRM contact
- Track which profiles fed into which sales scripts

### (Day 6+) Real-time Streaming
- WebSocket progress updates: status, progress_percent, current_step
- Stream findings as they're discovered (not batch at end)

---

## Notes for Phase 2

- **Provider interfaces** (in `services/intelligence/interfaces.py`): Define contracts for SearchProvider, PageFetcher, ContentExtractor, LLMProvider
- **Deterministic extraction**: BeautifulSoup + Trafilatura (no API key needed)
- **Free search**: DuckDuckGo (via `duckduckgo-search` Python package)
- **Config management**: Load score weights and thresholds from `intelligence_sessions.config` (snapshot at research time)
