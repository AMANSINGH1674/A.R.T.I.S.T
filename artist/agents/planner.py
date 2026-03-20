"""
Planner agent — classifies the user query and sets the workflow route.

Routes:
  "simple_factual"   → skip research, go straight to synthesis
  "complex_research" → full pipeline: research → synthesis → fact_check
  "code"             → research pipeline + code-aware synthesis prompt
"""

import json
import structlog
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from .base import BaseAgent
from ..orchestration.state import WorkflowState
from ..llm.providers import get_llm

logger = structlog.get_logger()


class PlannerAgent(BaseAgent):
    """Classifies the query and determines which workflow path to take."""

    def __init__(self):
        super().__init__(
            name="planner",
            description="Classifies query complexity and routes the workflow dynamically",
        )
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.0)  # deterministic classification
        return self._llm

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        user_request = state["user_request"]
        self.logger.info("Planning workflow route", user_request=user_request[:100])

        messages = [
            SystemMessage(content=(
                "Classify the user's query into exactly one category:\n\n"
                "- 'simple_factual': A short factual question answerable from general knowledge "
                "(e.g. 'Who is the PM of India?', 'What is the capital of France?')\n"
                "- 'complex_research': Requires gathering and synthesising multiple sources "
                "(e.g. 'Compare quantum computing approaches', 'Explain the causes of WW1')\n"
                "- 'code': Involves writing, debugging, or explaining code or technical commands\n\n"
                "Respond ONLY with valid JSON, no markdown:\n"
                "{\"route\": \"simple_factual\", \"reason\": \"one sentence\"}"
            )),
            HumanMessage(content=user_request),
        ]

        route = "complex_research"  # safe default
        try:
            response = await self.llm.ainvoke(messages)
            raw = response.content.strip()
            # Strip markdown code fences if LLM wraps the JSON
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
            candidate = result.get("route", "complex_research")
            if candidate in ("simple_factual", "complex_research", "code"):
                route = candidate
        except Exception as e:
            self.logger.warning("Planner classification failed, defaulting to complex_research", error=str(e))

        state["route"] = route
        state["query_complexity"] = route
        state["current_step"] = "planner"
        state["completed_steps"].append("planner")
        state["history"].append(f"Planner routed query as: {route}")
        self.logger.info("Query classified", route=route)

        return state
