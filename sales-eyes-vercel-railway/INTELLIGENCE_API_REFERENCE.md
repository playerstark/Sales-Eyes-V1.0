# Intelligence Agent API Quick Reference

## Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/intelligence/sessions` | Create session |
| POST | `/api/intelligence/sessions/{id}/research` | Start research job |
| GET | `/api/intelligence/jobs/{id}/status` | Poll job progress |
| GET | `/api/intelligence/sessions/{id}/candidates` | List candidates |
| GET | `/api/intelligence/candidates/{id}` | Get candidate detail |
| POST | `/api/intelligence/candidates/{id}/verify` | Verify candidate |
| GET | `/api/intelligence/sessions/{id}/verified-profile` | Get verified profile |
| DELETE | `/api/intelligence/sessions/{id}` | Delete session |

---

## Example Workflows

### Basic Workflow

```bash
# 1. Create session
SESSION=$(curl -X POST http://localhost:8000/api/intelligence/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prospect_name":"John Doe","prospect_company":"TechCorp"}' \
  | jq -r '.id')

echo "Session: $SESSION"

# 2. Start research (async)
JOB=$(curl -X POST http://localhost:8000/api/intelligence/sessions/$SESSION/research \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.job_id')

echo "Job: $JOB"

# 3. Poll job status (repeat until completed)
curl -X GET http://localhost:8000/api/intelligence/jobs/$JOB/status \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. List candidates (once job completed)
curl -X GET http://localhost:8000/api/intelligence/sessions/$SESSION/candidates \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. Get candidate detail
CANDIDATE=$(curl -X GET http://localhost:8000/api/intelligence/sessions/$SESSION/candidates \
  -H "Authorization: Bearer $TOKEN" | jq -r '.candidates[0].id')

curl -X GET http://localhost:8000/api/intelligence/candidates/$CANDIDATE \
  -H "Authorization: Bearer $TOKEN" | jq

# 6. Verify candidate
curl -X POST http://localhost:8000/api/intelligence/candidates/$CANDIDATE/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"accept","manual_corrections":{}}' | jq

# 7. Get verified profile
curl -X GET http://localhost:8000/api/intelligence/sessions/$SESSION/verified-profile \
  -H "Authorization: Bearer $TOKEN" | jq
```

### With Manual Corrections

```bash
curl -X POST http://localhost:8000/api/intelligence/candidates/$CANDIDATE/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "accept",
    "manual_corrections": {
      "email": "john.doe@techcorp.com",
      "phone": "+1-555-0100",
      "title": "VP of Sales"
    }
  }' | jq
```

### Rejection

```bash
curl -X POST http://localhost:8000/api/intelligence/candidates/$CANDIDATE/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"reject"}' | jq
```

---

## Request/Response Schemas

### Create Session Request
```json
{
  "prospect_name": "John Doe",
  "prospect_company": "TechCorp"
}
```

### Create Session Response (201)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "prospect_name": "John Doe",
  "prospect_company": "TechCorp",
  "status": "created",
  "progress_percent": 0,
  "current_step": null,
  "queries_count": 0,
  "candidates_count": 0,
  "verified_profiles_count": 0,
  "created_at": "2026-08-11T12:00:00",
  "updated_at": "2026-08-11T12:00:00"
}
```

### Start Research Response (200)
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "650e8400-e29b-41d4-a716-446655440001",
  "status": "queued"
}
```

### Job Status Response (200)
```json
{
  "job_id": "650e8400-e29b-41d4-a716-446655440001",
  "status": "running",
  "progress_percent": 45,
  "current_step": "Extracting information from pages",
  "message": null,
  "error": null
}
```

