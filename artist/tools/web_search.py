"""
Web search tool for information retrieval from the internet.

Two implementations:
- WebSearchTool   — Google Custom Search API (requires GOOGLE_API_KEY)
- DuckDuckGoSearchTool — DuckDuckGo (free, no API key required, used as default)
"""

import asyncio
from typing import Dict, Any, List
import structlog
import httpx

from .base import BaseTool

logger = structlog.get_logger()


class WebSearchTool(BaseTool):
    """Tool for performing web searches"""

    def __init__(self, api_key: str, search_engine_id: str):
        super().__init__(
            name="web_search",
            description="Search the web for information using a search engine API"
        )
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def execute(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Execute a web search and return a list of results"""
        self.logger.info("Executing web search", query=query)
        
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": num_results
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()  # Raise an exception for bad status codes
                
            search_results = response.json().get("items", [])
            
            formatted_results = [
                {
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "Google Custom Search"
                }
                for item in search_results
            ]
            
            self.logger.info("Web search completed successfully", num_results=len(formatted_results))
            return formatted_results
            
        except httpx.HTTPStatusError as e:
            self.logger.error("HTTP error during web search", error=str(e), status_code=e.response.status_code)
            return []
        except Exception as e:
            self.logger.error("An unexpected error occurred during web search", error=str(e))
            return []


class DuckDuckGoSearchTool(BaseTool):
    """Web search using DuckDuckGo — free, no API key required."""

    def __init__(self):
        super().__init__(
            name="duckduckgo_search",
            description="Search the web using DuckDuckGo (no API key required)",
        )

    async def execute(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Run DuckDuckGo text search in a thread pool (DDGS is synchronous)."""
        self.logger.info("Executing DuckDuckGo search", query=query)
        try:
            from ddgs import DDGS

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=num_results)),
            )
            formatted = [
                {
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "DuckDuckGo",
                }
                for r in results
            ]
            self.logger.info("DuckDuckGo search completed", num_results=len(formatted))
            return formatted
        except Exception as e:
            self.logger.warning("DuckDuckGo search failed", error=str(e))
            return []

