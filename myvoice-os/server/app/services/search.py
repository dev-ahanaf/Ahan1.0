"""Brave Search API integration for live web lookups."""
import httpx
from app.config import BRAVE_SEARCH_API_KEY

async def search_brave(query: str) -> str:
    """Execute search query using Brave Search REST API."""
    if not BRAVE_SEARCH_API_KEY:
        return "Web search is not yet configured. Add BRAVE_SEARCH_API_KEY to the server environment."
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
                "Accept": "application/json"
            },
            params={"q": query, "count": 3}
        )
        response.raise_for_status()
        hits = response.json().get("web", {}).get("results", [])[:3]
    if not hits:
        return "I couldn't find search results for that."
    parts = [f"{h.get('title', 'Result')}: {h.get('description', '')}" for h in hits]
    return "Search results: " + " ".join(parts)[:850]
