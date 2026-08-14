import uuid
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Finding
from app.services.deepseek_service import DeepSeekService


class PainPointService:
    def __init__(self, db: AsyncSession, deepseek_key: Optional[str] = None):
        self.db = db
        self.deepseek_service = DeepSeekService(api_key=deepseek_key)

    async def extract_pain_points_from_material(
        self,
        session_id: uuid.UUID,
        material_content: str,
        material_name: str,
        material_type: str,
        material_id: str | None = None
    ) -> list[Finding]:
        """Extract pain points from uploaded material and create findings."""
        if not material_content or not material_content.strip():
            return []

        # Use DeepSeek to identify pain points from the material
        pain_points = await self.deepseek_service.extract_pain_points(
            material_content[:5000],  # Limit to first 5000 chars for API
            material_type,
            material_name
        )

        findings = []
        if pain_points:
            for point in pain_points:
                finding = Finding(
                    session_id=session_id,
                    finding_type="pain_point",
                    summary=point.get("title", ""),
                    source_type="uploaded_material",
                    source_reference=material_id,
                    details={
                        "description": point.get("description", ""),
                        "material_name": material_name,
                        "material_type": material_type,
                        "relevance": point.get("relevance", "high")
                    },
                    confidence_score=float(point.get("confidence", 0.85))
                )
                self.db.add(finding)
                findings.append(finding)

        if findings:
            await self.db.commit()

        return findings

    async def extract_pain_points_from_research(
        self,
        session_id: uuid.UUID,
        prospect_info: str,
        research_findings: list[dict]
    ) -> list[Finding]:
        """Extract pain points from research findings and internet sources."""
        if not research_findings:
            return []

        findings_text = "\n".join([f.get("summary", "") for f in research_findings])

        # Use DeepSeek to synthesize pain points
        pain_points = await self.deepseek_service.synthesize_pain_points(
            prospect_info,
            findings_text
        )

        findings = []
        for idx, point in enumerate(pain_points, 1):
            finding = Finding(
                session_id=session_id,
                finding_type="pain_point",
                summary=point.get("title", ""),
                source_link=point.get("source_url"),
                source_type="internet",
                source_reference=point.get("source_url"),
                details={
                    "description": point.get("description", ""),
                    "industry": point.get("industry"),
                    "trend": point.get("trend", False),
                    "sources": point.get("sources", [])
                },
                confidence_score=float(point.get("confidence", 0.80))
            )
            self.db.add(finding)
            findings.append(finding)

        if findings:
            await self.db.commit()

        return findings
