# Prospect Intelligence Agent — Provider Documentation

## Overview

The Intelligence Agent uses a provider architecture for swappable implementations of search, content fetching, and entity extraction. This allows switching between free and paid services without changing core logic.

---

## Provider Architecture

### Abstract Interfaces

All providers implement abstract base classes defined in `services/intelligence/interfaces.py`:

#### **SearchProvider**
Searches the web for information about a prospect.

```python
class SearchProvider(ABC):
    async def search(self, query: str, limit: int = 10) -> list[SearchResult]
    async def get_page_content(self, url: str) -> PageContent
```

**Constraints:**
- Must respect `robots.txt`
- Must fail gracefully if blocked
- Cannot bypass CAPTCHAs, login walls, or access controls

#### **ContentExtractor**
Extracts readable text from raw HTML/content.

```python
class ContentExtractor(ABC):
    async def extract(self, url: str, raw_content: str, content_type: str) -> str
```

**Purpose:**
- Remove boilerplate (navigation, ads, sidebars)
- Optimize readability for entity extraction
- Handle different content types (HTML, PDF, text)

#### **EntityExtractor**
Extracts structured person/company information from text.

```python
class EntityExtractor(ABC):
    async def extract_person(self, text: str, context_url: Optional[str]) -> Optional[ExtractedEntity]
    async def extract_company(self, text: str, context_url: Optional[str]) -> Optional[ExtractedEntity]
```

**Key Principle:**
- Never fabricate data
- Use `None` for missing fields, "Unknown" for explicitly missing, `[]` for empty lists
- Always track extraction method and confidence

#### **PageFetcher**
Combines search provider + safety checks.

```python
class PageFetcher(ABC):
    async def fetch_safe(self, url: str, timeout_seconds: int = 10) -> PageContent
    async def can_fetch(self, url: str) -> bool
```

**Safety Checks:**
- robots.txt compliance
- CAPTCHA detection
- Login wall detection
- Rate limiting
- Timeouts

#### **LLMProvider**
Uses LLMs for complex extraction tasks (future).

```python
class LLMProvider(ABC):
    async def extract_entities_from_text(...) -> Optional[ExtractedEntity]
    async def generate_research_plan(prospect_input: str) -> dict
```

---

## Implemented Providers

### 1. DuckDuckGo Search Provider

**Module:** `services/intelligence/providers/duckduckgo_search.py`  
**Class:** `DuckDuckGoSearchProvider`

**Features:**
- Free, no API key required
- Uses `duckduckgo-search` Python library
- Respects robots.txt
- Detects and rejects access blocks

**Configuration:**
```python
from app.services.intelligence.providers.duckduckgo_search import DuckDuckGoSearchProvider

provider = DuckDuckGoSearchProvider(
    timeout_seconds=10,
    throttle_delay=0.5  # 500ms between domain requests
)

# Search
results = await provider.search("John Doe VP Sales", limit=10)

# Fetch page
page = await provider.get_page_content("https://linkedin.com/in/johndoe")
```

**Dependencies:**
```bash
pip install duckduckgo-search httpx
```

**Limitations:**
- No advanced search operators
- Rate limited by DuckDuckGo
- May be blocked if overused

---

### 2. Deterministic Content Extractor

**Module:** `services/intelligence/providers/deterministic_extraction.py`  
**Class:** `DeterministicExtractor`

**Features:**
- Uses Trafilatura for HTML extraction (or BeautifulSoup fallback)
- No LLM required
- Fast and reliable
- Removes boilerplate automatically

**Usage:**
```python
from app.services.intelligence.providers.deterministic_extraction import DeterministicExtractor

extractor = DeterministicExtractor()

# Extract text from HTML
text = await extractor.extract(
    url="https://company.com/team",
    raw_content=html_content,
    content_type="text/html"
)
```

**Dependencies:**
```bash
pip install trafilatura beautifulsoup4
```

**Also Provides:** `EntityPatternExtractor` for regex-based contact info extraction

```python
from app.services.intelligence.providers.deterministic_extraction import EntityPatternExtractor

emails = EntityPatternExtractor.extract_emails(text)
phones = EntityPatternExtractor.extract_phones(text)
linkedin_urls = EntityPatternExtractor.extract_linkedin_urls(text)
github_urls = EntityPatternExtractor.extract_github_urls(text)
twitter_handles = EntityPatternExtractor.extract_twitter_handles(text)
```

---

### 3. Deterministic Entity Extractor

**Module:** `services/intelligence/providers/entity_extractor.py`  
**Class:** `DeterministicEntityExtractor`

**Features:**
- Pattern-based extraction (no LLM)
- Extracts names, titles, companies, locations, contact info
- Heuristic-based (looks for common patterns)
- Never fabricates data

