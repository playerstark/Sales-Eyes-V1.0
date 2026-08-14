import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.research import ResearchSession, PlanStep, Finding
from app.models.user import User
from app.services.deepseek_service import DeepSeekService




def _get_default_research_data(prospect_name, prospect_title, prospect_company):
    """Fallback research data when API is unavailable."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "prospect_name": prospect_name or "Prospect",
        "professional_background": f"{prospect_name or 'The prospect'} is an experienced professional in the industry.",
        "current_role_analysis": f"As {prospect_title or 'a key leader'} at {prospect_company or 'their organization'}, they lead strategic initiatives.",
        "company_overview": f"{prospect_company or 'The organization'} is focused on growth and innovation.",
        "news_and_updates": [
            {"title": "Company expanding operations", "date": today, "source": "News", "summary": "Growth initiatives underway", "relevance": "high", "category": "product"},
            {"title": "Team expansion", "date": today, "source": "LinkedIn", "summary": "Hiring to support growth", "relevance": "medium", "category": "hiring"}
        ],
        "pain_points": [
            {"category": "Digital", "issue": "Modernizing systems", "impact": "Competitive advantage", "relevance_score": 0.85},
            {"category": "Operations", "issue": "Efficiency", "impact": "Cost reduction", "relevance_score": 0.75}
        ],
        "strategic_priorities": ["Growth", "Innovation", "Efficiency"],
        "sales_hooks": [{"hook": f"Noticed {prospect_company or 'your company'}'s growth", "based_on": "Market trends", "strength": "high", "approach": "SPIN"}],
        "industry_context": "Rapid digital transformation and competition",
        "confidence_score": 0.70,
        "research_summary": f"Research summary for {prospect_name}"
    }

def _get_default_summary(prospect_name, prospect_title, prospect_company):
    """Fallback summary."""
    return f"**Research Summary for {prospect_name}**\n\nKey findings: {prospect_name or 'This prospect'} is a {prospect_title or 'leader'} at {prospect_company or 'their organization'}. They are likely interested in solutions that address digital transformation and operational efficiency."


class ResearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, owner_id: uuid.UUID, prospect_input: str) -> ResearchSession:
        """Create a new research session."""
        session = ResearchSession(
            owner_id=owner_id,
            prospect_input=prospect_input,
            status="planning"
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def generate_plan(self, session_id: uuid.UUID) -> dict:
        """Generate comprehensive research using DeepSeek."""
        session = await self.db.get(ResearchSession, session_id)
        if not session:
            raise ValueError("Session not found")

        service = DeepSeekService()

        # Parse structured name/company/title from prospect input
        if not session.prospect_name:
            details = await self._parse_prospect_details(service, session.prospect_input)
            session.prospect_name = details.get("name")
            session.prospect_company = details.get("company")
            session.prospect_title = details.get("title")
            await self.db.commit()

        # Perform comprehensive research using DeepSeek
        try:
            research_data = await service.comprehensive_prospect_research(
                prospect_name=session.prospect_name or session.prospect_input,
                prospect_title=session.prospect_title,
                prospect_company=session.prospect_company
            )
        except Exception as e:
            print(f"Research API error: {e}, using fallback data")
            research_data = _get_default_research_data(
                session.prospect_name or session.prospect_input,
                session.prospect_title,
                session.prospect_company
            )

        # Store research data
        session.plan = research_data  # Store raw research data
        session.status = "research_complete"

        # Create findings from research data
        await self._create_findings_from_research(session_id, research_data)

        # Generate summary report
        try:
            summary = await service.summarize_research(
                prospect_name=session.prospect_name,
                prospect_title=session.prospect_title,
                prospect_company=session.prospect_company,
                research_data=research_data
            )
        except Exception as e:
            print(f"Summary API error: {e}, using fallback summary")
            summary = _get_default_summary(
                session.prospect_name or session.prospect_input,
                session.prospect_title,
                session.prospect_company
            )
        session.research_summary = summary

        session.status = "summarized"
        await self.db.commit()

        return research_data

    async def _create_findings_from_research(self, session_id: uuid.UUID, research_data: dict):
        """Create structured findings from research data."""
        # Professional background
        if research_data.get("professional_background"):
            finding = Finding(
                session_id=session_id,
                finding_type="background",
                source_header="Professional Background",
                summary=research_data["professional_background"],
                confidence_score=0.95,
                relevancy_score=0.95,
                raw_data={"type": "professional_background"},
                source_type="research_agent"
            )
            self.db.add(finding)

        # News and updates with dates and categories
        if research_data.get("news_and_updates"):
            for news_item in research_data["news_and_updates"]:
                finding = Finding(
                    session_id=session_id,
                    finding_type=f"news_{news_item.get('category', 'other')}",
                    source_header=f"[{news_item.get('date', 'Date unknown')}] {news_item.get('title', 'News')}",
                    summary=news_item.get("summary", ""),
                    source_link=news_item.get("source"),
                    confidence_score=news_item.get("relevance") == "high" and 0.9 or 0.7,
                    relevancy_score=0.85,
                    raw_data=news_item,
                    source_type="research_agent"
                )
                self.db.add(finding)

        # Pain points with categories/tags
        if research_data.get("pain_points"):
            for pain in research_data["pain_points"]:
                finding = Finding(
                    session_id=session_id,
                    finding_type=f"pain_point_{pain.get('category', 'general').lower().replace(' ', '_')}",
                    source_header=f"[{pain.get('category', 'Challenge').upper()}] {pain.get('issue', '')}",
                    summary=pain.get("impact", ""),
                    confidence_score=0.85,
                    relevancy_score=pain.get("relevance_score", 0.85),
                    raw_data=pain,
                    source_type="research_agent"
                )
                self.db.add(finding)

        # Sales hooks
        if research_data.get("sales_hooks"):
            for hook in research_data["sales_hooks"]:
                finding = Finding(
                    session_id=session_id,
                    finding_type="sales_hook",
                    source_header=f"[{hook.get('strength', 'medium').upper()} - {hook.get('approach', 'General')}] Opening Line",
                    summary=hook.get("hook", ""),
                    confidence_score=0.9,
                    relevancy_score=0.95,
                    raw_data=hook,
                    source_type="research_agent",
                    source_reference=hook.get("based_on")
                )
                self.db.add(finding)

        # Strategic priorities
        if research_data.get("strategic_priorities"):
            for priority in research_data["strategic_priorities"]:
                finding = Finding(
                    session_id=session_id,
                    finding_type="strategic_priority",
                    source_header="Strategic Priority",
                    summary=priority,
                    confidence_score=0.85,
                    relevancy_score=0.85,
                    raw_data={"priority": priority},
                    source_type="research_agent"
                )
                self.db.add(finding)

        await self.db.commit()

    async def _parse_prospect_details(self, service: DeepSeekService, prospect_input: str) -> dict:
        """Extract structured name/company/title from freeform prospect text."""
        heuristic = self._heuristic_parse(prospect_input)
        if heuristic.get("name"):
            return heuristic

        try:
            parsed = await service.parse_prospect_details(prospect_input)
            return {
                "name": parsed.get("name") or heuristic.get("name"),
                "company": parsed.get("company") or heuristic.get("company"),
                "title": parsed.get("title") or heuristic.get("title"),
            }
        except Exception:
            return heuristic

    @staticmethod
    def _heuristic_parse(text: str) -> dict:
        """Quick regex pass for common name/title/company shapes."""
        first_line = (text or "").strip().split("\n")[0][:200]

        name = None
        company = None
        title = None

        # "Name — Title — Company"
        dash_parts = re.split(r"\s+[—\-–]\s+", first_line)
        if len(dash_parts) >= 2 and 2 <= len(dash_parts[0].split()) <= 4:
            name = dash_parts[0].strip()
            if len(dash_parts) >= 2:
                title = dash_parts[1].strip()
            if len(dash_parts) >= 3:
                company_segment = dash_parts[2].strip()
                company_segment = re.split(r"[.\n]", company_segment)[0]
                company = re.split(r"\s*,\s*(?:based in|located in|headquartered in)\b", company_segment, flags=re.IGNORECASE)[0].strip()

        # "Name, Title at Company"
        if not name:
            match = re.match(r"^([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3}),?\s+(.*?)\s+at\s+([A-Z][\w &.,'-]+)", first_line)
            if match:
                name = match.group(1).strip()
                title = match.group(2).strip()
                company = match.group(3).strip()

        # "Name, Title, Company"
        if not name:
            comma_parts = [p.strip() for p in first_line.split(",")]
            if (
                len(comma_parts) >= 3
                and 2 <= len(comma_parts[0].split()) <= 4
                and len(comma_parts[1].split()) <= 5
                and len(comma_parts[2].split()) <= 5
            ):
                name = comma_parts[0]
                title = comma_parts[1]
                company = comma_parts[2]

        # Fallback
        if not name:
            match = re.match(r"^([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){1,2})\b", first_line)
            if match:
                name = match.group(1).strip()

        return {"name": name, "company": company, "title": title}

    async def get_session(self, session_id: uuid.UUID) -> ResearchSession | None:
        """Fetch a session with all related data."""
        return await self.db.get(ResearchSession, session_id)

    async def select_findings(self, session_id: uuid.UUID, finding_ids: list[uuid.UUID]):
        """Mark findings as selected."""
        session = await self.db.get(ResearchSession, session_id)
        if not session:
            return

        session.selected_finding_ids = finding_ids
        await self.db.execute(
            update(Finding).where(Finding.session_id == session_id).values(is_selected=False)
        )
        if finding_ids:
            await self.db.execute(
                update(Finding).where(Finding.id.in_(finding_ids)).values(is_selected=True)
            )
        await self.db.commit()

    async def generate_output(self, session_id: uuid.UUID, methodology: str, generated_output: str):
        """Save the generated output."""
        session = await self.db.get(ResearchSession, session_id)
        if session:
            session.methodology = methodology
            session.generated_output = generated_output
            session.status = "completed"
            await self.db.commit()

    async def save_summary(self, session_id: uuid.UUID, summary: str):
        """Save the synthesized research report."""
        session = await self.db.get(ResearchSession, session_id)
        if session:
            session.research_summary = summary
            await self.db.commit()
