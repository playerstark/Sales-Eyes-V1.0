import httpx
from typing import Optional

from app.core.config import settings


class NewsAPIService:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or settings.NEWSAPI_KEY
        self.endpoint = endpoint or settings.NEWSAPI_ENDPOINT

    async def get_industry_news(self, industry: str = "technology") -> dict:
        """Get top headlines for an industry/category."""
        if not self.api_key:
            raise ValueError("NewsAPI key not configured")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.endpoint}/top-headlines",
                    params={
                        "category": industry,
                        "language": "en",
                        "pageSize": 10,
                        "apiKey": self.api_key
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") != "ok":
                    return {"error": result.get("message", "Unknown error"), "articles": []}
                
                return {
                    "total_results": result.get("totalResults", 0),
                    "articles": result.get("articles", [])
                }
            except Exception as e:
                return {"error": str(e), "articles": []}

    async def search_news(self, query: str) -> dict:
        """Search for news articles by keyword."""
        if not self.api_key:
            raise ValueError("NewsAPI key not configured")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.endpoint}/everything",
                    params={
                        "q": query,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": 10,
                        "apiKey": self.api_key
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") != "ok":
                    return {"error": result.get("message", "Unknown error"), "articles": []}
                
                return {
                    "total_results": result.get("totalResults", 0),
                    "articles": result.get("articles", [])
                }
            except Exception as e:
                return {"error": str(e), "articles": []}

    def format_findings_from_articles(self, articles: list) -> list:
        """Convert news articles into findings with metadata."""
        findings = []
        
        for article in articles[:5]:  # Limit to top 5 articles
            if not article:
                continue
                
            finding = {
                "finding_type": "news",
                "source_header": article.get("source", {}).get("name", "News Source"),
                "summary": article.get("description") or article.get("title", "News article"),
                "source_link": article.get("url"),
                "confidence_score": 0.85,  # News from trusted sources
                "relevancy_score": 0.82,
                "raw_data": {
                    "title": article.get("title"),
                    "author": article.get("author"),
                    "published_at": article.get("publishedAt"),
                    "image_url": article.get("urlToImage"),
                    "content_preview": article.get("description", "")[:200]
                }
            }
            findings.append(finding)
        
        return findings

    async def get_company_news(self, company_name: str, industry: str = "business") -> dict:
        """Get news about a company using multiple strategies."""
        all_articles = []
        
        # Strategy 1: Try everything endpoint with exact company name
        try:
            result = await self.search_news(f'"{company_name}"')
            if "articles" in result and result.get("articles"):
                all_articles.extend(result.get("articles", []))
        except Exception:
            pass
        
        # Strategy 2: Try everything endpoint with company name + news
        if len(all_articles) < 5:
            try:
                result = await self.search_news(f'{company_name} news')
                if "articles" in result and result.get("articles"):
                    all_articles.extend(result.get("articles", []))
            except Exception:
                pass
        
        # Strategy 3: Fall back to industry news
        if len(all_articles) < 5:
            try:
                result = await self.get_industry_news(industry)
                if "articles" in result and result.get("articles"):
                    all_articles.extend(result.get("articles", []))
            except Exception:
                pass
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if not article:
                continue
            url = article.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return {
            "company_name": company_name,
            "articles_found": len(unique_articles),
            "articles": unique_articles[:10]
        }
