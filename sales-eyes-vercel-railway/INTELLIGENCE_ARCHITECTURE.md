# Prospect Intelligence Agent — Complete Architecture Overview

## System Components

```
┌────────────────────────────────────────────────────────────────────┐
│                         API Layer (Phase 4)                        │
│  /api/intelligence/sessions → /api/intelligence/candidates         │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
┌─────────────────────────────┴──────────────────────────────────────┐
│                    Orchestrator (Phase 3)                          │
│  Coordinates: Search → Extract → Resolve → Score → Conflict       │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        v                     v                     v
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │ Search   │         │ Extract  │         │ Resolve  │
    │ & Fetch  │         │ & Parse  │         │ & Score  │
    └──────────┘         └──────────┘         └──────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        v                     v                     v
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │Providers │         │Services  │         │Utils     │
    │(Phase 2) │         │(Phase 3) │         │(Phase 2) │
    └──────────┘         └──────────┘         └──────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
┌─────────────────────────────┴──────────────────────────────────────┐
│            Database (Models from Phase 1)                          │
│  IntelligenceSession → CandidateIdentity → IdentityScore          │
│  SearchResult → Source → ExtractedEntity                          │
│  Evidence ↔ Conflict → VerifiedProfile                            │
└────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Providers (Phase 2)

### SearchProvider Interface
- Implementation: `DuckDuckGoSearchProvider`
- Responsibilities: Web search, page fetching
- Safety: Respects robots.txt, detects CAPTCHA/login

### ContentExtractor Interface
- Implementation: `DeterministicExtractor` (Trafilatura + BeautifulSoup)
- Responsibilities: HTML → readable text
- Handles: Boilerplate removal, fallbacks

### EntityExtractor Interface
- Implementation: `DeterministicEntityExtractor`
- Responsibilities: Text → structured entities
- Principle: Never fabricate data

### PageFetcher Interface
- Implementation: `SafePageFetcher`
- Responsibilities: Search + safety checks combined
- Includes: robots.txt check, throttling, timeout

### Utilities
- `URLNormalizer` — Deduplication
- `RobotsChecker` — Access control
- `CaptchaDetector` — CAPTCHA heuristics
- `LoginDetector` — Login wall heuristics
- `ThrottleManager` — Rate limiting

---

## Layer 2: Services (Phase 3)

### IdentityResolution
**Purpose:** Reconcile multiple extracted entities into candidate profiles

**Key Methods:**
- `resolve_entities()` — Group & merge entities
- `_entities_match()` — String similarity matching
- `_merge_entities()` — Best-effort data merging

**Output:** Candidate profiles with merged data

### IdentityMatcher
**Purpose:** Build evidence graph (fact-to-source links)

**Key Methods:**
- `link_evidence()` — Connect each fact to its sources
- Confidence: Per-fact average across matching sources

### ConfidenceScorer
**Purpose:** Evidence-based scoring with configurable weights

**Key Methods:**
- `score_candidate()` — Compute overall + component scores
- `_score_name_match()` — Agreement ratio
- `_score_company_match()` — Agreement ratio
- `_score_title_match()` — Fuzzy matching
- `_score_location_match()` — Agreement ratio
- `_score_employment_history()` — Timeline consistency
- `_score_cross_source_agreement()` — Average evidence

**Weights (Configurable):**
```python
{
    "name_match": 0.25,
    "company_match": 0.25,
    "title_match": 0.15,
    "location_match": 0.10,
    "employment_history_consistency": 0.15,
    "cross_source_agreement": 0.10
}
```

### ConflictDetector
**Purpose:** Surface contradictions across sources

**Key Methods:**
- `detect_conflicts()` — Find all mismatches
- `_find_conflicts_in_field()` — Per-field comparison
- `_classify_conflict_type()` — Type classification
- `_calculate_severity()` — high | medium | low

**Types:**
- `name_mismatch` (high)
- `company_change` (high)
- `title_change` (medium)
- `location_change` (medium)

### ConflictResolver
**Purpose:** Utilities for resolving conflicts

**Key Methods:**
- `suggest_resolution()` — Heuristic preference
- `mark_resolved()` — Record user choice

### Orchestrator
**Purpose:** Coordinate entire research pipeline

**Pipeline:**
1. **Search Phase** — Generate queries, execute searches, save results
2. **Extract Phase** — Fetch pages, extract text, extract entities
3. **Resolve Phase** — Reconcile entities, link evidence
4. **Score Phase** — Compute confidence scores
5. **Conflict Phase** — Detect contradictions
6. **Save Phase** — Persist all records to DB

**Status Tracking:**
- searching (10%), extracting (30%), resolving (50%), scoring (70%), detecting_conflicts (90%), completed (100%)

**Error Handling:**
- Try/except around fetch and extract operations
- Graceful continuation on individual failures
- Log all errors, set status to failed on critical errors

---

## Layer 3: Data Models (Phase 1)

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|---|
| `intelligence_sessions` | Research lifecycle | status, progress_percent, current_step, config |
| `research_queries` | Search executions | query_text, search_provider, status |
| `search_results` | Raw results | result_index, title, snippet, url |
| `sources` | Fetched pages | url, raw_content, extracted_text, fetch_status |
| `extracted_entities` | Extracted data | full_name, title, company, email, phone, skills, etc. |
| `candidate_identities` | Merged profiles | canonical_full_name, merged_data, verification_status |
| `identity_scores` | Confidence | overall_confidence, component scores, reasoning |
| `evidence` | Fact-source links | fact_type, fact_value, source_url, confidence |
| `conflicts` | Contradictions | conflict_type, value_a, value_b, source_a_url, source_b_url |
| `verified_profiles` | Human-approved | verified_facts, labeled_inferences, evidence_summary |

### Relationships

```
IntelligenceSession (1) ──> (N) ResearchQuery
                        ├──> (N) CandidateIdentity
                        └──> (N) VerifiedProfile

