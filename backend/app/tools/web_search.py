from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from app.settings import settings

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Search the web for current information using Serper API."""

    def __init__(self) -> None:
        self.base_url = "https://google.serper.dev"
        if not self.api_key:
            logger.warning("SERPER_API_KEY not configured - web search disabled")

    @property
    def api_key(self) -> str:
        return (settings.serper_api_key or "").strip()

    async def search(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "search",
    ) -> dict[str, Any]:
        """
        Search the web and return results.

        Args:
            query: search query string
            num_results: number of results (1-10)
            search_type: 'search' | 'news' | 'images'
        """
        if not self.api_key:
            return {"error": "Web search not configured"}

        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": max(1, min(int(num_results), 10))}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/{search_type}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Serper API error: %s - %s", response.status, error_text)
                        return {"error": f"Search failed: {response.status}"}
                    return await response.json()
        except asyncio.TimeoutError:
            logger.error("Serper API timeout")
            return {"error": "Search timeout"}
        except Exception as e:
            logger.error("Search error: %s", e)
            return {"error": str(e)}

    def search_sync(self, query: str, num_results: int = 5, search_type: str = "search") -> dict[str, Any]:
        """Sync wrapper for route/client code that isn't async."""
        return asyncio.run(self.search(query=query, num_results=num_results, search_type=search_type))

    def format_results(self, results: dict[str, Any], max_results: int = 3) -> str:
        """Format search results for LLM context."""
        if "error" in results:
            return f"Search failed: {results['error']}"

        formatted: list[str] = []

        answer_box = results.get("answerBox") or {}
        if "answer" in answer_box:
            formatted.append(f"Direct Answer: {answer_box['answer']}")
        elif "snippet" in answer_box:
            formatted.append(f"Quick Answer: {answer_box['snippet']}")

        knowledge_graph = results.get("knowledgeGraph") or {}
        if "description" in knowledge_graph:
            formatted.append(f"\nAbout: {knowledge_graph.get('title', 'Entity')}")
            formatted.append(str(knowledge_graph["description"]))

        organic = results.get("organic") or []
        if organic:
            formatted.append("\n--- Search Results ---")
            for index, result in enumerate(organic[: max(1, int(max_results))], 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                link = result.get("link", "")
                formatted.append(f"\n{index}. {title}\n   {snippet}\n   Source: {link}")

        if not formatted:
            return "No results found."

        return "\n".join(formatted)

    def is_available(self) -> bool:
        return bool(self.api_key)


web_search = WebSearchTool()

