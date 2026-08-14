import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.research import ResearchSession, PlanStep, Finding
from app.services.linkedin_service import LinkedInService
from app.services.newsapi_service import NewsAPIService
from app.services.deepseek_service import DeepSeekService
from app.services.intelligence.providers.duckduckgo_search import DuckDuckGoSearchProvider
from app.services.intelligence.providers.page_fetcher import SafePageFetcher
from app.services.intelligence.providers.deterministic_extraction import DeterministicExtractor
from app.services.intelligence.interfaces import ProviderException
from app.core.config import settings

logger = logging.getLogger(__name__)


def prospect_snippet(text: str, length: int = 100) -> str:
    return (text or "")[:length]


class PlanExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.linkedin_service = LinkedInService()
        self.news_service = NewsAPIService(api_key=settings.NEWSAPI_KEY)
        self.deepseek_service = DeepSeekService()

        # Public web search stack — free, no API key required. Only ever
        # touches publicly reachable pages (robots.txt respected, no
        # CAPTCHA/login bypass) via the same providers used by the
        # Prospect Intelligence module.
        self.search_provider = DuckDuckGoSearchProvider()
        self.page_fetcher = SafePageFetcher(self.search_provider)
        self.content_extractor = DeterministicExtractor()

    async def execute_plan(self, session_id: uuid.UUID) -> dict:
        """Execute all plan steps for a session."""
        session = await self.db.get(ResearchSession, session_id)
        if not session:
            raise ValueError("Session not found")

        plan_steps = await self._get_plan_steps(session_id)
        results = {"executed_steps": 0, "findings_created": 0, "errors": []}

        for step in plan_steps:
            try:
                await self._execute_step(session_id, step, session)
                results["executed_steps"] += 1
            except Exception as e:
                logger.exception(f"Step {step.agent_type} failed")
                results["errors"].append({"step": step.agent_type, "error": str(e)})

        session.status = "completed"
        await self.db.commit()

        return results

    async def _get_plan_steps(self, session_id: uuid.UUID) -> list[PlanStep]:
        result = await self.db.execute(
            select(PlanStep).where(PlanStep.session_id == session_id).order_by(PlanStep.step_order)
        )
        return result.scalars().all()

    async def _execute_step(self, session_id: uuid.UUID, step: PlanStep, session: ResearchSession):
        step.status = "in_progress"
        await self.db.commit()

        agent_type = step.agent_type.lower()

        if "linkedin" in agent_type or "profile" in agent_type:
            await self._execute_linkedin_search(session_id, step, session)
        elif "news" in agent_type or "recent" in agent_type:
            await self._execute_news_search(session_id, step, session)
        elif "pain" in agent_type or "opportunity" in agent_type:
            await self._execute_pain_point_analysis(session_id, step, session)
        elif "company" in agent_type or "intelligence" in agent_type or "competitive" in agent_type:
            await self._execute_web_research(session_id, step, session, focus="company")
        else:
            await self._execute_web_research(session_id, step, session, focus="general")

        step.status = "completed"
        await self.db.commit()

    # ------------------------------------------------------------------
    # Web research (real public search, not a stub)
    # ------------------------------------------------------------------

    async def _execute_web_research(
        self, session_id: uuid.UUID, step: PlanStep, session: ResearchSession, focus: str
    ):
        """Search the public web for the prospect/company and turn the
        results into findings. Falls back to a plain note if search is
        unavailable (e.g. offline dev environment)."""
        name = session.prospect_name
        company = session.prospect_company

        query = self._build_query(name, company, session.prospect_input, focus)

        try:
            results = await self.search_provider.search(query, limit=5)
        except ProviderException as e:
            logger.warning(f"Web search unavailable ({e}); falling back to raw prospect input")
            await self._create_finding(
                session_id, step.id, "research",
                f"{step.description}: web search unavailable ({e}). "
                f"Using provided details only: {prospect_snippet(session.prospect_input)}",
                None, {"query": query}
            )
            return

        if not results:
            await self._create_finding(
                session_id, step.id, "research",
                f'No public web results found for "{query}".',
                None, {"query": query}
            )
            return

        created = 0
        web_summaries = []
        for result in results[:5]:
            if not result.url:
                continue
            summary = result.snippet or result.title or "No summary available"
            web_summaries.append(f"- {result.title or result.url}: {summary}")
            await self._create_finding(
                session_id, step.id,
                "web_presence" if focus == "general" else "company_info",
                f"{result.title or result.url}: {summary[:220]}",
                result.url,
                {"query": query, "title": result.title, "snippet": result.snippet},
            )
            created += 1

        # Try to enrich the single most relevant result with actual page
        # content — best effort, never blocks the rest of the pipeline if
        # it fails, is blocked by robots.txt, or times out.
        top_url = results[0].url
        try:
            if await self.page_fetcher.can_fetch(top_url):
                page = await self.page_fetcher.fetch_safe(top_url)
                text = await self.content_extractor.extract(top_url, page.raw_content, page.content_type)
                if text and len(text) > 40:
                    await self._create_finding(
                        session_id, step.id, "web_detail",
                        f"Details from {page.title or top_url}: {text[:300]}",
                        top_url,
                        {"query": query},
                    )
                    web_summaries.append(f"- Detailed page content from {page.title or top_url}: {text[:200]}")
        except ProviderException as e:
            logger.info(f"Skipping detail fetch for {top_url}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching detail page {top_url}: {e}")

        # Now use DeepSeek to perform deep analysis on the collected web findings
        if web_summaries and focus == "company":
            try:
                web_context = "\n".join(web_summaries)
                deep_analysis = await self.deepseek_service.deep_research_prospect(
                    prospect_name=name or "Unknown",
                    prospect_title=session.prospect_title,
                    prospect_company=company or "Unknown",
                    web_findings=web_context
                )
                await self._create_finding(
                    session_id, step.id, "deep_analysis",
                    f"AI-Powered Research Analysis:\n\n{deep_analysis}",
                    None, {"query": query, "analysis_type": "deepseek_synthesis"}
                )
                logger.info(f"Deep research analysis completed for: {name}")
            except Exception as e:
                logger.warning(f"Deep research analysis failed: {e}")

        logger.info(f"Web research created {created} findings for query: {query}")

    async def _execute_linkedin_search(self, session_id: uuid.UUID, step: PlanStep, session: ResearchSession):
        """Look up a LinkedIn profile — either from a URL already present in
        the prospect input, or by searching for one on the public web."""
        prospect_input = session.prospect_input
        try:
            linkedin_url = self._extract_linkedin_url(prospect_input)

            if linkedin_url:
                result = await self.linkedin_service.search_and_enrich(linkedin_url)
                if result.get("success"):
                    data = result.get("enriched_data", {})
                    summary = f"LinkedIn Profile: {data.get('name', 'Unknown')} - {data.get('headline', '')}"
                    await self._create_finding(
                        session_id, step.id, "profile_data", summary,
                        linkedin_url, data
                    )
                    return

            # No URL given (or enrichment failed) — search publicly for a
            # LinkedIn profile matching the name/company instead of
            # silently giving up.
            query = self._build_query(session.prospect_name, session.prospect_company, prospect_input, "linkedin")
            results = await self.search_provider.search(query, limit=3)
            linkedin_results = [r for r in results if "linkedin.com/in" in (r.url or "")]

            if linkedin_results:
                for r in linkedin_results[:2]:
                    await self._create_finding(
                        session_id, step.id, "profile_data",
                        f"Possible LinkedIn match: {r.title or r.url} — {(r.snippet or '')[:180]}",
                        r.url, {"query": query}
                    )
            else:
                await self._create_finding(
                    session_id, step.id, "profile_data",
                    "No public LinkedIn profile could be confidently identified. "
                    "Review manually if a LinkedIn profile is needed.",
                    None, {"query": query}
                )
        except Exception as e:
            summary = f"Unable to fetch LinkedIn data: {str(e)}"
            await self._create_finding(
                session_id, step.id, "error", summary, None, {}
            )

    async def _execute_news_search(self, session_id: uuid.UUID, step: PlanStep, session: ResearchSession):
        """Search recent news about the prospect's company."""
        try:
            company_name = session.prospect_company or session.prospect_input.split('\n')[0]
            news_data = await self.news_service.get_company_news(company_name)
            articles = news_data.get("articles", [])

            if not articles:
                # NewsAPIService swallows its own errors (missing key, rate limit,
                # no results) and returns an empty list rather than raising, so
                # this branch — not the except below — is what actually fires in
                # practice. Without it the step completes with zero trace.
                reason = news_data.get("error")
                summary = (
                    f"No recent news found for {company_name}"
                    + (f" ({reason})" if reason else "")
                )
                await self._create_finding(
                    session_id, step.id, "news_summary", summary, None,
                    {"company_name": company_name}
                )
                return

            for article in articles[:3]:
                title = article.get("title") or "Untitled article"
                description = article.get("description") or ""
                summary = f"{title}: {description[:200]}"
                await self._create_finding(
                    session_id, step.id, "news", summary,
                    article.get("url"), article
                )
        except Exception as e:
            summary = f"News search failed: {str(e)}"
            await self._create_finding(
                session_id, step.id, "news_summary", summary, None, {}
            )

    async def _execute_pain_point_analysis(self, session_id: uuid.UUID, step: PlanStep, session: ResearchSession):
        """Use DeepSeek to identify pain points and opportunities for the prospect."""
        try:
            prospect_info = f"{session.prospect_name or 'Unknown'}, {session.prospect_title or ''} at {session.prospect_company or ''}"
            company_info = session.prospect_company or "Company unknown"
            industry_context = f"Prospect works at {session.prospect_company}. Role: {session.prospect_title}"

            opportunities = await self.deepseek_service.identify_opportunities(
                prospect_info=prospect_info,
                company_info=company_info,
                industry_context=industry_context
            )

            if opportunities:
                for opp in opportunities[:3]:
                    summary = f"**{opp.get('opportunity_type', 'Opportunity').upper()}**: {opp.get('description', '')}\nImpact: {opp.get('impact', '')}\nUrgency: {opp.get('urgency', 'medium')}"
                    await self._create_finding(
                        session_id, step.id, "opportunity",
                        summary,
                        None, opp
                    )
            else:
                await self._create_finding(
                    session_id, step.id, "opportunity",
                    "Unable to identify specific opportunities from available data.",
                    None, {}
                )
        except Exception as e:
            logger.warning(f"Pain point analysis failed: {e}")
            await self._create_finding(
                session_id, step.id, "opportunity",
                f"Pain point analysis encountered an error: {str(e)}",
                None, {}
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_linkedin_url(text: str) -> str | None:
        match = re.search(r"https?://(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", text)
        return match.group(0) if match else None

    @staticmethod
    def _build_query(name: str | None, company: str | None, raw_input: str, focus: str) -> str:
        if name and company:
            base = f'"{name}" "{company}"'
        elif name:
            base = f'"{name}"'
        elif company:
            base = f'"{company}"'
        else:
            base = prospect_snippet(raw_input, 80)

        if focus == "linkedin":
            return f"{base} site:linkedin.com"
        if focus == "company":
            return f"{base} company overview"
        return base

    async def _create_finding(
        self,
        session_id: uuid.UUID,
        step_id: uuid.UUID,
        finding_type: str,
        summary: str,
        source_link: str | None,
        raw_data: dict
    ):
        finding = Finding(
            session_id=session_id,
            plan_step_id=step_id,
            finding_type=finding_type,
            source_link=source_link,
            source_header=finding_type.replace("_", " ").title(),
            summary=summary,
            confidence_score=0.75 if source_link else 0.5,
            relevancy_score=0.8,
            raw_data=raw_data,
            source_type="internet" if source_link else "research_agent",
            source_reference=source_link,
        )
        self.db.add(finding)
        await self.db.commit()
