"""Live web search tool for MyVoice OS integrating Brave Search."""
import os
from typing import Dict, Any, List
import httpx
from app.services.tools.base import BaseTool, ToolContext, ToolResult

class SearchTool(BaseTool):
    name = "web_search"
    description = "Search the live web for recent news, events, facts, or questions requiring current information."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query keywords to look up on the web."
            }
        },
        "required": ["query"]
    }

    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        query = (args.get("query") or "").strip()
        if not query:
            return ToolResult(
                success=False,
                error="Empty search query",
                voice_summary="Please provide something to search for."
            )

        api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
        if not api_key:
            return ToolResult(
                success=False,
                error="BRAVE_SEARCH_API_KEY is not configured",
                voice_summary="Web search is currently unavailable because a search API key is not configured on the server."
            )

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params={"q": query, "count": 3}
                )
                if res.status_code != 200:
                    return ToolResult(
                        success=False,
                        error=f"Brave Search returned HTTP {res.status_code}",
                        voice_summary=f"Search service returned an error for '{query}'."
                    )
                
                data = res.json()
                web_results = data.get("web", {}).get("results", [])
                if not web_results:
                    return ToolResult(
                        success=True,
                        data={"query": query, "results": []},
                        voice_summary=f"I searched the web for '{query}' but did not find any matching results."
                    )
                
                snippets: List[str] = []
                sources: List[Dict[str, str]] = []
                for item in web_results[:3]:
                    title = item.get("title", "")
                    desc = item.get("description", "")
                    url = item.get("url", "")
                    if desc:
                        snippets.append(f"{title}: {desc}")
                        sources.append({"title": title, "url": url})
                
                combined_text = " ".join(snippets)
                # Cap voice summary to 2 concise sentences for audio playback
                short_summary = f"According to online sources: {combined_text[:300]}..."

                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "snippets": snippets,
                        "sources": sources
                    },
                    voice_summary=short_summary,
                    display_data={
                        "screen": "search",
                        "query": query[:20],
                        "results_count": len(web_results)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                voice_summary=f"Sorry, I encountered an error while searching for '{query}'."
            )
