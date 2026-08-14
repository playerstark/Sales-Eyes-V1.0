# Phase 3: Identity Resolution & Scoring — COMPLETE ✅

## Summary

Successfully implemented the core intelligence reasoning services:
- Identity resolution (entity reconciliation with string matching)
- Evidence-based confidence scoring (configurable weights, no magic numbers)
- Conflict detection (surface contradictions across sources)
- Orchestrator (coordinates entire research pipeline)

---

## Files Created

### 1. **Identity Resolver Service**

**File:** `backend/app/services/intelligence/identity_resolver.py` (280 lines)

**Classes:**

#### `StringMatcher`
Static string similarity methods:
- `levenshtein_similarity()` — Levenshtein distance (0.0–1.0)
- `fuzzy_match()` — Fuzzy matching for typos/abbreviations
- `should_match()` — Binary match decision with threshold

**Usage:**
```python
matcher = StringMatcher()
similarity = matcher.levenshtein_similarity("John Smith", "Jon Smith")  # 0.85+
if matcher.should_match("VP Sales", "Vice President Sales", threshold=0.8):
    # Same person likely
```

#### `IdentityResolution`
Reconcile multiple extracted entities into candidate identities.

```python
resolver = IdentityResolution(name_threshold=0.85, company_threshold=0.80)
candidates = await resolver.resolve_entities(extracted_entities, session_id)
```

**Algorithm:**
1. Compare each entity pair for name/company match
2. Group matching entities together
3. Merge each group into single candidate profile
4. Prefer non-None values (best-effort merge)

**Merging Strategy:**
- Take non-None values from all entities
- Merge lists (skills, employment history, education)
- Remove duplicates
- Track source_count and source_entities

#### `IdentityMatcher`
Link facts to source evidence (evidence graph construction).

```python
matcher = IdentityMatcher()
evidence = await matcher.link_evidence(candidate, extracted_entities, sources)
# Returns [{fact_type, fact_value, source_urls, confidence}, ...]
```

**Output:**
- Links each fact (name, title, company, etc.) to its sources
- Computes per-fact confidence (average across matching sources)
- Deduplicates source URLs

---

### 2. **Confidence Scorer**

**File:** `backend/app/services/intelligence/confidence_scorer.py` (310 lines)

**Class:** `ConfidenceScorer`

**Features:**
✅ Configurable weights (no hardcoded magic numbers)  
✅ Component scores (name, company, title, location, history, cross-source agreement)  
✅ Evidence-based reasoning (explains each score)  
✅ Weighted overall confidence  

**Default Weights:**
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

**Usage:**
```python
scorer = ConfidenceScorer(weights=custom_weights)
score_result = await scorer.score_candidate(candidate, extracted_entities, evidence)

# Returns:
{
    "overall_confidence": 0.85,
    "component_scores": {
        "name_match": 0.95,
        "company_match": 0.80,
        ...
    },
    "scoring_details": {
        "name_match": {
            "score": 0.95,
            "evidence": "3/3 sources agree on 'John Doe'"
        },
        ...
    },
    "weights": {...}
}
```

**Scoring Methods:**
- `_score_name_match()` — Agreement ratio across sources
- `_score_company_match()` — Agreement ratio with exact match
- `_score_title_match()` — Fuzzy matching for title variations
- `_score_location_match()` — Agreement ratio
- `_score_employment_history()` — Timeline consistency
- `_score_cross_source_agreement()` — Average evidence confidence

**Key Principle:** Every score has reasoning. Never a mystery number.

---

### 3. **Conflict Detector**

**File:** `backend/app/services/intelligence/conflict_detector.py` (210 lines)

**Class:** `ConflictDetector`

Detects contradictions across sources.

```python
detector = ConflictDetector(similarity_threshold=0.85)
conflicts = await detector.detect_conflicts(candidate, extracted_entities, evidence)
```

**Returns:**
```python
[
    {
        "conflict_type": "company_change",
        "field_name": "company",
        "value_a": "TechCorp",
        "value_b": "InnovateCo",
        "source_a_url": "https://linkedin.com/...",
        "source_b_url": "https://company-site.com/...",
        "severity": "high",
        "resolution": None,
        "detected_at": "2026-08-11T..."
    },
    ...
]
```

**Conflict Types:**
- `name_mismatch` — Different full names (high severity)
- `company_change` — Different companies (high severity)
- `title_change` — Different titles (medium)
- `location_change` — Different locations (medium)

**Severity Levels:**
- `high` — Name or company (identity-critical)
- `medium` — Title or location (important but recoverable)

**Algorithm:**
1. Extract all values for each field
2. Compare each pair for similarity (using 0.85 threshold)
3. Exact/similar matches = no conflict
4. Different values = conflict record
5. Link each conflict to source URLs

#### `ConflictResolver`
Utilities for resolving conflicts.

```python
resolver = ConflictResolver()

# Get suggestion
preferred = resolver.suggest_resolution(conflict)  # Heuristic: longer = more complete

# Mark resolved
resolver.mark_resolved(conflict, "custom", "VP of Sales")
```

---

### 4. **Orchestrator Service**

**File:** `backend/app/services/intelligence/orchestrator.py` (440 lines)

**Class:** `IntelligenceOrchestrator`

Main coordinator for entire research pipeline.