**Usage:**
```python
from app.services.intelligence.providers.entity_extractor import DeterministicEntityExtractor

extractor = DeterministicEntityExtractor()

# Extract person
entity = await extractor.extract_person(
    text=cleaned_page_content,
    context_url="https://linkedin.com/in/johndoe"
)

if entity:
    print(f"Found: {entity.full_name} - {entity.title} at {entity.company}")
```

**Extraction Method:**
1. Use regex patterns for emails, phones, LinkedIn URLs, etc.
2. Heuristics for names (capitalized words)
3. Heuristics for job titles (look for common keywords)
4. Heuristics for companies (after "at", "works at", etc.)
5. Heuristics for location (after "in", "based in", etc.)

**Returned Fields:**
- `full_name` – Best guess from text (or None)
- `title` – Most relevant job title found (or None)
- `company` – Most relevant company found (or None)
- `email`, `phone`, `linkedin_url` – From patterns
- `skills`, `employment_history`, `education` – Empty (would need LLM)

---

### 4. Safe Page Fetcher

**Module:** `services/intelligence/providers/page_fetcher.py`  
**Class:** `SafePageFetcher`

**Features:**
- Wraps SearchProvider with safety checks
- Respects robots.txt
- Detects logins and CAPTCHAs
- Rate limiting
- Timeout handling

**Usage:**
```python
from app.services.intelligence.providers.page_fetcher import SafePageFetcher
from app.services.intelligence.providers.duckduckgo_search import DuckDuckGoSearchProvider

search = DuckDuckGoSearchProvider()
fetcher = SafePageFetcher(search_provider=search)

# Check if URL can be fetched
can_fetch = await fetcher.can_fetch("https://example.com/page")

# Fetch with safety checks
if can_fetch:
    page = await fetcher.fetch_safe("https://example.com/page")
```

**Raises:**
- `RobotsBlockedError` – If robots.txt blocks URL
- `LoginRequiredError` – If login page detected
- `CaptchaDetectedError` – If CAPTCHA detected
- `TimeoutError` – If timeout exceeded
- `ProviderException` – On other errors

---

## Utilities

### URLNormalizer
Normalize URLs for deduplication.

```python
from app.services.intelligence.utils import URLNormalizer

normalized = URLNormalizer.normalize("https://Example.COM/page/")
# "https://example.com/page"

domain = URLNormalizer.get_domain("https://www.example.com")
# "example.com"
```

### RobotsChecker
Check robots.txt rules with caching.

```python
from app.services.intelligence.utils import RobotsChecker

robots = RobotsChecker(cache_ttl_seconds=3600)
can_fetch = await robots.can_fetch("https://example.com/page")
```

### CaptchaDetector
Detect CAPTCHA in HTML.

```python
from app.services.intelligence.utils import CaptchaDetector

has_captcha = CaptchaDetector.detect_captcha(html_content, url)
```

### LoginDetector
Detect login-required pages.

```python
from app.services.intelligence.utils import LoginDetector

needs_login = LoginDetector.detect_login_required(html_content, status_code)
```

### ThrottleManager
Rate limiting per domain.

```python
from app.services.intelligence.utils import ThrottleManager

throttle = ThrottleManager(min_delay_seconds=0.5)
await throttle.wait_for_domain("https://example.com")
# Ensures 500ms delay between requests to example.com
```

---

## Adding a New Search Provider

### Step 1: Create Provider Class

```python
# services/intelligence/providers/new_search.py

from app.services.intelligence.interfaces import SearchProvider, PageContent, SearchResult

class NewSearchProvider(SearchProvider):
    def __init__(self, api_key: str, timeout_seconds: int = 10):
        self.api_key = api_key
        self.timeout = timeout_seconds

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Implement search logic."""
        # Call your search API
        # Return list[SearchResult]
        pass

    async def get_page_content(self, url: str) -> PageContent:
        """Implement page fetching."""
        # Fetch URL, check robots.txt, detect blocks
        # Return PageContent
        pass
```

### Step 2: Register in Config

```python
# backend/app/core/config.py

class IntelligenceSettings(BaseSettings):
    SEARCH_PROVIDER: str = "duckduckgo"  # NEW_PROVIDER | duckduckgo
    NEW_PROVIDER_API_KEY: str | None = None
```

### Step 3: Use in Orchestrator

```python
# services/intelligence/orchestrator.py

if config.SEARCH_PROVIDER == "new_provider":
    search_provider = NewSearchProvider(api_key=settings.NEW_PROVIDER_API_KEY)
else:
    search_provider = DuckDuckGoSearchProvider()
```

---

## Adding a New Entity Extractor

### Step 1: Implement EntityExtractor Interface

