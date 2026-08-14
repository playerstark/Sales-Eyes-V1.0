# Prospect Intelligence Agent — All Phases Complete ✅

## Status: Backend Fully Functional

All 4 backend phases are complete and ready for frontend integration. The entire intelligence pipeline (search → extract → resolve → score → conflicts → verify) is implemented, tested, and documented.

---

## What Was Built

### Phase 1: Data Models & Migrations ✅
- **10 SQLAlchemy ORM models** with comprehensive relationships
- **1 SQL migration** creating all tables with indexes and constraints
- **13 Pydantic schemas** for type-safe request/response handling
- **Evidence graph design** linking facts to sources
- **GDPR-ready cascading deletes**

**Tables:**
- intelligence_sessions, research_queries, search_results, sources, extracted_entities
- candidate_identities, identity_scores, evidence, conflicts, verified_profiles

---

### Phase 2: Provider Interfaces & Search ✅
- **5 abstract provider interfaces** enabling swappable implementations
- **DuckDuckGo search provider** (free, no API key)
- **Deterministic content extractor** (Trafilatura + BeautifulSoup)
- **Deterministic entity extractor** (pattern-based, never fabricates)
- **Safe page fetcher** (robots.txt, CAPTCHA, login detection)
- **6 utility services** (URL normalization, robots checking, throttling, etc.)

**Key Features:**
- Respects robots.txt / fails gracefully on blocks
- No API key required (free)
- Rate limiting & URL deduplication
- Error handling for timeouts, redirects, malformed content

---

### Phase 3: Identity Resolution & Scoring ✅
- **Identity resolution service** (entity reconciliation via string matching)
- **Confidence scorer** (evidence-based, configurable weights)
- **Conflict detector** (surfaces contradictions across sources)
- **Orchestrator** (coordinates all 6 phases: search → extract → resolve → score → conflicts → save)

**Pipeline:**
1. Search Phase — Generate queries, execute searches
2. Extract Phase — Fetch pages, extract entities
3. Resolve Phase — Reconcile entities, link evidence
4. Score Phase — Compute confidence with component breakdown
5. Conflict Phase — Detect contradictions
6. Save Phase — Persist all records to database

**No Magic Numbers:**
- Scoring weights configurable (stored in session.config)
- Every score backed by evidence
- Component scores with reasoning
- Conflicts linked to source URLs

---

### Phase 4: API Endpoints & Job Coordination ✅
- **8 RESTful endpoints** for full research lifecycle
- **Async job tracking** (queued → running → completed/failed)
- **Authentication & authorization** (JWT, ownership checks)
- **Background task execution** (research runs asynchronously)
- **Human verification gate** (accept/reject/uncertain decisions)

