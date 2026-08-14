import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.research import ResearchSession, Finding, PlanStep
from app.models.materials import CompanyMaterial
from app.models.schemas import (
    ResearchSessionCreate, ResearchSessionOut, FindingOut,
    GenerateScriptRequest, UserSettingsUpdate, UserSettingsOut
)
from app.services.research_service import ResearchService
from app.services.deepseek_service import DeepSeekService

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/sessions", response_model=ResearchSessionOut, status_code=status.HTTP_201_CREATED)
async def create_research_session(
    payload: ResearchSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new research session."""
    service = ResearchService(db)
    session = await service.create_session(current_user.id, payload.prospect_input)
    return session


@router.post("/sessions/{session_id}/plan")
async def generate_plan(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive research using DeepSeek."""
    # Verify ownership
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        service = ResearchService(db)
        research_data = await service.generate_plan(session_id)
        return {"plan": research_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research generation error: {str(e)}")


@router.post("/sessions/{session_id}/execute")
async def execute_plan(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute the research plan (now a no-op since plan() does everything)."""
    # Verify ownership
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "completed",
        "message": "Research already completed during plan generation",
        "results": {"executed_steps": 1, "findings_created": 0, "errors": []}
    }


@router.get("/sessions/{session_id}", response_model=ResearchSessionOut)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a research session."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    return ResearchSessionOut(
        id=session.id,
        prospect_input=session.prospect_input,
        prospect_name=session.prospect_name,
        prospect_company=session.prospect_company,
        prospect_title=session.prospect_title,
        research_summary=session.research_summary,
        status=session.status,
        plan=session.plan if isinstance(session.plan, list) else [],
        findings=[],
        methodology=session.methodology,
        generated_output=session.generated_output,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions/{session_id}/findings")
async def get_findings(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get findings for a session."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(select(Finding).where(Finding.session_id == session_id))
    findings = result.scalars().all()

    return {"findings": [FindingOut.model_validate(f) for f in findings]}


@router.post("/sessions/{session_id}/findings/select")
async def select_findings(
    session_id: uuid.UUID,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark findings as selected."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    finding_ids = [uuid.UUID(fid) if isinstance(fid, str) else fid for fid in payload.get("finding_ids", [])]
    service = ResearchService(db)
    await service.select_findings(session_id, finding_ids)

    return {"selected_count": len(finding_ids)}


@router.post("/sessions/{session_id}/generate-script")
async def generate_script(
    session_id: uuid.UUID,
    payload: GenerateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a sales script based on research and selected methodology."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.plan or not isinstance(session.plan, dict):
        raise HTTPException(status_code=400, detail="Research not completed. Please generate research first.")

    from app.core.config import settings

    # Pull uploaded product material as grounding context
    material_result = await db.execute(
        select(CompanyMaterial).where(CompanyMaterial.session_id == session_id)
    )
    materials = material_result.scalars().all()
    product_context = "\n\n".join(
        f"[{m.material_type}] {m.name}: {m.content_text[:4000]}"
        for m in materials if m.content_text
    ) or None

    # Generate script using the structured research data
    deepseek = DeepSeekService(api_key=settings.DEEPSEEK_API_KEY)

    try:
        script = await deepseek.generate_sales_script(
            research_data=session.plan,  # Pass the comprehensive research data
            methodology=payload.methodology,
            prospect_name=session.prospect_name,
            prospect_title=session.prospect_title,
            prospect_company=session.prospect_company,
            product_context=product_context,
            research_summary=session.research_summary,
        )

        # Save
        service = ResearchService(db)
        await service.generate_output(session_id, payload.methodology, script)

        return {"script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation error: {str(e)}")


@router.post("/sessions/{session_id}/summarize")
async def summarize_research(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a research summary report from the comprehensive research data."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.plan or not isinstance(session.plan, dict):
        raise HTTPException(status_code=400, detail="Research not completed")

    from app.core.config import settings

    deepseek = DeepSeekService(api_key=settings.DEEPSEEK_API_KEY)

    try:
        summary = await deepseek.summarize_research(
            prospect_name=session.prospect_name,
            prospect_title=session.prospect_title,
            prospect_company=session.prospect_company,
            research_data=session.plan,
        )

        service = ResearchService(db)
        await service.save_summary(session_id, summary)

        return {"research_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation error: {str(e)}")


@router.get("/settings", response_model=UserSettingsOut)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user settings."""
    return {
        "deepseek_api_key": None,
        "deepseek_endpoint": None,
        "newsapi_endpoint": None,
        "product_name": None,
        "default_framework": "spin"
    }


@router.put("/settings")
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings."""
    # TODO: Implement updating user_settings table
    return {"status": "updated"}