ResearchQuery (1) ──> (N) SearchResult (1) ──> (1) Source (1) ──> (N) ExtractedEntity

CandidateIdentity (1) ──> (1) IdentityScore
                      ├──> (N) Evidence
                      ├──> (N) Conflict
                      └──> (1) VerifiedProfile
```

---

## Data Flow Example

```
User Input: "Research John Doe at TechCorp"
    │
    v
Create IntelligenceSession (status: planning)
    │
    v
SEARCH PHASE (Orchestrator._search_phase)
    ├─ Generate: ["John Doe", "John Doe site:linkedin.com", "John Doe TechCorp"]
    ├─ Execute: DuckDuckGoSearchProvider.search()
    └─ Save: SearchQuery, SearchResult records
    │
    v
EXTRACT PHASE (Orchestrator._extract_phase)
    ├─ For each URL:
    │  ├─ SafePageFetcher.fetch_safe(url)
    │  ├─ DeterministicExtractor.extract(raw_content)
    │  └─ DeterministicEntityExtractor.extract_person(text)
    ├─ Save: Source, ExtractedEntity records
    └─ Return: [ExtractedEntity{full_name: "John Doe", title: "VP Sales", ...}, ...]
    │
    v
RESOLVE PHASE (Orchestrator._resolve_phase)
    ├─ IdentityResolution.resolve_entities()
    │  └─ Group similar entities, merge into candidates
    ├─ IdentityMatcher.link_evidence()
    │  └─ Link each fact to its sources
    └─ Return: [Candidate{full_name: "John Doe", evidence: [...], ...}, ...]
    │
    v
SCORE PHASE (Orchestrator._score_phase)
    ├─ ConfidenceScorer.score_candidate()
    │  ├─ name_match: 0.95 (3/3 sources agree)
    │  ├─ company_match: 0.80 (1/2 sources say TechCorp)
    │  ├─ title_match: 0.90 (fuzzy: "VP Sales" ≈ "Vice President, Sales")
    │  ├─ location_match: 0.70 (1/2 sources agree)
    │  ├─ employment_history_consistency: 0.80 (timeline OK)
    │  └─ overall_confidence: 0.85 (weighted average)
    └─ Return: [Candidate with scores and reasoning, ...]
    │
    v
CONFLICT PHASE (Orchestrator._conflict_phase)
    ├─ ConflictDetector.detect_conflicts()
    │  └─ Find mismatches: "John Doe" vs "Jon Smith"? (no) | "VP" vs "Director"? (yes)
    └─ Return: [Candidate with conflicts [], ...]
    │
    v
SAVE PHASE (Orchestrator._save_candidates)
    ├─ Create CandidateIdentity record
    ├─ Create IdentityScore record (linked to candidate)
    ├─ Create Conflict records (if any)
    └─ Save Evidence records (fact-to-source links)
    │
    v