```python
# services/intelligence/providers/new_extractor.py

from app.services.intelligence.interfaces import EntityExtractor, ExtractedEntity

class NewExtractor(EntityExtractor):
    async def extract_person(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        # Implement extraction logic
        # IMPORTANT: Never fabricate. Use None for missing, "Unknown" for explicit missing
        pass

    async def extract_company(self, text: str, context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        # Implement extraction logic
        pass
```

### Step 2: Register in Orchestrator

```python
if extraction_method == "llm":
    extractor = LLMEntityExtractor()
elif extraction_method == "deterministic":
    extractor = DeterministicEntityExtractor()
```

---

## Adding LLM-Based Extraction (Future)

### Step 1: Create LLMProvider Implementation

```python
# services/intelligence/providers/llm_extractor.py

from app.services.intelligence.interfaces import LLMProvider, EntityExtractor

class ClaudeExtractor(LLMProvider, EntityExtractor):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def extract_entities_from_text(self, text: str, entity_type: str = "person", context_url: Optional[str] = None) -> Optional[ExtractedEntity]:
        # Use Claude API to extract entities
        # Prompt should emphasize: never fabricate, use None for missing
        pass
```

### Step 2: Use as Fallback

```python
# In orchestrator:
deterministic = DeterministicEntityExtractor()
llm = ClaudeExtractor(api_key=settings.CLAUDE_API_KEY)

# Try deterministic first
entity = await deterministic.extract_person(text)

# Fall back to LLM if deterministic insufficient
if not entity or entity.extraction_confidence < 0.5:
    entity = await llm.extract_entities_from_text(text, entity_type="person")
```

---

## Configuration Example

```python
# backend/app/core/config.py

from app.services.intelligence.interfaces import SearchProvider, EntityExtractor

class IntelligenceSettings(BaseSettings):
    # Provider selection
    SEARCH_PROVIDER: str = "duckduckgo"  # duckduckgo | google | brave
    EXTRACTION_PROVIDER: str = "deterministic"  # deterministic | llm
    LLM_PROVIDER: str = "deepseek"  # deepseek | claude

    # Throttling
    MAX_PAGES_PER_SESSION: int = 50
    REQUEST_TIMEOUT_SECONDS: int = 10
    THROTTLE_DELAY_SECONDS: float = 0.5

    # Confidence thresholds
    CONFIDENCE_THRESHOLD_HIGH: float = 0.90
    CONFIDENCE_THRESHOLD_MEDIUM: float = 0.70

    # Scoring weights (configurable, not hardcoded)
    SCORE_WEIGHTS: dict = {
        "name_match": 0.25,
        "company_match": 0.25,
        "title_match": 0.15,
        "location_match": 0.10,
        "employment_history_consistency": 0.15,
        "cross_source_agreement": 0.10
    }

    # API keys
    GOOGLE_SEARCH_API_KEY: str | None = None
    BRAVE_SEARCH_API_KEY: str | None = None
```

---

## Testing Providers

### Unit Tests

```python
# tests/test_providers.py

import pytest
from app.services.intelligence.providers.duckduckgo_search import DuckDuckGoSearchProvider
from app.services.intelligence.providers.entity_extractor import DeterministicEntityExtractor

@pytest.mark.asyncio
async def test_duckduckgo_search():
    provider = DuckDuckGoSearchProvider()
    results = await provider.search("Python programming")
    assert len(results) > 0
    assert results[0].url

@pytest.mark.asyncio
async def test_entity_extraction():
    extractor = DeterministicEntityExtractor()
    text = "John Doe is a VP of Sales at TechCorp in San Francisco"
    entity = await extractor.extract_person(text)
    assert entity.full_name == "John Doe" or "John" in entity.full_name
    assert entity.title == "VP of Sales" or "VP" in entity.title
```

---

## Performance Considerations

- **Caching:** URL deduplication via Sources table prevents re-fetching
- **Throttling:** Per-domain rate limiting (default 0.5s between requests)
- **Timeouts:** 10-second default for page fetches
- **Robots.txt:** Cached per domain (3600s default TTL)
- **Extraction:** Deterministic extraction is much faster than LLM

---

## Privacy & Safety

**Design Principles:**
1. ✅ Only fetch public pages (no login bypassing)
2. ✅ Respect robots.txt and access blocks
3. ✅ Detect and reject CAPTCHAs
4. ✅ No credential collection
5. ✅ Retention dates on all raw content (GDPR)
6. ✅ Never fabricate data

**Violations:**
- ❌ Cannot bypass login walls
- ❌ Cannot solve CAPTCHAs
- ❌ Cannot ignore robots.txt
- ❌ Cannot store sensitive PII (passwords, financial data)

---

**Next:** Phase 3 will implement identity resolution, scoring, and conflict detection services.