### List Candidates Response (200)
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_candidates": 2,
  "candidates": [
    {
      "id": "750e8400-e29b-41d4-a716-446655440002",
      "canonical_full_name": "John Doe",
      "canonical_company": "TechCorp",
      "canonical_title": "VP Sales",
      "verification_status": "pending",
      "confidence": 0.85,
      "conflict_count": 1
    }
  ]
}
```

### Candidate Detail Response (200)
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440002",
  "canonical_full_name": "John Doe",
  "canonical_company": "TechCorp",
  "canonical_title": "VP Sales",
  "canonical_location": "San Francisco, CA",
  "merged_data": {
    "full_name": "John Doe",
    "email": "john.doe@techcorp.com",
    "skills": ["Sales", "Leadership"]
  },
  "verification_status": "pending",
  "confidence": 0.85,
  "score_details": {
    "component_scores": {
      "name_match": 0.95,
      "company_match": 0.80,
      "title_match": 0.90,
      "location_match": 0.70,
      "employment_history_consistency": 0.80,
      "cross_source_agreement": 0.80
    },
    "scoring_details": {
      "name_match": {
        "score": 0.95,
        "evidence": "3/3 sources agree on 'John Doe'"
      }
    }
  },
  "evidence": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440003",
      "fact_type": "title",
      "fact_value": "VP Sales",
      "source_url": "https://linkedin.com/in/johndoe",
      "source_snippet": "John Doe, VP Sales at TechCorp",
      "confidence": 0.95
    }
  ],
  "conflicts": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440004",
      "conflict_type": "title_change",
      "field_name": "title",
      "value_a": "VP Sales",
      "value_b": "Director, Sales",
      "source_a_url": "https://linkedin.com/...",
      "source_b_url": "https://techcorp.com/...",
      "severity": "medium",
      "resolution": null
    }
  ],
  "sources_count": 3
}
```

### Verify Candidate Request
```json
{
  "decision": "accept",
  "manual_corrections": {
    "email": "john.doe@techcorp.com"
  }
}
```

### Verify Candidate Response (200)
```json
{
  "candidate_id": "750e8400-e29b-41d4-a716-446655440002",
  "verification_status": "accept",
  "verified_at": "2026-08-11T12:05:00"
}
```

### Verified Profile Response (200)
```json
{
  "id": "a50e8400-e29b-41d4-a716-446655440005",
  "candidate_id": "750e8400-e29b-41d4-a716-446655440002",
  "verified_facts": {
    "full_name": "John Doe",
    "company": "TechCorp",
    "title": "VP Sales",
    "location": "San Francisco, CA",
    "email": "john.doe@techcorp.com"
  },
  "labeled_inferences": [
    {
      "inference": "Likely manages sales team of 10-50 people",
      "confidence": 0.80,
      "reasoning": "VP title + 'team' mentioned in LinkedIn"
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
  "verified_at": "2026-08-11T12:05:00"
}
```

---

## HTTP Status Codes

