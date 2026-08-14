import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, func, Integer, ForeignKey, DECIMAL, Text, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IntelligenceSession(Base):
    """Tracks the prospect intelligence research lifecycle."""
    __tablename__ = "intelligence_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    research_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=True)

    prospect_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Initial input
    prospect_company: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="searching", nullable=False)  # searching | extracting | resolving | verifying | completed | failed
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Configuration at research time (immutable snapshot)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # {score_weights, thresholds, etc.}

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    queries: Mapped[list["ResearchQuery"]] = relationship("ResearchQuery", cascade="all, delete-orphan")
    candidates: Mapped[list["CandidateIdentity"]] = relationship("CandidateIdentity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_intelligence_sessions_owner", "owner_id"),
        Index("idx_intelligence_sessions_status", "status"),
    )


class ResearchQuery(Base):
    """Search queries executed during intelligence phase."""
    __tablename__ = "research_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("intelligence_sessions.id", ondelete="CASCADE"), nullable=False)

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # duckduckgo, google, brave, etc.
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | in_progress | completed | failed

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    results: Mapped[list["SearchResult"]] = relationship("SearchResult", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_research_queries_session", "session_id"),
    )


class SearchResult(Base):
    """Raw search results from provider (before content extraction)."""
    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_queries.id", ondelete="CASCADE"), nullable=False)

    result_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Position in result set
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False, index=True)  # Index for deduplication

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="search_result", uselist=False, cascade="all, delete-orphan")
    extracted_entities: Mapped[list["ExtractedEntity"]] = relationship("ExtractedEntity", back_populates="search_result", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_search_results_query", "query_id"),
        Index("idx_search_results_url", "url"),
    )


class Source(Base):
    """Normalized source metadata (one per URL, deduplicated)."""
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("search_results.id", ondelete="CASCADE"), nullable=False)

    url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)  # Prevent re-fetching
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # text/html, application/pdf, etc.
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # Cleaned for readability

    fetch_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | success | blocked | timeout | error
    fetch_error: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Retention tracking
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # When to delete

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    search_result: Mapped["SearchResult"] = relationship("SearchResult", back_populates="source")

    __table_args__ = (
        Index("idx_sources_url", "url"),
        Index("idx_sources_retention", "retention_expires_at"),
    )


class ExtractedEntity(Base):
    """Extracted person/company entity from a source (before identity resolution)."""
    __tablename__ = "extracted_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("search_results.id", ondelete="CASCADE"), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # person | company | organization

    # Extracted fields (use null/"Unknown" for unverified)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Employment history, education, skills (stored as JSON)
    employment_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{company, title, start_date, end_date}, ...]
    education: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{school, degree, field, year}, ...]
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list, nullable=False)

    # Projects, publications, social presence
    projects: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    publications: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    social_profiles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # {github, twitter, etc.}

    # Extraction metadata
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)  # deterministic | llm
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0-1.0
    raw_extraction_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # Full LLM output or parser result

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    search_result: Mapped["SearchResult"] = relationship("SearchResult", back_populates="extracted_entities")

    __table_args__ = (
        Index("idx_extracted_entities_search_result", "search_result_id"),
        Index("idx_extracted_entities_name", "full_name"),
    )


class CandidateIdentity(Base):
    """A reconciled candidate person profile (may be accepted or rejected by user)."""
    __tablename__ = "candidate_identities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("intelligence_sessions.id", ondelete="CASCADE"), nullable=False)

    # Primary identity fields (from best sources)
    canonical_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Merged profile data
    merged_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # Best-effort merge of all extracted entities

    # Verification status
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | verified | rejected | uncertain
    human_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)  # accept | reject | manual_correction

    # Corrections made by human (overrides merged_data)
    manual_corrections: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    identity_score: Mapped["IdentityScore"] = relationship("IdentityScore", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    conflicts: Mapped[list["Conflict"]] = relationship("Conflict", back_populates="candidate", cascade="all, delete-orphan")
    evidence_links: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="candidate")
    verified_profile: Mapped["VerifiedProfile"] = relationship("VerifiedProfile", back_populates="candidate", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_candidate_identities_session", "session_id"),
        Index("idx_candidate_identities_status", "verification_status"),
        Index("idx_candidate_identities_name", "canonical_full_name"),
    )


class IdentityScore(Base):
    """Evidence-based confidence scoring breakdown for a candidate."""
    __tablename__ = "identity_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_identities.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Overall confidence (0.0 - 1.0)
    overall_confidence: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), nullable=False)

    # Component scores (with configurable weights)
    name_match_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    company_match_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    title_match_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    location_match_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    employment_history_consistency_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    cross_source_agreement_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)

    # Scoring reasoning (for transparency)
    scoring_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # {component: evidence_list, calculation}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["CandidateIdentity"] = relationship("CandidateIdentity", back_populates="identity_score")

    __table_args__ = (
        Index("idx_identity_scores_candidate", "candidate_id"),
    )


class Evidence(Base):
    """Links a fact to its source URL (evidence graph edge)."""
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_identities.id", ondelete="CASCADE"), nullable=False)
    extracted_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_entities.id", ondelete="CASCADE"), nullable=False)

    # Fact metadata
    fact_type: Mapped[str] = mapped_column(String(100), nullable=False)  # name | title | company | location | email | etc.
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)  # The actual extracted value

    # Source context
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # Quote from page
    confidence_in_fact: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)  # How confident in this specific fact

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["CandidateIdentity"] = relationship("CandidateIdentity", back_populates="evidence_links")

    __table_args__ = (
        Index("idx_evidence_candidate", "candidate_id"),
        Index("idx_evidence_entity", "extracted_entity_id"),
        Index("idx_evidence_fact_type", "fact_type"),
    )


class Conflict(Base):
    """Detected contradiction across sources for a candidate."""
    __tablename__ = "conflicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_identities.id", ondelete="CASCADE"), nullable=False)

    # Conflict details
    conflict_type: Mapped[str] = mapped_column(String(100), nullable=False)  # title | company | location | employment_gap | etc.
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)  # The field that conflicts

    # The conflicting values
    value_a: Mapped[str] = mapped_column(Text, nullable=False)  # Source A value
    value_b: Mapped[str] = mapped_column(Text, nullable=False)  # Source B value
    source_a_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_b_url: Mapped[str] = mapped_column(String(512), nullable=False)

    # Resolution
    resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)  # manual | ignored | reconciled
    resolved_value: Mapped[str | None] = mapped_column(Text, nullable=True)  # What human/system chose

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["CandidateIdentity"] = relationship("CandidateIdentity", back_populates="conflicts")

    __table_args__ = (
        Index("idx_conflicts_candidate", "candidate_id"),
        Index("idx_conflicts_type", "conflict_type"),
    )


class VerifiedProfile(Base):
    """Final, human-approved prospect intelligence profile."""
    __tablename__ = "verified_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_identities.id", ondelete="CASCADE"), nullable=False, unique=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("intelligence_sessions.id", ondelete="CASCADE"), nullable=False)

    # Verified facts (human-approved)
    verified_facts: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {full_name, company, title, location, contact_info, etc.}

    # Inferences with confidence labels
    labeled_inferences: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{inference, confidence, reasoning}, ...]

    # Complete evidence trail
    evidence_summary: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{fact, sources, confidence}, ...]

    # Overall assessment
    overall_confidence: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), nullable=False)
    verified_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["CandidateIdentity"] = relationship("CandidateIdentity", back_populates="verified_profile")

    __table_args__ = (
        Index("idx_verified_profiles_candidate", "candidate_id"),
        Index("idx_verified_profiles_session", "session_id"),
    )
