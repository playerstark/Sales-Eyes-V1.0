"""Page fetcher with safety checks."""

import logging
from typing import Optional

from app.services.intelligence.interfaces import (
    PageFetcher, PageContent, SearchProvider,
    RobotsBlockedError, LoginRequiredError, CaptchaDetectedError, TimeoutError, ProviderException
)
from app.services.intelligence.utils import RobotsChecker, CaptchaDetector, LoginDetector

logger = logging.getLogger(__name__)


class SafePageFetcher(PageFetcher):
    """Fetch pages with robots.txt, login, and CAPTCHA checks."""

    def __init__(self, search_provider: SearchProvider, timeout_seconds: int = 10):
        self.search_provider = search_provider
        self.timeout = timeout_seconds
        self.robots_checker = RobotsChecker()

    async def fetch_safe(self, url: str, timeout_seconds: int = 10) -> PageContent:
        """Fetch page with safety checks.

        Args:
            url: URL to fetch
            timeout_seconds: Request timeout

        Returns:
            PageContent

        Raises:
            RobotsBlockedError: If robots.txt blocks URL
            LoginRequiredError: If login required
            CaptchaDetectedError: If CAPTCHA detected
            TimeoutError: If timeout
            ProviderException: On other errors
        """
        logger.info(f"Fetching (safe): {url}")

        try:
            # Check robots.txt
            can_fetch = await self.robots_checker.can_fetch(url)
            if not can_fetch:
                raise RobotsBlockedError(f"robots.txt blocks: {url}")

            # Use search provider's get_page_content
            content = await self.search_provider.get_page_content(url)

            # Check for login page
            if LoginDetector.detect_login_required(content.raw_content, content.status_code):
                raise LoginRequiredError(f"Login required: {url}")

            # Check for CAPTCHA
            if CaptchaDetector.detect_captcha(content.raw_content, url):
                raise CaptchaDetectedError(f"CAPTCHA detected: {url}")

            logger.info(f"Successfully fetched: {url} ({len(content.raw_content)} bytes)")
            return content

        except (RobotsBlockedError, LoginRequiredError, CaptchaDetectedError, TimeoutError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise ProviderException(f"Failed to fetch {url}: {e}")

    async def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched.

        Args:
            url: URL to check

        Returns:
            True if can fetch, False if blocked
        """
        try:
            can_fetch = await self.robots_checker.can_fetch(url)
            return can_fetch
        except Exception as e:
            logger.warning(f"Error checking if can fetch {url}: {e}")
            # Default to allow if error
            return True
