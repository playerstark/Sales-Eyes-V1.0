"""Abstract provider interfaces for swappable implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# =========================================
# Data Structures
# =========================================

@dataclass
class SearchResult:
    """Single search result."""
    title: Optional[str]
    snippet: Optional[str]
    url: str
    rank: int  # Position in result set (0-based)


@dataclass
class PageContent:
    """Fetched page content."""
    url: str
    title: Optional[str]
    content_type: str  # text/html, application/pdf, etc.
    raw_content: str  # Raw HTML/text
    status_code: int


@dataclass
class ExtractedEntity:
    """Extracted entity from content."""
    entity_type: str  # person | company | organization
    full_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    linkedin_url: Optional[str]
    skills: list[str]
    employment_history: list[dict]  # [{company, title, start_date, end_date}, ...]
    education: list[dict]  # [{school, degree, field, year}, ...]
    social_profiles: dict  # {github, twitter, etc.}
    raw_text: Optional[str]  # Source text used for extraction


# =========================================
# Exceptions
# =========================================

class ProviderException(Exception):
    """Base exception for provider errors."""
    pass


class RobotsBlockedError(ProviderException):
    """Attempted access to robots.txt-blocked URL."""
    pass


class CaptchaDetectedError(ProviderException):
    """CAPTCHA detected; cannot proceed."""
    pass


class LoginRequiredError(ProviderException):
    """Page requires authentication."""
    pass


class TimeoutError(ProviderException):
    """Request timeout."""
    pass


class InvalidProviderError(ProviderException):
    """Provider misconfiguration."""
    pass


# =========================================
# Abstract Provider Interfaces
# =========================================

class SearchProvider(ABC):
    """Search provider interface.

    Implementations must:
    - Respect robots.txt
    - Fail gracefully on blocked access
    - Return only public results
    - Not attempt to bypass access controls
    """

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Execute a search query.

        Args:
            query: Search query string
            limit: Max results to return

        Returns:
            List of SearchResult, sorted by relevance

        Raises:
            RobotsBlockedError: If provider is blocked by robots.txt
            ProviderException: On network errors, timeouts, etc.
        """
        pass

    @abstractmethod
    async def get_page_content(self, url: str) -> PageContent:
        """Fetch full page content.

        Args:
            url: URL to fetch

        Returns:
            PageContent with raw HTML/text

        Raises:
            RobotsBlockedError: If URL is blocked by robots.txt
            LoginRequiredError: If page requires authentication
            CaptchaDetectedError: If CAPTCHA detected
            TimeoutError: If request times out
            ProviderException: On network errors
        """
        pass


class ContentExtractor(ABC):
    """Content extraction from raw HTML/text.

    Extracts readable text from web pages.
    Implementations should handle:
    - HTML cleaning
    - Boilerplate removal
    - Readability optimization
    """

    @abstractmethod
    async def extract(self, url: str, raw_content: str, content_type: str = "text/html") -> str:
        """Extract readable text from raw page content.

        Args:
            url: Source URL (context)
            raw_content: Raw HTML or text
            content_type: MIME type (text/html, application/pdf, etc.)

        Returns:
            Cleaned, readable text
        """
        pass


class EntityExtractor(ABC):
    """Extract structured entities from text.

    Implementations should:
    - Be deterministic when possible
    - Populate only verified fields (use None for unverified)
    - Return confidence scores
    """

    @abstractmethod
    async def extract_person(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        """Extract person entity from text.

        Args:
            text: Source text to extract from
            context_url: Optional URL context (LinkedIn, company site, etc.)

        Returns:
            ExtractedEntity or None if no person found
        """
        pass

    @abstractmethod
    async def extract_company(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        """Extract company entity from text.

        Args:
            text: Source text
            context_url: Optional URL context

        Returns:
            ExtractedEntity or None if no company found
        """
        pass


class LLMProvider(ABC):
    """LLM provider for text processing tasks.

    Used when deterministic extraction isn't sufficient.
    """

    @abstractmethod
    async def extract_entities_from_text(
        self,
        text: str,
        entity_type: str = "person",  # person | company
        context_url: Optional[str] = None
    ) -> Optional[ExtractedEntity]:
        """Use LLM to extract entities from text.

        Args:
            text: Source text
            entity_type: Type of entity to extract
            context_url: Optional URL for context

        Returns:
            ExtractedEntity or None if extraction failed
        """
        pass

    @abstractmethod
    async def generate_research_plan(self, prospect_input: str) -> dict:
        """Generate a research plan for a prospect.

        Args:
            prospect_input: User's freeform prospect description

        Returns:
            Plan dict with search queries and instructions
        """
        pass


class PageFetcher(ABC):
    """Fetches page content with safety checks.

    Combines SearchProvider and robots.txt checking.
    """

    @abstractmethod
    async def fetch_safe(self, url: str, timeout_seconds: int = 10) -> PageContent:
        """Fetch page with safety checks.

        Args:
            url: URL to fetch
            timeout_seconds: Request timeout

        Returns:
            PageContent if successful

        Raises:
            RobotsBlockedError: If robots.txt blocks this URL
            LoginRequiredError: If login required
            CaptchaDetectedError: If CAPTCHA detected
            TimeoutError: If timeout exceeded
            ProviderException: On other errors
        """
        pass

    @abstractmethod
    async def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched (consult robots.txt, etc).

        Args:
            url: URL to check

        Returns:
            True if can fetch, False if blocked
        """
        pass
