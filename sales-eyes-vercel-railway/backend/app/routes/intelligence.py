"""Prospect Intelligence Agent API routes."""

import logging
import uuid
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.intelligence import (
    IntelligenceSession, CandidateIdentity, IdentityScore, Evidence, Conflict, VerifiedProfile
)
from app.schemas.intelligence import (
    IntelligenceSessionOut, StartIntelligenceResearchRequest, VerifyCandidateRequest,
    CandidateIdentityOut, CandidateDetailOut, VerifiedProfileOut, IntelligenceJobStatusOut,
    IntelligenceStartOut
)
from app.services.intelligence.orchestrator import IntelligenceOrchestrator
from app.services.intelligence.providers.duckduckgo_search import DuckDuckGoSearchProvider
from app.services.intelligence.providers.deterministic_extraction import DeterministicExtractor
from app.services.intelligence.providers.entity_extractor import DeterministicEntityExtractor
from app.services.intelligence.providers.page_fetcher import SafePageFetcher
from app.services.intelligence.job_tracker import get_job_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# =========================================
# Helper Functions
# =========================================

def _create_orchestrator() -> IntelligenceOrchestrator:
    """Create orchestrator with default providers."""
    search = DuckDuckGoSearchProvider(timeout_seconds=10)
    fetcher = SafePageFetcher(search_provider=search)
    extractor = DeterministicExtractor()
    entity_extractor = DeterministicEntityExtractor()

    # Note: db will be injected per-request
    return IntelligenceOrchestrator(
        db=None,  # Set by caller
        search_provider=search,
        content_extractor=extractor,
        entity_extractor=entity_extractor,
        page_fetcher=fetcher,
    )


async def _run_research_background(
    session_id: uuid.UUID,
    job_id: str,
    db: AsyncSession,
    prospect_name: str,
    prospect_company: Optional[str]
) -> None:
    """Background task for research execution."""
    job_tracker = get_job_tracker()

    try:
        job_tracker.mark_running(job_id, "Initializing research")

        # Create orchestrator
        orchestrator = _create_orchestrator()
        orchestrator.db = db

        # Execute research
        result = await orchestrator.research(
            session_id=session_id,
            prospect_name=prospect_name,
            prospect_company=prospect_company,
            max_queries=5,
            max_pages_per_query=10
        )

        job_tracker.mark_completed(job_id, f"Research complete: {result.get('total_candidates', 0)} candidates found")

    except Exception as e:
        logger.exception(f"Research failed for job {job_id}: {e}")
        job_tracker.mark_failed(job_id, str(e))


# =========================================
# Routes
# =========================================