| Code | Scenario |
|------|----------|
| 200 | Success (GET, POST, DELETE) |
| 201 | Created (POST) |
| 400 | Bad request (invalid payload) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (access denied - not owner) |
| 404 | Not found (resource doesn't exist or access denied) |
| 500 | Server error |

---

## Authentication

All endpoints require:
```
Authorization: Bearer <JWT_TOKEN>
```

Token obtained from:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

Returns:
```json
{
  "access_token": "eyJ0...",
  "token_type": "bearer"
}
```

---

## Job Status Phases

| Status | Progress | Phase | Duration |
|--------|----------|-------|----------|
| queued | 0% | Waiting | ~immediately |
| running | 10% | Initializing search | ~1-5s per query |
| running | 30% | Extracting | ~2-3s per page |
| running | 50% | Resolving | ~10-50ms |
| running | 70% | Scoring | ~5-10ms |
| running | 90% | Detecting conflicts | ~10-20ms |
| completed | 100% | Done | ~immediately |
| failed | 0% | Error occurred | — |

**Example timeline for 5 queries + 10 results:**
- Queued: 0%
- Searching: 0-10% (5-10s)
- Extracting: 10-30% (30-45s)
- Resolving: 30-50% (<1s)
- Scoring: 50-70% (<1s)
- Conflicts: 70-90% (<1s)
- Completed: 100%
- **Total: ~45-65s**

---

## Error Examples

### Missing Token
```
curl http://localhost:8000/api/intelligence/sessions
```

Response (401):
```json
{
  "detail": "Not authenticated"
}
```

### Invalid Session
```
curl -X GET http://localhost:8000/api/intelligence/sessions/invalid-uuid \
  -H "Authorization: Bearer $TOKEN"
```

Response (404):
```json
{
  "detail": "Session not found"
}
```

### Access Denied
```
curl -X GET http://localhost:8000/api/intelligence/sessions/$OTHER_USER_SESSION \
  -H "Authorization: Bearer $TOKEN"
```

Response (403):
```json
{
  "detail": "Access denied"
}
```

### Research Failed
After job completes with error:

```
curl -X GET http://localhost:8000/api/intelligence/jobs/$JOB_ID/status \
  -H "Authorization: Bearer $TOKEN"
```

Response (200):
```json
{
  "job_id": "uuid",
  "status": "failed",
  "progress_percent": 0,
  "current_step": "Failed",
  "message": null,
  "error": "Search provider error: Connection timeout"
}
```

---

## SDK Example (Python)

```python
import requests
import time

API_BASE = "http://localhost:8000"
TOKEN = "..."  # JWT token

def create_session(prospect_name: str, prospect_company: str = None):
    resp = requests.post(
        f"{API_BASE}/api/intelligence/sessions",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"prospect_name": prospect_name, "prospect_company": prospect_company}
    )
    return resp.json()["id"]

def start_research(session_id: str):
    resp = requests.post(
        f"{API_BASE}/api/intelligence/sessions/{session_id}/research",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    return resp.json()["job_id"]

def wait_for_job(job_id: str, timeout_seconds: int = 600):
    start = time.time()
    while time.time() - start < timeout_seconds:
        resp = requests.get(
            f"{API_BASE}/api/intelligence/jobs/{job_id}/status",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        job = resp.json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(2)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout_seconds}s")

def get_candidates(session_id: str):
    resp = requests.get(
        f"{API_BASE}/api/intelligence/sessions/{session_id}/candidates",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    return resp.json()["candidates"]

def verify_candidate(candidate_id: str, decision: str = "accept", corrections: dict = None):
    resp = requests.post(
        f"{API_BASE}/api/intelligence/candidates/{candidate_id}/verify",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"decision": decision, "manual_corrections": corrections or {}}
    )
    return resp.json()

def get_verified_profile(session_id: str):
    resp = requests.get(
        f"{API_BASE}/api/intelligence/sessions/{session_id}/verified-profile",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    return resp.json()

# Usage
session_id = create_session("John Doe", "TechCorp")
job_id = start_research(session_id)
job = wait_for_job(job_id)

if job["status"] == "completed":
    candidates = get_candidates(session_id)
    if candidates:
        candidate_id = candidates[0]["id"]
        verify_candidate(candidate_id, "accept")
        profile = get_verified_profile(session_id)
        print(f"Verified: {profile['verified_facts']}")
```

---

## Monitoring & Debugging

### Check Session Status
```bash
curl -X GET http://localhost:8000/api/intelligence/sessions/$SESSION_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.status, .progress_percent'
```

### Stream Job Progress
```bash
while true; do
  curl -s -X GET http://localhost:8000/api/intelligence/jobs/$JOB_ID/status \
    -H "Authorization: Bearer $TOKEN" | jq '.progress_percent, .current_step'
  sleep 2
done
```

### Check Backend Logs
```bash
docker-compose logs -f backend | grep intelligence
```

### Database Inspection
```bash
# Count candidates for session
docker-compose exec db psql -U salesstalker -d sales_stalker -c \
  "SELECT COUNT(*) FROM candidate_identities WHERE session_id = '$SESSION_ID';"

# View conflicts
docker-compose exec db psql -U salesstalker -d sales_stalker -c \
  "SELECT conflict_type, field_name FROM conflicts WHERE candidate_id = '$CANDIDATE_ID';"
```

---

**API Reference Complete.** For more details, see PHASE4_COMPLETION.md and INTELLIGENCE_ARCHITECTURE.md.
