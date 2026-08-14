import httpx
import json
import re
from typing import Optional
from datetime import datetime

from app.core.config import settings


class DeepSeekService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.endpoint = endpoint or settings.DEEPSEEK_ENDPOINT
        self.model = model or settings.DEEPSEEK_MODEL

    def _extract_json(self, text: str) -> dict | list:
        """Extract JSON from markdown code blocks or plain JSON."""
        text = re.sub(r'^```(?:json)?\n', '', text)
        text = re.sub(r'\n```$', '', text)
        return json.loads(text.strip())

    async def comprehensive_prospect_research(self, prospect_name: str, prospect_title: str | None, prospect_company: str | None) -> dict:
        """Use DeepSeek to perform comprehensive research on a prospect including news, background, and hooks."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        prompt = f"""You are an expert sales research analyst. Perform comprehensive research on this prospect and return detailed findings in JSON format.

PROSPECT INFORMATION:
- Name: {prospect_name}
- Title: {prospect_title or 'Not provided'}
- Company: {prospect_company or 'Not provided'}

Please research and provide:
1. Professional background and career trajectory
2. Recent news and company updates (with dates)
3. Pain points and challenges (by category/tag)
4. Strategic initiatives and priorities
5. Sales hooks (specific, concrete details to open with)
6. Company intelligence and market position
7. Industry trends affecting this prospect

Return ONLY this JSON structure:
{{
  "prospect_name": "{prospect_name}",
  "professional_background": "Summary of their background and experience",
  "current_role_analysis": "Analysis of their current position and responsibilities",
  "company_overview": "Company information and market position",
  "news_and_updates": [
    {{
      "title": "News headline",
      "date": "YYYY-MM-DD",
      "source": "Source of news",
      "summary": "Brief summary (1-2 sentences)",
      "relevance": "high|medium|low",
      "category": "announcement|product|hiring|partnership|acquisition|earnings|other"
    }}
  ],
  "pain_points": [
    {{
      "category": "Category (e.g., digital transformation, cost reduction, scaling, talent)",
      "issue": "Specific pain point",
      "impact": "Business impact",
      "relevance_score": 0.85
    }}
  ],
  "strategic_priorities": [
    "Priority 1",
    "Priority 2",
    "Priority 3"
  ],
  "sales_hooks": [
    {{
      "hook": "Specific, concrete opening line based on research",
      "based_on": "The specific news or fact this hook is based on",
      "strength": "high|medium",
      "approach": "SPIN|Sandler|Challenger recommendation"
    }}
  ],
  "industry_context": "Relevant industry trends and context",
  "confidence_score": 0.85,
  "research_summary": "Executive summary of all findings (2-3 paragraphs)"
}}"""

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert sales research analyst. Provide comprehensive, factual research. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 3500
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]
                research = self._extract_json(content)
                return research
            except Exception as e:
                raise ValueError(f"DeepSeek API error: {str(e)}")

    async def parse_prospect_details(self, prospect_input: str) -> dict:
        """Extract structured name/company/title from freeform prospect text."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        prompt = f"""Extract the prospect's name, company, and job title from this text. If a field truly isn't present, use null — never guess or invent one.

Text:
{prospect_input}

