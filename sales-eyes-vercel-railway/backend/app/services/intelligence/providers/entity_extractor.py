"""Entity extraction implementations."""

import logging
from typing import Optional
import json

from app.services.intelligence.interfaces import EntityExtractor, ExtractedEntity
from app.services.intelligence.providers.deterministic_extraction import EntityPatternExtractor

logger = logging.getLogger(__name__)


class DeterministicEntityExtractor(EntityExtractor):
    """Extract entities using patterns and simple heuristics (no LLM)."""

    async def extract_person(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        """Extract person from text using patterns."""
        if not text or len(text) < 10:
            return None

        try:
            # Extract contact info
            emails = EntityPatternExtractor.extract_emails(text)
            phones = EntityPatternExtractor.extract_phones(text)
            linkedin_urls = EntityPatternExtractor.extract_linkedin_urls(text)
            github_urls = EntityPatternExtractor.extract_github_urls(text)
            twitter_handles = EntityPatternExtractor.extract_twitter_handles(text)

            # Extract names from content (heuristic: look for capitalized words at start)
            names = self._extract_names(text)
            full_name = names[0] if names else None

            # Extract job titles (heuristic: look for common title keywords)
            titles = self._extract_titles(text)
            title = titles[0] if titles else None

            # Extract company names (heuristic: look after "at", "works at", etc.)
            companies = self._extract_companies(text)
            company = companies[0] if companies else None

            # Location heuristics (after "in", "based in", etc.)
            location = self._extract_location(text)

            # If we found at least some information, return entity
            if full_name or title or company or emails or linkedin_urls:
                return ExtractedEntity(
                    entity_type="person",
                    full_name=full_name,
                    first_name=self._split_name(full_name)[0] if full_name else None,
                    last_name=self._split_name(full_name)[1] if full_name else None,
                    title=title,
                    company=company,
                    location=location,
                    email=emails[0] if emails else None,
                    phone=phones[0] if phones else None,
                    linkedin_url=linkedin_urls[0] if linkedin_urls else None,
                    skills=[],
                    employment_history=[],
                    education=[],
                    social_profiles={
                        "github": github_urls[0] if github_urls else None,
                        "twitter": twitter_handles[0] if twitter_handles else None,
                    },
                    raw_text=text[:1000]
                )

            return None

        except Exception as e:
            logger.warning(f"Error extracting person: {e}")
            return None

    async def extract_company(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        """Extract company from text."""
        if not text or len(text) < 10:
            return None

        try:
            # Look for company indicators
            companies = self._extract_companies(text)
            company_name = companies[0] if companies else None

            if company_name:
                return ExtractedEntity(
                    entity_type="company",
                    full_name=company_name,
                    title=None,
                    company=company_name,
                    location=self._extract_location(text),
                    email=None,
                    phone=None,
                    linkedin_url=None,
                    skills=[],
                    employment_history=[],
                    education=[],
                    social_profiles={},
                    raw_text=text[:500]
                )

            return None

        except Exception as e:
            logger.warning(f"Error extracting company: {e}")
            return None

    @staticmethod
    def _extract_names(text: str) -> list[str]:
        """Extract potential names from text."""
        # Simple heuristic: look for capitalized words
        import re
        # Match sequences of capitalized words
        matches = re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b", text)
        # Filter short names
        return [m for m in matches if len(m) > 3][:5]  # Top 5

    @staticmethod
    def _extract_titles(text: str) -> list[str]:
        """Extract job titles."""
        titles = [
            "CEO", "CTO", "CFO", "COO",
            "Vice President", "VP", "SVP",
            "Director", "Manager", "Lead",
            "Engineer", "Developer", "Architect",
            "Sales Representative", "Account Executive",
            "Product Manager", "Designer", "Data Scientist",
        ]

        found_titles = []
        text_lower = text.lower()
        for title in titles:
            if title.lower() in text_lower:
                found_titles.append(title)

        return found_titles

    @staticmethod
    def _extract_companies(text: str) -> list[str]:
        """Extract company names (heuristic)."""
        import re
        # Look after "at", "works at", "company", etc.
        pattern = r"(?:at|works at|company|company:)\s+([A-Z][a-zA-Z0-9\s&.,]*)"
        matches = re.findall(pattern, text)
        companies = [m.strip() for m in matches if m.strip()]
        return companies[:5]

    @staticmethod
    def _extract_location(text: str) -> Optional[str]:
        """Extract location (heuristic)."""
        import re
        # Look after "in", "based in", "located in"
        pattern = r"(?:in|based in|located in)\s+([A-Za-z\s,]+?)(?:\.|,|and|\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            if len(location) < 100:  # Sanity check
                return location
        return None

    @staticmethod
    def _split_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Split name into first and last."""
        if not full_name:
            return None, None

        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        elif len(parts) == 1:
            return parts[0], None
        return None, None
