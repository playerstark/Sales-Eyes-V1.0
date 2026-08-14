"""DuckDuckGo search provider (free, no API key required)."""

import logging
import asyncio
from typing import Optional

from app.services.intelligence.interfaces import (
    SearchProvider, PageContent, SearchResult,
    TimeoutError, ProviderException, RobotsBlockedError
)
from app.services.intelligence.utils import RobotsChecker, ThrottleManager

logger = logging.getLogger(__name__)


class DuckDuckGoSearchProvider(SearchProvider):
    """DuckDuckGo search provider.

    Free, no API key required. Uses `duckduckgo-search` library.
    """

    def __init__(self, timeout_seconds: int = 10, throttle_delay: float = 0.5):
        self.timeout = timeout_seconds
        self.robots_checker = RobotsChecker()
        self.throttle = ThrottleManager(throttle_delay)
        self._session = None

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Execute DuckDuckGo search.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of SearchResult
        """
        try:
            from duckduckgo_search import DDGS

            logger.info(f"Searching DuckDuckGo for: {query[:100]}")

            # Note: duckduckgo_search is sync; wrap in executor for async
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._do_search,
                query,
                limit
            )
            return results

        except ImportError:
            raise ProviderException(
                "duckduckgo-search not installed. Install with: pip install duckduckgo-search"
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"DuckDuckGo search timed out after {self.timeout}s")
        except Exception as e:
            raise ProviderException(f"DuckDuckGo search error: {e}")

    def _do_search(self, query: str, limit: int) -> list[SearchResult]:
        """Synchronous search (runs in executor)."""
        from duckduckgo_search import DDGS

        results = []
        try:
            with DDGS(timeout=self.timeout) as ddgs:
                # text_search returns: [{"title": ..., "href": ..., "body": ...}, ...]
                for i, result in enumerate(ddgs.text(query, max_results=limit)):
                    results.append(SearchResult(
                        title=result.get("title"),
                        snippet=result.get("body"),
                        url=result.get("href", ""),
                        rank=i
                    ))
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise

        logger.info(f"Got {len(results)} results from DuckDuckGo")
        return results

    async def get_page_content(self, url: str) -> PageContent:
        """Fetch page content.

        Args:
            url: URL to fetch

        Returns:
            PageContent

        Raises:
            RobotsBlockedError: If blocked by robots.txt
            TimeoutError: If request times out
            ProviderException: On other errors
        """
        try:
            # Check robots.txt first
            can_fetch = await self.robots_checker.can_fetch(url)
            if not can_fetch:
                raise RobotsBlockedError(f"robots.txt blocks {url}")

            # Rate limiting
            await self.throttle.wait_for_domain(url)

            logger.info(f"Fetching: {url}")

            # Use httpx for async HTTP
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                    },
                    follow_redirects=True
                )

                # Check for blocked access
                if response.status_code == 403:
                    raise RobotsBlockedError(f"Access denied (403): {url}")
                if response.status_code == 401:
                    from app.services.intelligence.interfaces import LoginRequiredError
                    raise LoginRequiredError(f"Login required (401): {url}")

                # Check for CAPTCHA
                from app.services.intelligence.utils import CaptchaDetector
                if CaptchaDetector.detect_captcha(response.text, url):
                    from app.services.intelligence.interfaces import CaptchaDetectedError
                    raise CaptchaDetectedError(f"CAPTCHA detected at: {url}")

                return PageContent(
                    url=url,
                    title=self._extract_title(response.text),
                    content_type=response.headers.get("content-type", "text/html"),
                    raw_content=response.text,
                    status_code=response.status_code
                )

        except RobotsBlockedError:
            raise
        except TimeoutError:
            raise
        except asyncio.TimeoutError:
            raise TimeoutError(f"Fetch timeout: {url}")
        except Exception as e:
            if "LoginRequiredError" in str(type(e).__name__):
                raise
            if "CaptchaDetectedError" in str(type(e).__name__):
                raise
            logger.error(f"Error fetching {url}: {e}")
            raise ProviderException(f"Failed to fetch {url}: {e}")

    @staticmethod
    def _extract_title(html: str) -> Optional[str]:
        """Extract title from HTML."""
        try:
            import re
            match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None
