"""Prospect Intelligence Agent orchestrator.

Coordinates the entire research pipeline:
Search → Extraction → Identity Resolution → Scoring → Conflict Detection → Verification
"""

import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.intelligence import (
    IntelligenceSession, ResearchQuery, SearchResult, Source, ExtractedEntity as ExtractedEntityModel,
    CandidateIdentity, IdentityScore, Evidence, Conflict
)
from app.services.intelligence.interfaces import (
    SearchProvider, ContentExtractor, EntityExtractor, PageFetcher
)
from app.services.intelligence.identity_resolver import IdentityResolution, IdentityMatcher
from app.services.intelligence.confidence_scorer import ConfidenceScorer
from app.services.intelligence.conflict_detector import ConflictDetector, ConflictResolver
from app.services.intelligence.utils import URLNormalizer

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """Orchestrate prospect intelligence research."""

    def __init__(
        self,
        db: AsyncSession,
        search_provider: SearchProvider,
        content_extractor: ContentExtractor,
        entity_extractor: EntityExtractor,
        page_fetcher: PageFetcher,
    ):
        self.db = db
        self.search = search_provider
        self.extractor = content_extractor
        self.entity_extractor = entity_extractor
        self.fetcher = page_fetcher

        # Sub-services
        self.identity_resolver = IdentityResolution()
        self.identity_matcher = IdentityMatcher()
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()

        self.url_normalizer = URLNormalizer()

    async def research(
        self,
        session_id: uuid.UUID,
        prospect_name: str,
        prospect_company: Optional[str] = None,
        max_queries: int = 5,
        max_pages_per_query: int = 10,
    ) -> dict:
        """Execute full intelligence research pipeline.

        Args:
            session_id: Intelligence session ID
            prospect_name: Prospect name to research
            prospect_company: Optional company name
            max_queries: Max search queries to execute
            max_pages_per_query: Max pages to fetch per query

        Returns:
            Result dict with candidates, scores, conflicts
        """
        logger.info(f"Starting intelligence research for {prospect_name}")

        session = await self.db.get(IntelligenceSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        try:
            # Phase 1: Search
            await self._update_session_status(session_id, "searching", "Searching for prospect information")
            search_results = await self._search_phase(session_id, prospect_name, prospect_company, max_queries)

            if not search_results:
                logger.warning("No search results found")
                await self._update_session_status(session_id, "completed", "No results found")
                return {"candidates": [], "errors": ["No search results found"]}

            # Phase 2: Extract
            await self._update_session_status(session_id, "extracting", "Extracting information from pages")
            extracted_entities = await self._extract_phase(session_id, search_results, max_pages_per_query)

            if not extracted_entities:
                logger.warning("No entities extracted")
                await self._update_session_status(session_id, "completed", "No entities extracted from results")
                return {"candidates": [], "errors": ["No entities extracted from results"]}

            # Phase 3: Resolve
            await self._update_session_status(session_id, "resolving", "Reconciling entities into candidates")
            candidates = await self._resolve_phase(session_id, extracted_entities, search_results)

            # Phase 4: Score
            await self._update_session_status(session_id, "scoring", "Computing confidence scores")
            candidates = await self._score_phase(session_id, candidates, extracted_entities)

            # Phase 5: Detect Conflicts
            await self._update_session_status(session_id, "detecting_conflicts", "Detecting contradictions")
            candidates = await self._conflict_phase(session_id, candidates, extracted_entities)

            # Phase 6: Save to DB
            await self._save_candidates(session_id, candidates)

            await self._update_session_status(session_id, "completed", "Research complete")

            logger.info(f"Research complete: {len(candidates)} candidates found")
            return {
                "session_id": str(session_id),
                "candidates": candidates,
                "total_candidates": len(candidates),
            }

        except Exception as e:
            logger.exception(f"Research error: {e}")
            await self._update_session_status(session_id, "failed", f"Error: {str(e)}")
            raise

    async def _search_phase(
        self,
        session_id: uuid.UUID,
        prospect_name: str,
        prospect_company: Optional[str],
        max_queries: int
    ) -> list[dict]:
        """Search phase: Generate queries and execute searches."""
        queries = self._generate_queries(prospect_name, prospect_company, max_queries)
        results = []

        for query_text in queries:
            logger.info(f"Executing search: {query_text}")

            # Save query to DB
            db_query = ResearchQuery(
                session_id=session_id,
                query_text=query_text,
                search_provider="duckduckgo",
                status="in_progress"
            )
            self.db.add(db_query)
            await self.db.flush()

            try:
                # Execute search
                search_results = await self.search.search(query_text, limit=10)

                # Save results
                for rank, result in enumerate(search_results):
                    db_result = SearchResult(
                        query_id=db_query.id,
                        result_index=rank,
                        title=result.title,
                        snippet=result.snippet,
                        url=result.url
                    )
                    self.db.add(db_result)
                    results.append({
                        "url": result.url,
                        "title": result.title,
                        "snippet": result.snippet,
                        "rank": rank
                    })

                db_query.status = "completed"
                logger.info(f"Got {len(search_results)} results for: {query_text}")

            except Exception as e:
                logger.error(f"Search error for '{query_text}': {e}")
                db_query.status = "failed"

        await self.db.commit()
        return results

    async def _extract_phase(
        self,
        session_id: uuid.UUID,
        search_results: list[dict],
        max_pages: int
    ) -> list[dict]:
        """Extract phase: Fetch pages and extract entities."""
        extracted = []
        fetched_urls = set()
        pages_fetched = 0

        for result in search_results[:max_pages]:
            url = result.get("url")
            if not url or url in fetched_urls:
                continue

            fetched_urls.add(url)
            pages_fetched += 1

            try:
                # Check if can fetch
                can_fetch = await self.fetcher.can_fetch(url)
                if not can_fetch:
                    logger.warning(f"Cannot fetch {url} (robots.txt)")
                    continue

                # Fetch page
                logger.info(f"Fetching: {url}")
                page = await self.fetcher.fetch_safe(url)

                # Extract text
                text = await self.extractor.extract(url, page.raw_content, page.content_type)

                # Save source
                normalized_url = self.url_normalizer.normalize(url)
                db_source = Source(
                    search_result_id=uuid.uuid4(),  # TODO: link properly
                    url=normalized_url,
                    title=page.title,
                    domain=self.url_normalizer.get_domain(url),
                    content_type=page.content_type,
                    raw_content=page.raw_content,
                    extracted_text=text,
                    fetch_status="success"
                )
                self.db.add(db_source)
                await self.db.flush()

                # Extract entities
                person = await self.entity_extractor.extract_person(text, context_url=url)
                if person:
                    extracted.append({
                        "entity": person,
                        "source_url": url,
                        "source_id": str(db_source.id)
                    })
                    logger.info(f"Extracted person: {person.full_name} from {url}")

            except Exception as e:
                logger.warning(f"Extraction error for {url}: {e}")
                # Continue with next URL

        await self.db.commit()
        logger.info(f"Extracted {len(extracted)} entities from {pages_fetched} pages")
        return extracted

    async def _resolve_phase(
        self,
        session_id: uuid.UUID,
        extracted_entities: list[dict],
        search_results: list[dict]
    ) -> list[dict]:
        """Resolve phase: Reconcile entities into candidates."""
        entities = [item["entity"] for item in extracted_entities]
        sources = [item["source_url"] for item in extracted_entities]

        candidates = await self.identity_resolver.resolve_entities(entities, str(session_id))

        # Link evidence for each candidate
        for candidate in candidates:
            evidence = await self.identity_matcher.link_evidence(candidate, entities, sources)
            candidate["evidence"] = evidence

        logger.info(f"Resolved into {len(candidates)} candidates")
        return candidates

    async def _score_phase(
        self,
        session_id: uuid.UUID,
        candidates: list[dict],
        extracted_entities: list[dict]
    ) -> list[dict]:
        """Score phase: Compute confidence for each candidate."""
        entity_dicts = [
            {
                "full_name": e["entity"].full_name,
                "title": e["entity"].title,
                "company": e["entity"].company,
                "location": e["entity"].location,
            }
            for e in extracted_entities
        ]

        for candidate in candidates:
            score_result = await self.confidence_scorer.score_candidate(
                candidate,
                entity_dicts,
                candidate.get("evidence", [])
            )
            candidate["confidence"] = score_result["overall_confidence"]
            candidate["score_details"] = score_result

        logger.info(f"Scored {len(candidates)} candidates")
        return candidates

    async def _conflict_phase(
        self,
        session_id: uuid.UUID,
        candidates: list[dict],
        extracted_entities: list[dict]
    ) -> list[dict]:
        """Conflict phase: Detect and surface contradictions."""
        entity_dicts = [
            {
                "full_name": e["entity"].full_name,
                "title": e["entity"].title,
                "company": e["entity"].company,
                "location": e["entity"].location,
            }
            for e in extracted_entities
        ]

        for candidate in candidates:
            conflicts = await self.conflict_detector.detect_conflicts(
                candidate,
                entity_dicts,
                candidate.get("evidence", [])
            )
            candidate["conflicts"] = conflicts

        logger.info(f"Detected conflicts across {len(candidates)} candidates")
        return candidates

    async def _save_candidates(self, session_id: uuid.UUID, candidates: list[dict]) -> None:
        """Save candidate identities to database."""
        for candidate in candidates:
            # Create candidate identity
            db_candidate = CandidateIdentity(
                session_id=session_id,
                canonical_full_name=candidate.get("full_name", "Unknown"),
                canonical_company=candidate.get("company"),
                canonical_title=candidate.get("title"),
                canonical_location=candidate.get("location"),
                merged_data=candidate,
                verification_status="pending"
            )
            self.db.add(db_candidate)
            await self.db.flush()

            # Create identity score
            score_details = candidate.get("score_details", {})
            db_score = IdentityScore(
                candidate_id=db_candidate.id,
                overall_confidence=round(candidate.get("confidence", 0.0), 2),
                name_match_score=round(score_details.get("component_scores", {}).get("name_match", 0.0), 2),
                company_match_score=round(score_details.get("component_scores", {}).get("company_match", 0.0), 2),
                title_match_score=round(score_details.get("component_scores", {}).get("title_match", 0.0), 2),
                location_match_score=round(score_details.get("component_scores", {}).get("location_match", 0.0), 2),
                employment_history_consistency_score=round(score_details.get("component_scores", {}).get("employment_history_consistency", 0.0), 2),
                cross_source_agreement_score=round(score_details.get("component_scores", {}).get("cross_source_agreement", 0.0), 2),
                scoring_details=score_details
            )
            self.db.add(db_score)

            # Save conflicts
            for conflict in candidate.get("conflicts", []):
                db_conflict = Conflict(
                    candidate_id=db_candidate.id,
                    conflict_type=conflict.get("conflict_type", "field_mismatch"),
                    field_name=conflict.get("field_name", "unknown"),
                    value_a=conflict.get("value_a", ""),
                    value_b=conflict.get("value_b", ""),
                    source_a_url=conflict.get("source_a_url", ""),
                    source_b_url=conflict.get("source_b_url", "")
                )
                self.db.add(db_conflict)

        await self.db.commit()

    @staticmethod
    def _generate_queries(prospect_name: str, company: Optional[str], count: int) -> list[str]:
        """Generate search queries for a prospect."""
        queries = [
            f"{prospect_name}",
            f'"{prospect_name}"',
            f"{prospect_name} site:linkedin.com",
        ]

        if company:
            queries.extend([
                f"{prospect_name} {company}",
                f"{prospect_name} {company} site:linkedin.com",
            ])

        return queries[:count]

    async def _update_session_status(
        self,
        session_id: uuid.UUID,
        status: str,
        step_description: str
    ) -> None:
        """Update session status."""
        session = await self.db.get(IntelligenceSession, session_id)
        if session:
            session.status = status
            session.current_step = step_description
            if status == "searching":
                session.progress_percent = 10
            elif status == "extracting":
                session.progress_percent = 30
            elif status == "resolving":
                session.progress_percent = 50
            elif status == "scoring":
                session.progress_percent = 70
            elif status == "detecting_conflicts":
                session.progress_percent = 90
            elif status == "completed":
                session.progress_percent = 100
            elif status == "failed":
                session.progress_percent = 0

            await self.db.commit()
