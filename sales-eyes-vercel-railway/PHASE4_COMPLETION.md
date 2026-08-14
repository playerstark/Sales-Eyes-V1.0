# Phase 4: API Endpoints & Job Coordination — COMPLETE ✅

## Summary

Successfully created RESTful API endpoints for prospect intelligence research with async job coordination and human verification gating. All endpoints require authentication and enforce ownership checks.

---

## Files Created

### 1. **Job Tracker Service** (`job_tracker.py`)

**Class:** `JobTracker`

Simple in-memory job tracking for async operations. (For production, would use Celery, RQ, or similar.)

**Job Status Values:**
- `queued` — Waiting to run
- `running` — Currently executing
- `completed` — Finished successfully
- `failed` — Encountered error
- `cancelled` — User cancelled

**Key Methods:**

```python
job_id = tracker.create_job(session_id)
# Returns: UUID string

job = tracker.get_job(job_id)
# Returns: {job_id, session_id, status, progress_percent, current_step, message, error, ...}

tracker.update_job(job_id, status="running", progress_percent=30, current_step="Extracting")
tracker.mark_running(job_id, "Starting extraction")
tracker.mark_completed(job_id, "Found 3 candidates")
tracker.mark_failed(job_id, "Search provider error")
```

**Global Accessor:**
```python
tracker = get_job_tracker()  # Get singleton instance
```

---

### 2. **Intelligence Routes** (`routes/intelligence.py`)

**Endpoints:**

#### 1. Create Session
```
POST /api/intelligence/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "prospect_name": "John Doe",
  "prospect_company": "TechCorp"
}

Response 201:
{
  "id": "uuid",
  "prospect_name": "John Doe",
  "prospect_company": "TechCorp",
  "status": "created",
  "progress_percent": 0,
  "current_step": null,
  "created_at": "2026-08-11T...",
  "updated_at": "2026-08-11T..."
}
```

**Purpose:** Create empty research session (no research runs yet)

---

#### 2. Start Research Job (Async)
```
POST /api/intelligence/sessions/{session_id}/research
Authorization: Bearer <token>

Response 200:
{
  "session_id": "uuid",
  "job_id": "uuid",
  "status": "queued"
}
```

**Purpose:** Queue async research job, return job ID for polling

**Flow:**
1. Creates background task
2. Returns job ID immediately
3. Client polls job status with returned job_id
4. Task runs orchestrator pipeline (search → extract → resolve → score → conflicts)
5. Results saved to database

---

#### 3. Poll Job Status
```
GET /api/intelligence/jobs/{job_id}
Authorization: Bearer <token>

Response 200:
{
  "job_id": "uuid",
  "status": "running",
  "progress_percent": 45,
  "current_step": "Extracting information from pages",
  "message": null,
  "error": null
}
```

**Purpose:** Check job progress (polling mechanism)

**Status Values:**
- `queued` → 0%
- `running` → 10-90% (updates during phases)
- `completed` → 100%
- `failed` → 0% (with error message)

---

#### 4. List Candidates
```
GET /api/intelligence/sessions/{session_id}/candidates
Authorization: Bearer <token>

Response 200:
{
  "session_id": "uuid",
  "total_candidates": 2,
  "candidates": [
    {
      "id": "uuid",
      "canonical_full_name": "John Doe",
      "canonical_company": "TechCorp",
      "canonical_title": "VP Sales",
      "verification_status": "pending",
      "confidence": 0.85,
      "conflict_count": 1
    },
    ...
  ]
}
```

**Purpose:** List all candidates from a research session

**Filters:**
- By session (required)
- By verification_status (future enhancement)
- By confidence threshold (future enhancement)

---

