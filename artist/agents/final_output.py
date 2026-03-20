"""
Final output agent — assembles a structured, presentation-ready response
from all intermediate agent results.
"""

import structlog
from typing import Any

from .base import BaseAgent
from ..orchestration.state import WorkflowState

logger = structlog.get_logger()


class FinalOutputAgent(BaseAgent):
    """Formats and structures the final response for delivery to the user."""

    def __init__(self):
        super().__init__(
            name="final_output",
            description="Formats intermediate agent results into a structured final response",
        )

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        self.logger.info("Assembling final output")

        synthesis = state.get("intermediate_results", {}).get("synthesis", {})
        fact_check = state.get("intermediate_results", {}).get("fact_check", {})
        research = state.get("intermediate_results", {}).get("research", {})

        # Deduplicate and collect source URLs / names
        sources = []
        seen = set()
        for doc in state.get("retrieved_documents", []):
            meta = doc.get("metadata", {})
            source = meta.get("source") or meta.get("link") or meta.get("title", "")
            if source and source not in seen:
                seen.add(source)
                sources.append(source)

        # Determine overall confidence — prefer fact_check score when available
        fc_status = fact_check.get("status")
        if fc_status == "no_data":
            confidence = synthesis.get("confidence_score", 0.75)
            verified = False
            concerns = []
            recommendation = "needs_review"
        else:
            confidence = fact_check.get("confidence_score", synthesis.get("confidence_score", 0.75))
            verified = fact_check.get("verified", False)
            concerns = fact_check.get("concerns", [])
            recommendation = fact_check.get("recommendation", "needs_review")

        state["final_output"] = {
            "summary": synthesis.get("summary", "No summary available."),
            "key_points": synthesis.get("key_points", []),
            "confidence": round(confidence, 2),
            "verified": verified,
            "concerns": concerns,
            "unsupported_claims": fact_check.get("unsupported_claims", []),
            "recommendation": recommendation,
            "sources": sources[:5],
            "metadata": {
                "route_taken": state.get("route", "unknown"),
                "research_iterations": state.get("research_iteration_count", 0),
                "kb_results_found": research.get("kb_results", 0),
                "web_results_found": research.get("web_results", 0),
                "total_sources": len(state.get("retrieved_documents", [])),
            },
        }

        state["status"] = "completed"
        state["current_step"] = "final_output"
        state["completed_steps"].append("final_output")
        state["history"].append("Final output structured and ready")
        self.logger.info(
            "Final output assembled",
            confidence=confidence,
            sources=len(sources),
            route=state.get("route"),
        )

        return state
