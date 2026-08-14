import httpx
from typing import Optional
from app.core.config import settings


class LinkedInService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.LINKEDIN_API_KEY
        self.api_host = settings.LINKEDIN_API_HOST
        self.endpoint = settings.LINKEDIN_API_ENDPOINT

    async def get_profile_data(self, linkedin_url: str) -> dict:
        """Fetch LinkedIn profile data from a URL."""
        if not self.api_key:
            raise ValueError("LinkedIn API key not configured")

        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": self.api_host,
            "x-rapidapi-key": self.api_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.endpoint}/get-profile-data-by-url",
                    params={"url": linkedin_url},
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise ValueError(f"LinkedIn API error: {str(e)}")

    def extract_key_info(self, profile_data: dict) -> dict:
        """Extract key information from LinkedIn profile."""
        data = profile_data.get("data", {})
        return {
            "name": data.get("full_name", ""),
            "headline": data.get("headline", ""),
            "summary": data.get("summary", ""),
            "location": data.get("location", ""),
            "industry": data.get("industry", ""),
            "current_position": data.get("experiences", [{}])[0].get("title", "") if data.get("experiences") else "",
            "company": data.get("experiences", [{}])[0].get("company_name", "") if data.get("experiences") else "",
        }

    async def search_and_enrich(self, prospect_input: str) -> dict:
        """Search and enrich prospect data (expects LinkedIn URL in input)."""
        if "linkedin.com" not in prospect_input.lower():
            return {
                "success": False,
                "message": "Please provide a LinkedIn URL for profile enrichment",
                "raw_data": prospect_input
            }

        profile_data = await self.get_profile_data(prospect_input)
        enriched = self.extract_key_info(profile_data)
        return {
            "success": True,
            "enriched_data": enriched,
            "raw_data": profile_data
        }