#### 5. Get Candidate Detail
```
GET /api/intelligence/candidates/{candidate_id}
Authorization: Bearer <token>

Response 200:
{
  "id": "uuid",
  "canonical_full_name": "John Doe",
  "canonical_company": "TechCorp",
  "canonical_title": "VP Sales",
  "canonical_location": "San Francisco, CA",
  "merged_data": {...},
  "verification_status": "pending",
  "confidence": 0.85,
  "score_details": {
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
    }
  },
  "evidence": [
    {
      "id": "uuid",
      "fact_type": "title",
      "fact_value": "VP Sales",
      "source_url": "https://linkedin.com/in/johndoe",
      "source_snippet": "John Doe, VP Sales at TechCorp",
      "confidence": 0.95
    },
    ...
  ],
  "conflicts": [
    {
      "id": "uuid",
      "conflict_type": "title_change",
      "field_name": "title",
      "value_a": "VP Sales",
      "value_b": "Director, Sales",
      "source_a_url": "https://linkedin.com/...",
      "source_b_url": "https://techcorp.com/...",
      "severity": "medium",
      "resolution": null
    },
    ...
  ],
  "sources_count": 3
}
```

**Purpose:** Get full candidate detail with all evidence and conflicts

**Data Breakdown:**
- `merged_data` — Best-effort merge of all sources
- `confidence` — Overall confidence score (0.0-1.0)
- `score_details` — Component scores with reasoning
- `evidence` — Facts linked to sources (evidence graph)
- `conflicts` — Contradictions requiring review
- `sources_count` — Number of unique sources

---

#### 6. Verify/Reject Candidate
```
POST /api/intelligence/candidates/{candidate_id}/verify
Authorization: Bearer <token>
Content-Type: application/json

{
  "decision": "accept",
  "manual_corrections": {
    "email": "john.doe@techcorp.com",
    "linkedin_url": "https://linkedin.com/in/johndoe"
  }
}
```

**Purpose:** Human approval gate (accept/reject/uncertain)

**Decision Values:**
- `accept` — Treat as verified, create VerifiedProfile
- `reject` — Mark as incorrect, skip
- `uncertain` — Mark for manual review

**Response 200:**
```json
{
  "candidate_id": "uuid",
  "verification_status": "accept",
  "verified_at": "2026-08-11T..."
}
```

**Side Effects (if decision == "accept"):**
- `verification_status` → "accept"
- `VerifiedProfile` created with verified_facts + manual_corrections
- Ready for sales-script generation

---

#### 7. Get Verified Profile
```
GET /api/intelligence/sessions/{session_id}/verified-profile
Authorization: Bearer <token>

Response 200:
{
  "id": "uuid",
  "candidate_id": "uuid",
  "verified_facts": {
    "full_name": "John Doe",
    "company": "TechCorp",
    "title": "VP Sales",
    "location": "San Francisco, CA",
    "email": "john.doe@techcorp.com"
  },
  "labeled_inferences": [
    {
      "inference": "Likely manages sales team",
      "confidence": 0.85,
      "reasoning": "VP title + LinkedIn management experience"
    }
  ],
  "evidence_summary": [
    {
      "fact": "title = VP Sales",
      "sources": ["linkedin.com", "techcorp.com"],
      "confidence": 0.95
    }
  ],
  "overall_confidence": 0.85,
  "verified_at": "2026-08-11T..."
}
```

**Purpose:** Get final approved profile (after human verification)

**Usage:** Pass to sales-script generation engine

**Key Fields:**
- `verified_facts` — Human-approved ground truth (immutable)
- `labeled_inferences` — AI guesses clearly labeled
- `evidence_summary` — Reasoning trail
- `overall_confidence` — Final confidence score

---

#### 8. Delete Session
```
DELETE /api/intelligence/sessions/{session_id}
Authorization: Bearer <token>

Response 200:
{
  "message": "Session deleted",
  "session_id": "uuid"
}
```

**Purpose:** GDPR cleanup (delete session + all derived data)

**Side Effects (cascading delete):**
- IntelligenceSession deleted
- All ResearchQuery → SearchResult → Source → ExtractedEntity deleted
- All CandidateIdentity → IdentityScore, Evidence, Conflict, VerifiedProfile deleted
- Complete data expungement

---

## Authentication & Authorization

All endpoints require:
- `Authorization: Bearer <JWT_token>` header
- Ownership verification (user can only see/modify own sessions)
- 404 response if user lacks access