Human Verification (Phase 4/5)
    ├─ User reviews candidate in UI
    ├─ Views confidence scores & evidence
    ├─ Reviews conflicts (if any)
    ├─ Makes decision: accept/reject/manual_correction
    └─ Creates VerifiedProfile record
    │
    v
Sales Script Generation
    ├─ Sales engine reads VerifiedProfile
    ├─ Uses verified_facts as ground truth
    ├─ Labels any labeled_inferences as such
    └─ Generates personalized sales script
```

---

## Configuration

### Environment Variables
```bash
# Provider selection
INTELLIGENCE_SEARCH_PROVIDER=duckduckgo  # Free option
INTELLIGENCE_EXTRACTION_PROVIDER=deterministic

# Throttling
INTELLIGENCE_MAX_PAGES_PER_SESSION=50
INTELLIGENCE_REQUEST_TIMEOUT_SECONDS=10
INTELLIGENCE_THROTTLE_DELAY_SECONDS=0.5

# Confidence thresholds
INTELLIGENCE_CONFIDENCE_THRESHOLD_HIGH=0.90
INTELLIGENCE_CONFIDENCE_THRESHOLD_MEDIUM=0.70

# Scoring weights (JSON)
INTELLIGENCE_SCORE_WEIGHTS={
  "name_match": 0.25,
  "company_match": 0.25,
  ...
}

# Data retention
INTELLIGENCE_DATA_RETENTION_DAYS=90
```

### Runtime Configuration
Stored in `intelligence_sessions.config` (JSONB) at research time for reproducibility.

---

## Privacy & Safety Guardrails

✅ **Only Public Data**
- No password collection
- No bypassing login walls
- No solving CAPTCHAs
- No credentials storage

✅ **Respect robots.txt**
- Check before every fetch
- Fail gracefully if blocked

✅ **Detect Access Blocks**
- Raise `RobotsBlockedError` if 403/robots.txt blocks
- Raise `LoginRequiredError` if login page detected
- Raise `CaptchaDetectedError` if CAPTCHA detected
- Never attempt to bypass

✅ **Data Retention**
- Retention dates on all raw_content
- Automatic cleanup job deletes expired data
- Full cascade delete on session cleanup

✅ **Never Fabricate**
- Use `None` for missing fields
- Use "Unknown" for explicitly missing
- Track extraction_confidence
- Extraction method always stored

---

## Extensibility Points

### Add a New Search Provider
```python
# Implement SearchProvider interface
class BraveSearchProvider(SearchProvider):
    async def search(query, limit) -> SearchResult[]
    async def get_page_content(url) -> PageContent
```

### Add a New Extractor
```python
# Implement EntityExtractor interface
class LLMEntityExtractor(EntityExtractor):
    async def extract_person(text, context_url) -> ExtractedEntity
    async def extract_company(text, context_url) -> ExtractedEntity
```

### Add a New Scoring Component
```python
# In ConfidenceScorer
def _score_new_component(self, candidate, entities) -> dict:
    return {"score": 0.8, "evidence": "..."}

# Update weights
self.weights["new_component"] = 0.05
```

### Add a New Conflict Type
```python
# In ConflictDetector
if field == "new_field":
    return "new_field_conflict"
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Search 1 query | ~1s | DuckDuckGo rate limited |
| Fetch + extract 1 page | ~2-3s | Includes robots.txt check + throttle |
| Resolve 10 entities | ~10ms | String matching in Python |
| Score 1 candidate | ~5ms | Calculation only |
| Detect conflicts 1 candidate | ~10ms | Pairwise comparison |
| Full pipeline (5 queries, 10 results) | ~60-90s | Mostly I/O bound |

**Optimization Opportunities:**
- Parallel fetch/extract (currently sequential)
- Cache common extracted entities
- Batch conflict detection

---

## Testing Strategy

### Unit Tests
- `StringMatcher` — Similarity functions
- `IdentityResolution` — Entity merging
- `ConfidenceScorer` — Score calculation
- `ConflictDetector` — Conflict identification

### Integration Tests
- Full orchestrator pipeline
- Search → extract → resolve → score → conflicts
- Database persistence

### End-to-End Tests
- Real search (DuckDuckGo) → extract → score → verify
- Mock human decisions → sales script generation

---

**Architecture Complete.** All three phases (data models, providers, reasoning services) are now in place. Ready for Phase 4: API endpoints and human verification UI.
