import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# =========================================
# Request Schemas
# =========================================

class StartIntelligenceResearchRequest(BaseModel):
    """Request to start prospect intelligence research."""
    prospect_name: str = Field(..., min_length=1)
    prospect_company: Optional[str] = None
    research_session_id: Optional[uuid.UUID] = None  # Link to existing research session


class VerifyCandidateRequest(BaseModel):
    """Request to verify/reject a candidate identity."""
    decision: str = Field(..., description="accept | reject | uncertain")
    manual_corrections: Optional[dict] = Field(default_factory=dict, description="Field overrides")


# =========================================
# Response Schemas
# =========================================

class ExtractedEntityOut(BaseModel):
    """Extracted entity from a source."""
    id: uuid.UUID
    entity_type: str
    full_name: Optional[str]
    current_title: Optional[str]
    current_company: Optional[str]
    location: Optional[str]
    email: Optional[str]
    linkedin_url: Optional[str]
    skills: list[str]
    extraction_method: str
    extraction_confidence: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    """Source document metadata."""
    id: uuid.UUID
    url: str
    title: Optional[str]
    domain: Optional[str]
    fetch_status: str
    fetch_error: Optional[str]
    fetched_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResultOut(BaseModel):
    """Search result with optional source content."""
    id: uuid.UUID
    title: Optional[str]
    snippet: Optional[str]
    url: str
    source: Optional[SourceOut] = None
    extracted_entities: list[ExtractedEntityOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchQueryOut(BaseModel):
    """Search query execution record."""
    id: uuid.UUID
    query_text: str
    search_provider: str
    status: str
    results_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    """Evidence linking a fact to a source."""
    id: uuid.UUID
    fact_type: str
    fact_value: str
    source_url: str
    source_snippet: Optional[str]
    confidence_in_fact: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictOut(BaseModel):
    """Detected contradiction between sources."""
    id: uuid.UUID
    conflict_type: str
    field_name: str
    value_a: str
    value_b: str
    source_a_url: str
    source_b_url: str
    resolution: Optional[str]
    resolved_value: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IdentityScoreOut(BaseModel):
    """Confidence scoring breakdown."""
    id: uuid.UUID
    overall_confidence: float
    name_match_score: Optional[float]
    company_match_score: Optional[float]
    title_match_score: Optional[float]
    location_match_score: Optional[float]
    employment_history_consistency_score: Optional[float]
    cross_source_agreement_score: Optional[float]
    scoring_details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateIdentityOut(BaseModel):
    """Candidate person profile with all evidence."""
    id: uuid.UUID
    canonical_full_name: str
    canonical_company: Optional[str]
    canonical_title: Optional[str]
    canonical_location: Optional[str]
    merged_data: dict
    verification_status: str
    identity_score: Optional[IdentityScoreOut]
    conflicts: list[ConflictOut] = []
    evidence_count: int = 0
    created_at: datetime
    verified_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CandidateDetailOut(BaseModel):
    """Full candidate details with all related entities."""
    id: uuid.UUID
    canonical_full_name: str
    canonical_company: Optional[str]
    canonical_title: Optional[str]
    merged_data: dict
    verification_status: str
    identity_score: Optional[IdentityScoreOut]
    conflicts: list[ConflictOut]
    evidence: list[EvidenceOut]
    sources_count: int

    model_config = {"from_attributes": True}


class VerifiedProfileOut(BaseModel):
    """Final, human-approved prospect intelligence."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    verified_facts: dict
    labeled_inferences: list
    evidence_summary: list
    overall_confidence: float
    verified_at: datetime

    model_config = {"from_attributes": True}


class IntelligenceSessionOut(BaseModel):
    """Intelligence research session status."""
    id: uuid.UUID
    prospect_name: str
    prospect_company: Optional[str]
    status: str
    progress_percent: int
    current_step: Optional[str]
    queries_count: int = 0
    candidates_count: int = 0
    verified_profiles_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IntelligenceJobStatusOut(BaseModel):
    """Async job status response."""
    job_id: uuid.UUID
    status: str
    progress_percent: int
    current_step: Optional[str]
    message: Optional[str]
    error: Optional[str]

    model_config = {"from_attributes": True}


class IntelligenceStartOut(BaseModel):
    """Response after starting intelligence research."""
    session_id: uuid.UUID
    job_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}