@router.post("/sessions", response_model=IntelligenceSessionOut, status_code=status.HTTP_201_CREATED)
async def create_intelligence_session(
    payload: StartIntelligenceResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IntelligenceSessionOut:
    """Create a new intelligence research session."""
    try:
        session = IntelligenceSession(
            owner_id=current_user.id,
            prospect_name=payload.prospect_name,
            prospect_company=payload.prospect_company,
            status="created",
            config={
                "score_weights": {
                    "name_match": 0.25,
                    "company_match": 0.25,
                    "title_match": 0.15,
                    "location_match": 0.10,
                    "employment_history_consistency": 0.15,
                    "cross_source_agreement": 0.10
                }
            }
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(f"Created intelligence session {session.id} for user {current_user.id}")
        return IntelligenceSessionOut.model_validate(session)

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/sessions/{session_id}/research", response_model=IntelligenceStartOut)
async def start_research(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> IntelligenceStartOut:
    """Start intelligence research (async job).

    Returns job ID for polling progress.
    """
    try:
        # Verify ownership
        session = await db.get(IntelligenceSession, session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Create job
        job_tracker = get_job_tracker()
        job_id = job_tracker.create_job(session_id)

        # Queue background task
        background_tasks.add_task(
            _run_research_background,
            session_id,
            job_id,
            db,
            session.prospect_name,
            session.prospect_company
        )

        logger.info(f"Queued research job {job_id} for session {session_id}")

        return IntelligenceStartOut(
            session_id=session_id,
            job_id=uuid.UUID(job_id),
            status="queued"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting research: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")


@router.get("/jobs/{job_id}/status", response_model=IntelligenceJobStatusOut)
async def get_job_status(job_id: uuid.UUID) -> IntelligenceJobStatusOut:
    """Poll job progress."""
    try:
        job_tracker = get_job_tracker()
        job = job_tracker.get_job(str(job_id))

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return IntelligenceJobStatusOut(
            job_id=uuid.UUID(job["job_id"]),
            status=job["status"],
            progress_percent=job["progress_percent"],
            current_step=job["current_step"],
            message=job.get("message"),
            error=job.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.get("/sessions/{session_id}/candidates")
async def list_candidates(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """List all candidates for a session."""
    try:
        # Verify ownership
        session = await db.get(IntelligenceSession, session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get candidates
        result = await db.execute(
            select(CandidateIdentity).where(CandidateIdentity.session_id == session_id)
        )
        candidates = result.scalars().all()

        return {
            "session_id": str(session_id),
            "total_candidates": len(candidates),
            "candidates": [
                {
                    "id": str(c.id),
                    "canonical_full_name": c.canonical_full_name,
                    "canonical_company": c.canonical_company,
                    "canonical_title": c.canonical_title,
                    "verification_status": c.verification_status,
                    "confidence": float(c.identity_score.overall_confidence) if c.identity_score else 0.0,
                    "conflict_count": len(c.conflicts),
                }
                for c in candidates
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing candidates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list candidates")


@router.get("/candidates/{candidate_id}", response_model=dict)
async def get_candidate_detail(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get full candidate detail with evidence and conflicts."""
    try:
        # Get candidate
        candidate = await db.get(CandidateIdentity, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Verify ownership (through session)
        session = await db.get(IntelligenceSession, candidate.session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get related data
        result = await db.execute(
            select(Evidence).where(Evidence.candidate_id == candidate_id)
        )
        evidence_records = result.scalars().all()

        conflict_result = await db.execute(
            select(Conflict).where(Conflict.candidate_id == candidate_id)
        )
        conflict_records = conflict_result.scalars().all()

        return {
            "id": str(candidate.id),
            "canonical_full_name": candidate.canonical_full_name,
            "canonical_company": candidate.canonical_company,
            "canonical_title": candidate.canonical_title,
            "canonical_location": candidate.canonical_location,
            "merged_data": candidate.merged_data,
            "verification_status": candidate.verification_status,
            "confidence": float(candidate.identity_score.overall_confidence) if candidate.identity_score else 0.0,
            "score_details": candidate.identity_score.scoring_details if candidate.identity_score else {},
            "evidence": [
                {
                    "id": str(e.id),
                    "fact_type": e.fact_type,
                    "fact_value": e.fact_value,
                    "source_url": e.source_url,
                    "source_snippet": e.source_snippet,
                    "confidence": float(e.confidence_in_fact) if e.confidence_in_fact else 0.0,
                }
                for e in evidence_records
            ],
            "conflicts": [
                {
                    "id": str(c.id),
                    "conflict_type": c.conflict_type,
                    "field_name": c.field_name,
                    "value_a": c.value_a,
                    "value_b": c.value_b,
                    "source_a_url": c.source_a_url,
                    "source_b_url": c.source_b_url,
                    "severity": self._infer_severity(c.conflict_type),
                    "resolution": c.resolution,
                }
                for c in conflict_records
            ],
            "sources_count": len(set(e.source_url for e in evidence_records)),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to get candidate detail")


@router.post("/candidates/{candidate_id}/verify")
async def verify_candidate(
    candidate_id: uuid.UUID,
    payload: VerifyCandidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Verify/reject a candidate identity (human decision gate)."""
    try:
        # Get candidate
        candidate = await db.get(CandidateIdentity, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Verify ownership
        session = await db.get(IntelligenceSession, candidate.session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update candidate
        candidate.verification_status = payload.decision
        candidate.human_decision = payload.decision

        if payload.manual_corrections:
            candidate.manual_corrections = payload.manual_corrections

        if payload.decision == "accept":
            candidate.verified_at = None  # Will be set when VerifiedProfile created
            # Create verified profile
            verified_profile = VerifiedProfile(
                candidate_id=candidate_id,
                session_id=candidate.session_id,
                verified_facts={
                    "full_name": candidate.canonical_full_name,
                    "company": candidate.canonical_company,
                    "title": candidate.canonical_title,
                    "location": candidate.canonical_location,
                    **payload.manual_corrections
                },
                labeled_inferences=[],
                evidence_summary=[],
                overall_confidence=candidate.identity_score.overall_confidence if candidate.identity_score else 0.0,
                verified_by_user_id=current_user.id,
            )
            db.add(verified_profile)

        await db.commit()

        logger.info(f"Verified candidate {candidate_id}: {payload.decision}")

        return {
            "candidate_id": str(candidate_id),
            "verification_status": candidate.verification_status,
            "verified_at": candidate.verified_at.isoformat() if candidate.verified_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying candidate: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify candidate")


@router.get("/sessions/{session_id}/verified-profile", response_model=dict)
async def get_verified_profile(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get final verified intelligence profile (after human approval)."""
    try:
        # Verify ownership
        session = await db.get(IntelligenceSession, session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get verified profile
        result = await db.execute(
            select(VerifiedProfile).where(VerifiedProfile.session_id == session_id).limit(1)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail="No verified profile yet")

        return {
            "id": str(profile.id),
            "candidate_id": str(profile.candidate_id),
            "verified_facts": profile.verified_facts,
            "labeled_inferences": profile.labeled_inferences,
            "evidence_summary": profile.evidence_summary,
            "overall_confidence": float(profile.overall_confidence),
            "verified_at": profile.verified_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verified profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get verified profile")


@router.delete("/sessions/{session_id}")
async def delete_intelligence_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a session and all derived data (GDPR cleanup)."""
    try:
        # Verify ownership
        session = await db.get(IntelligenceSession, session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete (cascading delete handles related records)
        await db.delete(session)
        await db.commit()

        logger.info(f"Deleted intelligence session {session_id}")

        return {"message": "Session deleted", "session_id": str(session_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@staticmethod
def _infer_severity(conflict_type: str) -> str:
    """Infer severity from conflict type."""
    if conflict_type in ("name_mismatch", "company_change"):
        return "high"
    return "medium"