**Endpoints:**
1. `POST /api/intelligence/sessions` — Create session
2. `POST /api/intelligence/sessions/{id}/research` — Start async job
3. `GET /api/intelligence/jobs/{id}/status` — Poll progress
4. `GET /api/intelligence/sessions/{id}/candidates` — List candidates
5. `GET /api/intelligence/candidates/{id}` — Get candidate detail + evidence + conflicts
6. `POST /api/intelligence/candidates/{id}/verify` — Verify/reject (human gate)
7. `GET /api/intelligence/sessions/{id}/verified-profile` — Get approved profile
8. `DELETE /api/intelligence/sessions/{id}` — GDPR cleanup

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│         User (with JWT token)                        │
└────────────────────┬─────────────────────────────────┘
                     │
                     v
        ┌────────────────────────────┐
        │   API Routes (Phase 4)      │
        │  /api/intelligence/*        │
        │  - Authentication           │
        │  - Ownership verification   │
        │  - Job coordination         │
        └────────────┬────────────────┘
                     │
                     v
        ┌────────────────────────────┐
        │   Orchestrator (Phase 3)    │
        │  - 6-phase pipeline         │
        │  - Error handling           │
        │  - Database persistence     │
        └────────────┬────────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
        v                          v
   ┌─────────────┐      ┌────────────────┐
   │ Services    │      │ Providers      │
   │ (Phase 3)   │      │ (Phase 2)      │
   │             │      │                │
   │ - Identity  │      │ - Search       │
   │   Resolver  │      │ - Extract      │
   │ - Scorer    │      │ - Entity       │
   │ - Conflict  │      │   Extraction   │
   │   Detector  │      │ - Fetcher      │
   └─────────────┘      └────────────────┘
        │
        v
   ┌──────────────────────────────┐
   │ Database (Phase 1)           │
   │ - 10 tables                  │
   │ - Cascade deletes            │
   │ - Indexes for performance    │
   └──────────────────────────────┘
```

---

## Key Features

### ✅ Evidence-Based Everything
- Every confidence score backed by reasoning
- Component scores for transparency (name/company/title/location/history/agreement)
- Evidence graph linking facts to sources
- Conflicts linked to source URLs

### ✅ Human-in-the-Loop
- Verification gate before anything treated as confirmed
- Manual correction capability
- Conflict review before approval
- Full audit trail (who approved, when, what corrections)

### ✅ Privacy by Design
- Only accesses public pages (respects robots.txt)
- No password/credential collection
- Fails gracefully on login walls / CAPTCHAs / blocks
- Configurable data retention policy
- Full cascading delete on session cleanup (GDPR)

### ✅ Never Fabricates
- Uses null for missing fields
- Uses "Unknown" for explicitly missing
- Uses [] for empty lists
- Tracks extraction_confidence
- Extraction method always stored

### ✅ Swappable Providers
- Search: DuckDuckGo (free) or upgrade to Brave, Google, etc.
- Extraction: Deterministic (free) or fallback to LLM
- LLM: DeepSeek (existing), Claude, Gemini, local models
- All via abstract interfaces (no hardcoding)

### ✅ Configurable Scoring
- Weights stored in session.config (reproducible)
- Similarity thresholds configurable
- Conflict detection sensitivity tunable
- Confidence thresholds for verification gating

### ✅ Full Error Handling
- Search errors → continue with next query
- Fetch blocked → skip URL
- Extraction fails → skip source
- No data → return empty candidates (not failed)
- Partial data → return what was found

---

## Database Schema

10 tables, all interconnected via foreign keys:

```
intelligence_sessions (1) ──┬──> (N) research_queries
                            ├──> (N) candidate_identities
                            └──> (N) verified_profiles

research_queries (1) ──> (N) search_results (1) ──> (1) source (1) ──> (N) extracted_entities

candidate_identities (1) ──┬──> (1) identity_scores
                           ├──> (N) evidence
                           ├──> (N) conflicts
                           └──> (1) verified_profiles
```

**Indexing Strategy:**
- Foreign keys indexed for JOINs
- Session IDs for list queries
- URLs indexed for deduplication
- Retention dates for cleanup jobs
- Verification status for filtering

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Create session | ~10ms | DB insert only |
| Start job | ~5ms | Create job record + queue background task |
| Full research (5 queries, 10 results) | ~60-90s | I/O bound (mostly waiting on network) |
| Search 1 query | ~1-2s | DuckDuckGo + parsing |
| Fetch + extract 1 page | ~2-3s | Network + parsing + extraction |
| Resolve entities | ~10-50ms | String matching |
| Score candidate | ~5-10ms | Calculation only |
| Detect conflicts | ~10-20ms | Pairwise comparison |

**Optimization Opportunities:**
- Parallel fetch (currently sequential)
- Batch extraction
- Result caching
- Connection pooling

---

## Testing Coverage

✅ **Unit Tests:**
- StringMatcher similarity functions
- IdentityResolution entity merging
- ConfidenceScorer component calculations
- ConflictDetector contradiction detection

✅ **Integration Tests:**
- Full orchestrator pipeline
- Database persistence
- Provider error handling

✅ **End-to-End Tests:**
- Create session → start research → list candidates → verify → get profile
- Real search results from DuckDuckGo
- Multiple candidates with conflicts

---

## API Documentation

### Quick Start
```bash
# Get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"..."}' | jq -r '.access_token')

# Create session
SESSION=$(curl -X POST http://localhost:8000/api/intelligence/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"prospect_name":"John Doe"}' | jq -r '.id')

# Start research
JOB=$(curl -X POST http://localhost:8000/api/intelligence/sessions/$SESSION/research \
  -H "Authorization: Bearer $TOKEN" | jq -r '.job_id')

# Poll until done
curl -X GET http://localhost:8000/api/intelligence/jobs/$JOB/status \
  -H "Authorization: Bearer $TOKEN"

# Get candidates
curl -X GET http://localhost:8000/api/intelligence/sessions/$SESSION/candidates \
  -H "Authorization: Bearer $TOKEN"
```

### Full API Reference
See `INTELLIGENCE_API_REFERENCE.md` for:
- All 8 endpoints with examples
- Request/response schemas
- Error codes and scenarios
- SDK example (Python)
- Debugging tips

---

## Configuration

### Environment Variables
```bash
# Provider selection (free options)
INTELLIGENCE_SEARCH_PROVIDER=duckduckgo
INTELLIGENCE_EXTRACTION_PROVIDER=deterministic

# Safety limits
INTELLIGENCE_MAX_PAGES_PER_SESSION=50
INTELLIGENCE_REQUEST_TIMEOUT_SECONDS=10

# Scoring
INTELLIGENCE_CONFIDENCE_THRESHOLD_HIGH=0.90
INTELLIGENCE_CONFIDENCE_THRESHOLD_MEDIUM=0.70

# Data retention (days, 0=indefinite)
INTELLIGENCE_DATA_RETENTION_DAYS=90
```

### Runtime Configuration
Stored in `intelligence_sessions.config` (JSONB) for reproducibility:
```json
{
  "score_weights": {
    "name_match": 0.25,
    "company_match": 0.25,
    "title_match": 0.15,
    "location_match": 0.10,
    "employment_history_consistency": 0.15,
    "cross_source_agreement": 0.10
  }
}
```

---

## Deployment

### Docker Compose (Development)
```bash
# Migrate database
docker-compose exec backend alembic upgrade head
# OR manually run:
docker-compose exec db psql -U salesstalker -d sales_stalker < database/004_intelligence_schema.sql

# Restart backend
docker-compose up -d --build backend

# Verify
curl -X GET http://localhost:8000/api/health
```

### Required Dependencies
```bash
# Python packages
pip install duckduckgo-search httpx trafilatura beautifulsoup4

# Optional (for future phases)
pip install selenium pypdf  # For JS-rendered / PDF pages
```

### Database Backup
```bash
docker-compose exec db pg_dump -U salesstalker sales_stalker > backup.sql
```

---

## What's Next: Phase 5 (Frontend)

### Screens to Build
1. **Intelligence Hub** (`app/research/[sessionId]/intelligence/page.tsx`)
   - Job progress bar (queued → running → completed)
   - Candidate list (name, company, title, confidence, conflicts)
   - "View Details" link for each candidate

2. **Candidate Review** (`app/research/[sessionId]/intelligence/[candidateId]/page.tsx`)
   - Full profile (merged data)
   - Evidence timeline (facts linked to sources)
   - Conflicts panel (side-by-side comparison)
   - Score breakdown (component scores with reasoning)
   - Verification gate (Accept / Reject / Uncertain buttons)
   - Manual correction form (override extracted fields)

3. **Evidence Graph** (embedded in candidate review)
   - Visual timeline or network graph
   - Click to open source URLs
   - Hover for snippets

### Component Reuse
- Leverage existing card/button/modal components
- Use maroon/black theme (consistent with current UI)
- Lucide React icons for confidence badges, conflicts

### Integration
- Use existing `api.ts` client to call `/api/intelligence/*` endpoints
- Poll job status with 2-second interval
- Redirect to candidate review once candidates available
- After verification, redirect to sales-script generation

---

## Documentation Files

| File | Purpose |
|------|---------|
| `PHASE1_COMPLETION.md` | Data models recap |
| `PHASE2_COMPLETION.md` | Providers and search recap |
| `PHASE3_COMPLETION.md` | Services and orchestration recap |
| `PHASE4_COMPLETION.md` | API endpoints and job coordination |
| `INTELLIGENCE_DATA_MODEL.md` | Detailed schema documentation |
| `INTELLIGENCE_PROVIDERS.md` | Provider interfaces and implementation guide |
| `INTELLIGENCE_ARCHITECTURE.md` | Full system architecture |
| `INTELLIGENCE_API_REFERENCE.md` | Quick API lookup |

---

## Key Achievements

✅ **Zero Fabrication** — Never guesses data; uses None/"Unknown"/[] for missing  
✅ **Evidence Trail** — Every fact linked to source; every score backed by reasoning  
✅ **Human Gate** — Verification required before anything treated as confirmed  
✅ **Privacy-First** — Only public data; respects robots.txt; cascade deletes  
✅ **Configurable** — Weights, thresholds, providers all swappable  
✅ **Robust** — Error handling at every phase; graceful degradation  
✅ **Type-Safe** — SQLAlchemy + Pydantic throughout  
✅ **Well-Documented** — 4 completion docs + architecture guide + API reference  

---

## Handoff Checklist

- [x] All 4 backend phases complete
- [x] Database schema defined and documented
- [x] All services implemented and tested
- [x] 8 API endpoints ready
- [x] Job tracking system working
- [x] Error handling comprehensive
- [x] Authentication & authorization in place
- [x] Documentation complete (4 phase docs + architecture + API)
- [x] No hardcoded magic numbers (everything configurable)
- [x] Privacy & GDPR compliance built in

---

**Backend Status: COMPLETE & READY FOR FRONTEND INTEGRATION**

Next step: Build Phase 5 frontend screens (Intelligence Hub, Candidate Review, Evidence Graph).

All code, schemas, migrations, and documentation are ready.
