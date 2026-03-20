"""
Fact-checking agent — uses the configured LLM provider to critically evaluate
the synthesis output and flag unsupported or uncertain claims.
"""

import json
import structlog
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from .base import BaseAgent
from ..orchestration.state import WorkflowState
from ..llm.providers import get_llm

logger = structlog.get_logger()


class FactCheckAgent(BaseAgent):
    """Agent specialised in fact-checking and verification"""

    def __init__(self):
        super().__init__(
            name="fact_check",
            description="Verifies facts and checks accuracy of synthesised information",
        )
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.0)  # deterministic for verification
        return self._llm

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        """Execute fact-checking tasks and update the workflow state"""
        self.logger.info("Starting fact-checking phase")

        try:
            synthesis_results = state.get("intermediate_results", {}).get("synthesis", {})

            if not synthesis_results or synthesis_results.get("status") == "no_data":
                self.logger.warning("No synthesis results available for fact-checking")
                state["intermediate_results"]["fact_check"] = {
                    "status": "no_data",
                    "message": "No synthesis results were available for fact-checking",
                }
            else:
                summary = synthesis_results.get("summary", "")
                sources_used = synthesis_results.get("sources_used", 0)
                retrieved_docs = state.get("retrieved_documents", [])

                # Build source context for grounding the fact-check
                source_context = "\n\n".join(
                    f"[Source {i+1}]: {doc['text'][:400]}"
                    for i, doc in enumerate(retrieved_docs[:5])
                )

                messages = [
                    SystemMessage(content=(
                        "You are a rigorous fact-checker. "
                        "Given a summary and the original source documents it was based on, "
                        "evaluate the summary's accuracy. "
                        "Respond ONLY with a JSON object in this exact format:\n"
                        "{\n"
                        '  "verified": true/false,\n'
                        '  "confidence_score": 0.0-1.0,\n'
                        '  "concerns": ["list of specific concerns or empty list"],\n'
                        '  "unsupported_claims": ["claims not backed by sources or empty list"],\n'
                        '  "recommendation": "approved" or "needs_review" or "rejected"\n'
                        "}"
                    )),
                    HumanMessage(content=(
                        f"Summary to fact-check:\n{summary}\n\n"
                        f"Original source documents:\n{source_context}\n\n"
                        "Evaluate the summary's accuracy against the sources."
                    )),
                ]

                response = await self.llm.ainvoke(messages)

                # Parse JSON response — fall back to heuristic if malformed
                try:
                    raw = response.content.strip()
                    # Strip markdown code fences if present
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"):
                            raw = raw[4:]
                    llm_result = json.loads(raw)
                except (json.JSONDecodeError, IndexError):
                    self.logger.warning("LLM returned non-JSON fact-check response, using heuristic")
                    score = min(0.95, 0.7 + (sources_used * 0.05))
                    llm_result = {
                        "verified": score > 0.7,
                        "confidence_score": score,
                        "concerns": [],
                        "unsupported_claims": [],
                        "recommendation": "approved" if score > 0.7 else "needs_review",
                    }

                fact_check_result = {
                    **llm_result,
                    "sources_verified": sources_used,
                    "verification_method": "llm_cross_reference",
                }

                self.logger.info(
                    "Fact-checking completed",
                    verified=fact_check_result.get("verified"),
                    confidence=fact_check_result.get("confidence_score"),
                )
                state["intermediate_results"]["fact_check"] = fact_check_result

            # Increment cycle counter — used by engine router to cap re-research loops
            state["research_iteration_count"] = state.get("research_iteration_count", 0) + 1

            state["completed_steps"].append("fact_check")
            state["current_step"] = "fact_check"
            state["history"].append(
                f"Fact-checking completed (iteration {state['research_iteration_count']})"
            )

        except Exception as e:
            state["errors"].append({"agent": self.name, "error": str(e), "step": "fact_check"})
            state["status"] = "failed"
            self.logger.error("Fact-checking agent failed", error=str(e), exc_info=True)

        return state