```python
orchestrator = IntelligenceOrchestrator(
    db=session,
    search_provider=DuckDuckGoSearchProvider(),
    content_extractor=DeterministicExtractor(),
    entity_extractor=DeterministicEntityExtractor(),
    page_fetcher=SafePageFetcher(search_provider)
)

result = await orchestrator.research(
    session_id=uuid.uuid4(),
    prospect_name="John Doe",
    prospect_company="TechCorp",
    max_queries=5,
    max_pages_per_query=10
)
```

**Pipeline Phases:**

1. **Search Phase** (`_search_phase()`)
   - Generate search queries (name, name+company, LinkedIn variants)
   - Execute searches
   - Save queries and results to DB
   - Track status and errors

2. **Extract Phase** (`_extract_phase()`)
   - Fetch pages (with safety checks)
   - Extract readable text (Trafilatura/BeautifulSoup)
   - Extract person entities
   - Save sources and extracted data to DB

3. **Resolve Phase** (`_resolve_phase()`)
   - Reconcile entities into candidates
   - Link evidence (facts to sources)

4. **Score Phase** (`_score_phase()`)
   - Compute confidence for each candidate
   - Store component scores and reasoning

5. **Conflict Phase** (`_conflict_phase()`)
   - Detect contradictions
   - Store conflict records

6. **Save Phase** (`_save_candidates()`)
   - Persist all candidates to DB
   - Create IdentityScore, Conflict, Evidence records

**Status Tracking:**
- `searching` (10%)
- `extracting` (30%)
- `resolving` (50%)
- `scoring` (70%)
- `detecting_conflicts` (90%)
- `completed` (100%)

**Error Handling:**
- Try/except around each search and extraction
- Continue on individual failures
- Log all errors
- Set status to `failed` on critical errors

**Query Generation:**
```python
_generate_queries("John Doe", "TechCorp", count=5)
# Returns:
# - "John Doe"
# - '"John Doe"'
# - "John Doe site:linkedin.com"
# - "John Doe TechCorp"
# - "John Doe TechCorp site:linkedin.com"
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Prospect Input                             │
│              (name, company, optionally more)                │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      v
        ┌─────────────────────────────┐
        │   PHASE 1: SEARCH           │
        │  (generate queries, execute)│
        └──────────┬──────────────────┘
                   │
        SearchResult[], SearchQuery saved to DB
                   │
                   v
        ┌─────────────────────────────┐
        │  PHASE 2: EXTRACT           │
        │ (fetch pages, extract text) │
        └──────────┬──────────────────┘
                   │
        ExtractedEntity[], Source records saved to DB
                   │
                   v
        ┌─────────────────────────────────┐
        │   PHASE 3: RESOLVE              │
        │  (reconcile entities, link       │
        │   evidence graph)                │
        └──────────┬──────────────────────┘
                   │
        Candidate[] with Evidence[] records
                   │
                   v
        ┌─────────────────────────────────┐
        │   PHASE 4: SCORE                │
        │  (confidence scoring,            │
        │   component scores)              │
        └──────────┬──────────────────────┘
                   │
        Candidate[] with IdentityScore records
                   │
                   v
        ┌─────────────────────────────────┐
        │   PHASE 5: DETECT CONFLICTS     │
        │  (surface contradictions)       │
        └──────────┬──────────────────────┘
                   │
        Candidate[] with Conflict[] records
                   │
                   v
        ┌─────────────────────────────────┐
        │   PHASE 6: SAVE TO DB           │
        │  (persist all records)          │
        └──────────┬──────────────────────┘
                   │
                   v
        CandidateIdentity[], IdentityScore[], Conflict[]
        ready for human verification
```

---

## Architecture Benefits

✅ **Separation of Concerns** — Each service has single responsibility  
✅ **Testability** — Each service can be tested independently  
✅ **Extensibility** — Easy to add new scoring components or conflict types  
✅ **Configurability** — Weights, thresholds all configurable  
✅ **Transparency** — Every decision backed by evidence  
✅ **Robustness** — Error handling at each phase  

---

## Testing Checklist

- [ ] StringMatcher calculates similarity correctly
- [ ] IdentityResolution merges similar entities
- [ ] Merged profile has all non-None values
- [ ] ConfidenceScorer returns 0.0-1.0 scores
- [ ] Scores backed by evidence explanation
- [ ] ConflictDetector identifies value mismatches
- [ ] Conflicts include source URLs
- [ ] Orchestrator executes all 6 phases
- [ ] Status updates correctly through pipeline
- [ ] CandidateIdentity records saved to DB
- [ ] IdentityScore records linked correctly
- [ ] Conflict records created for mismatches
- [ ] Evidence records link facts to sources

---

## Ready for Phase 4

### What Phase 3 Provides
- ✅ Entity reconciliation (string matching)
- ✅ Evidence graph (fact-to-source links)
- ✅ Confidence scoring (evidence-based, configurable)
- ✅ Conflict detection (contradiction surfacing)
- ✅ Full orchestration (search → extraction → resolution → scoring → conflicts)
- ✅ Database persistence (all records saved)

### What Phase 4 Will Add
- API endpoints for starting research jobs
- Async job tracking (webhook/polling/WebSocket)
- Candidate listing endpoint
- Candidate detail endpoint (with all evidence)
- Verification/approval endpoint
- Final profile handoff to sales-script engine

---

**Status:** Phase 3 ✅ Complete. Ready for Phase 4: API Endpoints & Job Coordination.
