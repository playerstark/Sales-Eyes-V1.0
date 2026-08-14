"""Deterministic content extraction using BeautifulSoup and Trafilatura."""

import logging
from typing import Optional

from app.services.intelligence.interfaces import ContentExtractor, ProviderException

logger = logging.getLogger(__name__)


class DeterministicExtractor(ContentExtractor):
    """Extract readable text from HTML using Trafilatura + BeautifulSoup.

    Deterministic extraction means:
    - No LLM required
    - Fast, reliable
    - Good fallback when LLM not available
    """

    async def extract(self, url: str, raw_content: str, content_type: str = "text/html") -> str:
        """Extract readable text from raw content.

        Args:
            url: Source URL
            raw_content: Raw HTML or text
            content_type: MIME type

        Returns:
            Cleaned readable text
        """
        try:
            # If not HTML, return as-is
            if "html" not in content_type.lower():
                return raw_content[:5000]  # Cap at 5000 chars for non-HTML

            # Use Trafilatura for HTML extraction
            import trafilatura

            # Extract main text content
            extracted = trafilatura.extract(raw_content, include_comments=False)
            if extracted:
                return extracted[:10000]  # Cap output

            # Fallback to BeautifulSoup if Trafilatura fails
            return self._extract_with_beautifulsoup(raw_content)

        except ImportError:
            logger.warning("trafilatura not installed, falling back to BeautifulSoup")
            return self._extract_with_beautifulsoup(raw_content)
        except Exception as e:
            logger.warning(f"Extraction error for {url}: {e}")
            # Last resort: strip HTML tags
            return self._strip_html_tags(raw_content)

    def _extract_with_beautifulsoup(self, html: str) -> str:
        """Extract text using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text[:10000]  # Cap output

        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed: {e}")
            return self._strip_html_tags(html)

    @staticmethod
    def _strip_html_tags(html: str) -> str:
        """Strip HTML tags (last resort)."""
        import re
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Clean whitespace
        text = re.sub(r"\s+", " ", text)
        return text[:10000]


class EntityPatternExtractor:
    """Extract entities using regex patterns (deterministic)."""

    # Common patterns
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    PHONE_PATTERN = r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
    LINKEDIN_PATTERN = r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)"

    @staticmethod
    def extract_emails(text: str) -> list[str]:
        """Extract email addresses."""
        import re
        matches = re.findall(EntityPatternExtractor.EMAIL_PATTERN, text)
        return list(set(matches))  # Deduplicate

    @staticmethod
    def extract_phones(text: str) -> list[str]:
        """Extract phone numbers."""
        import re
        matches = re.findall(EntityPatternExtractor.PHONE_PATTERN, text)
        return list(set(matches))

    @staticmethod
    def extract_linkedin_urls(text: str) -> list[str]:
        """Extract LinkedIn URLs."""
        import re
        matches = re.findall(
            r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+/?",
            text,
            re.IGNORECASE
        )
        return list(set(matches))

    @staticmethod
    def extract_github_urls(text: str) -> list[str]:
        """Extract GitHub URLs."""
        import re
        matches = re.findall(
            r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?",
            text,
            re.IGNORECASE
        )
        return list(set(matches))

    @staticmethod
    def extract_twitter_handles(text: str) -> list[str]:
        """Extract Twitter handles."""
        import re
        matches = re.findall(r"@[a-zA-Z0-9_]{1,15}", text)
        return list(set(matches))
