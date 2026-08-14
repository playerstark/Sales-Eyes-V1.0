"""Utilities for intelligence service."""

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Optional

logger = logging.getLogger(__name__)


class URLNormalizer:
    """Normalize and validate URLs."""

    @staticmethod
    def normalize(url: str) -> str:
        """Normalize URL for deduplication.

        - Lowercase
        - Remove fragment
        - Remove trailing slash
        """
        parsed = urlparse(url)
        # Rebuild without fragment, lowercase
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
        if parsed.query:
            normalized += f"?{parsed.query}"
        # Remove trailing slash from path (but not for root)
        if normalized.endswith("/") and normalized.count("/") > 2:
            normalized = normalized.rstrip("/")
        return normalized

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")


class RobotsChecker:
    """Check robots.txt rules (with caching)."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, RobotFileParser] = {}

    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt.

        Args:
            url: URL to check
            user_agent: User-Agent to check rules for

        Returns:
            True if can fetch, False if blocked by robots.txt
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            # Get or create robots parser for this domain
            if domain not in self._cache:
                self._cache[domain] = RobotFileParser()
                robots_url = f"{domain}/robots.txt"
                try:
                    # Fetch robots.txt (with timeout)
                    self._cache[domain].set_url(robots_url)
                    self._cache[domain].read()  # Blocking, but unavoidable
                except Exception as e:
                    # If robots.txt fetch fails, assume fetch is allowed
                    logger.debug(f"Could not fetch robots.txt for {domain}: {e}")
                    return True

            # Check if URL is allowed
            allowed = self._cache[domain].can_fetch(user_agent, url)
            if not allowed:
                logger.warning(f"robots.txt blocks {url} for {user_agent}")
            return allowed

        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # Default to allow if error (fail open)
            return True


class CaptchaDetector:
    """Detect common CAPTCHA patterns in HTML."""

    CAPTCHA_INDICATORS = [
        "recaptcha",
        "hcaptcha",
        "g-recaptcha",
        "captcha",
        "cloudflare",
        "challenge",
        "access_denied",
        "please_verify",
    ]

    @staticmethod
    def detect_captcha(html: str, url: str = "") -> bool:
        """Detect CAPTCHA in HTML content.

        Args:
            html: HTML content
            url: URL (for context)

        Returns:
            True if CAPTCHA likely present
        """
        lower_html = html.lower()
        lower_url = url.lower()

        # Check for common CAPTCHA indicators in HTML
        for indicator in CaptchaDetector.CAPTCHA_INDICATORS:
            if indicator in lower_html:
                return True

        # Check for short/empty content (sign of CAPTCHA page)
        if len(html) < 500 and "verify" in lower_html:
            return True

        return False


class LoginDetector:
    """Detect if page requires authentication."""

    LOGIN_INDICATORS = [
        "login",
        "sign in",
        "sign up",
        "register",
        "authenticate",
        "unauthorized",
        "forbidden",
        "403",
        "401",
    ]

    @staticmethod
    def detect_login_required(html: str, status_code: int = 200) -> bool:
        """Detect if page requires login.

        Args:
            html: HTML content
            status_code: HTTP status code

        Returns:
            True if login likely required
        """
        # 401/403 always mean login required
        if status_code in (401, 403):
            return True

        lower_html = html.lower()
        for indicator in LoginDetector.LOGIN_INDICATORS:
            if indicator in lower_html and "form" in lower_html:
                return True

        return False


class ThrottleManager:
    """Rate limiting for requests."""

    def __init__(self, min_delay_seconds: float = 0.5):
        self.min_delay = min_delay_seconds
        self._last_fetch_time: dict[str, float] = {}

    async def wait_for_domain(self, url: str) -> None:
        """Wait before fetching from domain (rate limiting).

        Args:
            url: URL to fetch
        """
        import asyncio
        from time import time

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain in self._last_fetch_time:
            elapsed = time() - self._last_fetch_time[domain]
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)

        self._last_fetch_time[domain] = time()


class ResponseValidator:
    """Validate HTTP responses."""

    @staticmethod
    def is_valid_html(content: str, content_type: str = "text/html") -> bool:
        """Check if content appears to be valid HTML.

        Args:
            content: Response content
            content_type: MIME type

        Returns:
            True if appears to be valid HTML
        """
        if "html" not in content_type.lower():
            return True  # Not HTML, assume valid

        # Must have some HTML tags
        return "<" in content and ">" in content

    @staticmethod
    def is_error_page(content: str, status_code: int) -> bool:
        """Check if content is an error page.

        Args:
            content: Response content
            status_code: HTTP status code

        Returns:
            True if appears to be error page
        """
        if status_code >= 400:
            return True

        lower_content = content.lower()
        error_patterns = ["404", "error", "not found", "page not available", "temporarily unavailable"]
        return any(p in lower_content for p in error_patterns)
