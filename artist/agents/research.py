"""
Research agent — runs KB semantic search and web search in parallel,
then merges results into a single retrieved_documents list.

Parallel execution (asyncio.gather) means both searches happen simultaneously,
reducing latency vs sequential execution.
"""

import asyncio
import structlog
from typing import Dict, Any, List, Optional

from .base import BaseAgent
from ..orchestration.state import WorkflowState
from ..knowledge.rag import RAGSystem
from ..tools.web_search import DuckDuckGoSearchTool

logger = structlog.get_logger()


class ResearchAgent(BaseAgent):
    """Conducts parallel KB + web research and merges results."""

    def __init__(self, rag_system: RAGSystem, web_search_tool: Optional[DuckDuckGoSearchTool] = None):
        super().__init__(
            name="research",
            description="Conducts parallel knowledge-base and web research",
        )
        self.rag_system = rag_system
        self.web_search_tool = web_search_tool or DuckDuckGoSearchTool()

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        user_request = state["user_request"]
        iteration = state.get("research_iteration_count", 0)
        self.logger.info("Starting research phase", iteration=iteration, user_request=user_request[:100])

        # Refine query on re-search iterations — append context from previous concerns
        query = user_request
        if iteration > 0:
            concerns = state.get("intermediate_results", {}).get("fact_check", {}).get("concerns", [])
            if concerns:
                query = f"{user_request} — clarify: {'; '.join(concerns[:2])}"

        # Run KB search and web search concurrently
        kb_results, web_results = await asyncio.gather(
            self._kb_search(query),
            self._web_search(query),
        )

        # Merge and deduplicate by source identifier
        merged = _merge_results(kb_results, web_results)

        state["kb_results"] = kb_results
        state["web_results"] = web_results
        state["retrieved_documents"] = merged
        state["intermediate_results"]["research"] = {
            "documents_found": len(merged),
            "kb_results": len(kb_results),
            "web_results": len(web_results),
            "search_query": query,
            "iteration": iteration,
            "top_sources": [
                d.get("metadata", {}).get("source", "unknown") for d in merged[:3]
            ],
        }
        state["completed_steps"].append("research")
        state["current_step"] = "research"
        state["history"].append(
            f"Research (iteration {iteration}): {len(merged)} docs "
            f"(KB: {len(kb_results)}, Web: {len(web_results)})"
        )
        self.logger.info(
            "Research phase completed",
            kb=len(kb_results), web=len(web_results), merged=len(merged),
        )
        return state

    async def _kb_search(self, query: str) -> List[Dict[str, Any]]:
        try:
            return await self.rag_system.search(query, k=5)
        except Exception as e:
            self.logger.warning("KB search failed", error=str(e))
            return []

    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        try:
            raw = await self.web_search_tool.execute(query, num_results=5)
            # Normalise to the same shape as KB results
            return [
                {
                    "text": f"{r.get('title', '')}\n{r.get('snippet', '')}",
                    "metadata": {
                        "source": r.get("link") or r.get("title", "web"),
                        "title": r.get("title", ""),
                        "type": "web",
                    },
                    "score": 0.75,
                }
                for r in raw
                if r.get("snippet") or r.get("title")
            ]
        except Exception as e:
            self.logger.warning("Web search failed", error=str(e))
            return []


def _merge_results(
    kb_results: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge KB and web results, deduplicating by source URL/name."""
    seen: set = set()
    merged: List[Dict[str, Any]] = []
    for doc in kb_results + web_results:
        key = doc.get("metadata", {}).get("source", doc.get("text", "")[:80])
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    # Sort by score descending (KB results tend to have explicit similarity scores)
    merged.sort(key=lambda d: d.get("score", 0), reverse=True)
    return merged