Return ONLY this JSON:
{{
  "name": "Full Name or null",
  "company": "Company Name or null",
  "title": "Job Title or null"
}}"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Extract structured data. Return only valid JSON, no invented facts."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._extract_json(content)

    async def summarize_research(
        self,
        prospect_name: str | None,
        prospect_title: str | None,
        prospect_company: str | None,
        research_data: dict,
    ) -> str:
        """Generate a polished research report from the comprehensive research data."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        display_name = prospect_name or "the prospect"

        # Format news with dates
        news_section = ""
        if research_data.get("news_and_updates"):
            news_items = research_data["news_and_updates"]
            news_section = "**Recent News & Company Updates:**\n"
            for item in news_items:
                date = item.get("date", "Date unknown")
                title = item.get("title", "Untitled")
                category = item.get("category", "update").upper()
                news_section += f"- [{date}] {category}: {title} - {item.get('summary', '')}\n"

        # Format pain points with tags
        pain_section = ""
        if research_data.get("pain_points"):
            pain_section = "**Key Pain Points & Challenges:**\n"
            for pain in research_data["pain_points"]:
                category = pain.get("category", "General").upper()
                pain_section += f"- [{category}] {pain.get('issue', '')} (Impact: {pain.get('impact', '')})\n"

        # Format hooks
        hooks_section = ""
        if research_data.get("sales_hooks"):
            hooks_section = "**Opening Hooks:**\n"
            for hook in research_data["sales_hooks"]:
                strength = hook.get("strength", "medium").upper()
                approach = hook.get("approach", "General")
                hooks_section += f"- [{strength} | {approach}] {hook.get('hook', '')} (Based on: {hook.get('based_on', '')})\n"

        prompt = f"""Write a professional, concise research report for {display_name}{f", {prospect_title}" if prospect_title else ""}{f" at {prospect_company}" if prospect_company else ""}.

Use this research data:

Professional Background: {research_data.get('professional_background', 'Not available')}
Current Role: {research_data.get('current_role_analysis', 'Not available')}
Company: {research_data.get('company_overview', 'Not available')}

{news_section}

{pain_section}

{hooks_section}

Strategic Priorities: {', '.join(research_data.get('strategic_priorities', []))}
Industry Context: {research_data.get('industry_context', 'Not available')}

Create a polished research report (250-400 words) with these sections:
1. **Who They Are** - Role, company, and professional context
2. **What's Happening** - Recent news and company developments (reference dates)
3. **Where They're Headed** - Strategic priorities and initiatives
4. **Where The Pain Is** - Key challenges and pain points (organized by category)
5. **Why They'll Listen** - Opening hooks and conversation starters

Be specific. Reference dates and facts. Never invent information not in the source data."""

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a research report writer. Create professional, factual reports. Never fabricate details."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.4,
                        "max_tokens": 1000
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=45.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                raise ValueError(f"DeepSeek API error: {str(e)}")

    FRAMEWORK_GUIDANCE = {
        "spin": """SPIN Selling structure — this is a discovery-led, question-heavy framework:
1. Opening Hook: one or two lines referencing the researched detail, then a bridge into a Situation question.
2. Situation Questions: 1-2 questions establishing their current state (only ask what isn't already known from research — don't ask what you already found).
3. Problem Questions: 1-2 questions surfacing a specific difficulty tied to the researched pain point.
4. Implication Questions: 1-2 questions that make the cost of the problem concrete (time, money, risk).
5. Need-Payoff Questions: 1-2 questions that get the prospect to state the value of solving it themselves.
6. Brief solution bridge connecting to the product, only after the questions.
7. Clear, low-friction CTA.""",
        "sandler": """Sandler Selling structure — this is a trust-first, no-pressure, qualification-led framework:
1. Opening Hook: warm, low-pressure line referencing the researched detail — explicitly lower the stakes (e.g. "not sure if this is even a fit, but...").
2. Bonding & Rapport: one line building rapport without flattery.
3. Pain Funnel: 2-3 progressively deeper questions that get the prospect to articulate their own pain in their own words (surface pain -> real pain -> impact of pain).
4. Budget/Decision Process: one question gauging whether solving this is even a priority worth resourcing (asked respectfully, not pushy).
5. Up-Front Contract: propose what happens next only if it's a mutual fit, explicitly giving them an easy out.
6. No hard close — the CTA should feel like a mutual next step, not a pitch.""",
        "challenger": """Challenger Sale structure — this is an insight-led, teach-tailor-take-control framework:
1. Opening Hook / Commercial Insight: lead with a sharp, specific insight or reframe about their industry or situation, grounded in the researched detail — something that challenges their current thinking, not a compliment or generic observation.
2. Tailor: connect that insight directly to something specific about their company/role from the research.
3. Constructive Tension: name the cost of not acting on the insight, directly and confidently.
4. Take Control: firmly but respectfully propose the specific next step (not overly deferential).
5. Tie the product to the insight, not the other way around.
6. Confident, direct CTA — Challenger reps lead, they don't just ask.""",
    }

    def _resolve_framework(self, methodology: str) -> tuple[str, str]:
        key = (methodology or "").strip().lower()
        if key in self.FRAMEWORK_GUIDANCE:
            return key, self.FRAMEWORK_GUIDANCE[key]
        return "custom", f"Custom approach requested by the user: {methodology}"

    async def generate_sales_script(
        self,
        research_data: dict,
        methodology: str,
        prospect_name: str | None = None,
        prospect_title: str | None = None,
        prospect_company: str | None = None,
        product_context: str | None = None,
        research_summary: str | None = None,
    ) -> str:
        """Generate a personalized sales script grounded in research and product material."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        _, framework_guidance = self._resolve_framework(methodology)
        display_name = prospect_name or "the prospect"

        # Build research document from structured research data
        research_document = research_summary or self._build_research_document(research_data)
        product_document = product_context or "No product material was provided — keep the value proposition generic and clearly flagged as a placeholder to fill in."

        prompt = f"""Write a complete, ready-to-use sales outreach script for {display_name}{f", {prospect_title}" if prospect_title else ""}{f" at {prospect_company}" if prospect_company else ""}.

You are given a research report and product material. Use each for its stated purpose.

RESEARCH REPORT ON {display_name.upper()}
{research_document}

PRODUCT / COMPANY MATERIAL
{product_document}

REQUESTED SCRIPT TYPE: {methodology}
{framework_guidance}

HARD REQUIREMENTS:
1. Address {display_name} by first name at least once, naturally.
2. The opening hook MUST cite a specific, concrete detail from the research — not generic. Reference dates and facts.
3. Follow the {methodology} structure above precisely.
4. Ground every product claim strictly in the product material — never fabricate capabilities.
5. Natural, conversational language — no corporate jargon.
6. Output the script only, with clear section labels matching the requested methodology."""

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert B2B sales writer. Follow the requested script structure precisely. Ground the hook in specific research details."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1800
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=45.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                raise ValueError(f"DeepSeek API error: {str(e)}")

    def _build_research_document(self, research_data: dict) -> str:
        """Build a formatted research document from structured research data."""
        doc = []

        doc.append(f"**Prospect:** {research_data.get('prospect_name', 'Unknown')}")
        doc.append(f"**Background:** {research_data.get('professional_background', 'Not available')}")
        doc.append(f"**Current Role:** {research_data.get('current_role_analysis', 'Not available')}")
        doc.append(f"**Company:** {research_data.get('company_overview', 'Not available')}")
        doc.append("")

        if research_data.get("news_and_updates"):
            doc.append("**Recent News & Updates:**")
            for item in research_data["news_and_updates"]:
                date = item.get("date", "Date unknown")
                title = item.get("title", "Untitled")
                doc.append(f"- [{date}] {title}: {item.get('summary', '')}")
            doc.append("")

        if research_data.get("pain_points"):
            doc.append("**Key Challenges:**")
            for pain in research_data["pain_points"]:
                category = pain.get("category", "General")
                doc.append(f"- [{category}] {pain.get('issue', '')}")
            doc.append("")

        if research_data.get("strategic_priorities"):
            doc.append("**Strategic Priorities:**")
            for priority in research_data["strategic_priorities"]:
                doc.append(f"- {priority}")
            doc.append("")

        if research_data.get("sales_hooks"):
            doc.append("**Opening Hooks:**")
            for hook in research_data["sales_hooks"]:
                doc.append(f"- {hook.get('hook', '')}")

        return "\n".join(doc)