**Error Handling:**
- 401 → Missing/invalid token
- 403 → Access denied (not owner)
- 404 → Resource not found or access denied
- 500 → Server error

---

## Async Job Execution

### Flow
```
1. User calls POST /api/intelligence/sessions/{id}/research
2. API creates job record (status=queued) + background task
3. Returns job_id immediately
4. Client polls GET /api/intelligence/jobs/{job_id}/status
5. Background task executes orchestrator pipeline
6. Updates job status at each phase (10% → 90% → 100%)
7. Final results saved to database
8. Client can list candidates once job completed
```

### Status Transitions
```
create_job
    ↓
queued (0%)
    ↓
mark_running
    ↓
running (10%+)
    ↓ (phases: search→extract→resolve→score→conflicts)
    ↓
running (90%)
    ↓
mark_completed OR mark_failed
    ↓
completed (100%) OR failed (0% + error)
```

### Polling Recommendations
- Short poll interval (1s) for active sessions
- Long poll interval (5s) for idle sessions
- WebSocket for real-time updates (future enhancement)

---

## Error Scenarios

### Search Fails
- Orchestrator logs error, continues with next query
- If all queries fail: job marked as failed with error message

### Page Fetch Blocked
- robots.txt blocks → skip URL
- CAPTCHA detected → skip URL
- Login required → skip URL
- Timeout → skip URL
- Continues with remaining URLs

### Extraction Fails
- Deterministic extraction fails → skip
- No entity found → skip source

### No Results
- If no candidates found: job completes with 0 candidates (not failed)
- Returns empty candidate list

### Database Error
- Job marked as failed with database error message
- Partial data may be saved (transaction rollback)

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden (access denied) |
| 404 | Not found |
| 500 | Server error |

---

## Integration with Sales Script Engine

After human verification:

```python
# Get verified profile
profile = await GET /api/intelligence/sessions/{session_id}/verified-profile

# Pass to script engine
script = await sales_script_generator.generate(
    prospect={
        "verified_facts": profile.verified_facts,
        "labeled_inferences": profile.labeled_inferences,
        "evidence": profile.evidence_summary,
        "confidence": profile.overall_confidence
    },
    methodology="SPIN"
)
```

**Key Contract:**
- Script engine ONLY uses `verified_facts` as ground truth
- Can reference `labeled_inferences` but MUST label them as such
- Must cite evidence for transparency

---

## Testing Checklist

- [ ] Create session returns valid IntelligenceSession
- [ ] Start research creates job and queues background task
- [ ] Poll job status returns current state (queued, running, completed, failed)
- [ ] Job progresses through all phases (0% → 100%)
- [ ] List candidates returns all candidates for session
- [ ] Get candidate detail includes evidence and conflicts
- [ ] Verify candidate (accept) creates VerifiedProfile
- [ ] Verify candidate (reject) marks as rejected
- [ ] Get verified profile returns final approved data
- [ ] Delete session cascades to all child records
- [ ] Ownership checks prevent access to other users' sessions
- [ ] JWT authentication required for all endpoints
- [ ] Error handling for network timeouts, blocked pages, extraction failures

---

## Future Enhancements

### Phase 5: Frontend UI
- Intelligence hub screen (job progress, candidate list)
- Candidate review screen (evidence, conflicts, verification)
- Evidence graph visualization

### Job Coordination
- WebSocket for real-time progress updates (instead of polling)
- Celery/RQ for distributed job queue
- Job retry logic with exponential backoff
- Job timeout enforcement

### Scaling
- Cache search results across users (privacy-aware)
- Parallel extraction (fetch multiple URLs concurrently)
- Batch conflict detection
- Database query optimization (eager loading, indexes)

### Advanced Features
- LLM-based extraction fallback (when deterministic insufficient)
- Multiple identity candidates (if ambiguous)
- Confidence threshold gating (only verify if high confidence)
- Batch verification (multiple candidates at once)

---

**Status:** Phase 4 ✅ Complete. Ready for Phase 5: Frontend UI Screens.
