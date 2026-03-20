"""
Orchestration engine — cyclic LangGraph workflow with dynamic routing.

Graph topology:
                    ┌─────────────────────────────────────┐
                    │  (confidence < 0.7 && iteration < 3) │
                    ▼                                       │
  planner ──► research ──► synthesis ──► fact_check ───────┘
     │                                       │
     │ (simple_factual)                      │ (approved / max iterations)
     ▼                                       ▼
  synthesis                            final_output ──► END

Dynamic routing:
  - PlannerAgent classifies query → simple_factual skips research
  - FactCheckAgent sets confidence; if < 0.7 the graph cycles back to research
  - Cycle is capped at 3 iterations to prevent infinite loops
"""

import structlog
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from ..agents.planner import PlannerAgent
from ..agents.research import ResearchAgent
from ..agents.synthesis import SynthesisAgent
from ..agents.fact_check import FactCheckAgent
from ..agents.final_output import FinalOutputAgent
from ..knowledge.rag import RAGSystem
from ..tools.web_search import DuckDuckGoSearchTool
from .state import WorkflowState

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Routing functions — pure functions, no side effects
# ---------------------------------------------------------------------------

def _route_after_planner(state: WorkflowState) -> str:
    """Route simple queries directly to synthesis; everything else through research."""
    if state.get("route") == "simple_factual":
        return "synthesis"
    return "research"


def _route_after_fact_check(state: WorkflowState) -> str:
    """Cycle back to research if confidence is low and we haven't hit the cap."""
    iterations = state.get("research_iteration_count", 0)
    if iterations >= 3:
        return "final_output"

    fc = state.get("intermediate_results", {}).get("fact_check", {})
    # Don't cycle when there were no sources to verify against
    if fc.get("status") == "no_data":
        return "final_output"

    confidence = fc.get("confidence_score", 1.0)
    if confidence < 0.7:
        logger.info("Low confidence detected — cycling back to research", confidence=confidence, iteration=iterations)
        return "research"

    return "final_output"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class OrchestrationEngine:
    """Manages the cyclic multi-agent LangGraph workflow."""

    def __init__(self, rag_system: RAGSystem):
        self.rag_system = rag_system
        self._agents: Dict[str, Any] = {}
        self._compiled_graph = None

    async def initialize(self):
        logger.info("Initializing orchestration engine...")
        web_search_tool = DuckDuckGoSearchTool()
        self._agents = {
            "planner":      PlannerAgent(),
            "research":     ResearchAgent(rag_system=self.rag_system, web_search_tool=web_search_tool),
            "synthesis":    SynthesisAgent(),
            "fact_check":   FactCheckAgent(),
            "final_output": FinalOutputAgent(),
        }
        self._compiled_graph = self._build_graph()
        logger.info("Orchestration engine ready — cyclic graph compiled")

    async def shutdown(self):
        logger.info("Shutting down orchestration engine...")

    def _make_node(self, agent_name: str):
        """Wrap an agent's execute() as an async LangGraph node."""
        agent = self._agents[agent_name]

        async def node(state: WorkflowState) -> WorkflowState:
            logger.info("Executing agent node", agent=agent_name)
            return await agent.execute(state)

        node.__name__ = agent_name
        return node

    def _build_graph(self):
        """Build the cyclic StateGraph."""
        workflow = StateGraph(WorkflowState)

        # Register all agent nodes
        for name in ("planner", "research", "synthesis", "fact_check", "final_output"):
            workflow.add_node(name, self._make_node(name))

        # Entry point
        workflow.set_entry_point("planner")

        # Planner → conditional fork
        workflow.add_conditional_edges(
            "planner",
            _route_after_planner,
            {
                "synthesis": "synthesis",   # simple_factual shortcut
                "research":  "research",    # full pipeline
            },
        )

        # Linear edges through the pipeline
        workflow.add_edge("research", "synthesis")
        workflow.add_edge("synthesis", "fact_check")

        # Fact-check → conditional (THE CYCLE or exit)
        workflow.add_conditional_edges(
            "fact_check",
            _route_after_fact_check,
            {
                "research":     "research",      # cycle back for low confidence
                "final_output": "final_output",  # approved or max iterations hit
            },
        )

        # Terminal edge
        workflow.add_edge("final_output", END)

        return workflow.compile()

    async def execute_workflow(self, workflow_id: str, initial_state: WorkflowState) -> Dict[str, Any]:
        if self._compiled_graph is None:
            raise RuntimeError("OrchestrationEngine not initialized — call initialize() first")

        logger.info("Executing cyclic workflow", workflow_id=workflow_id, run_id=initial_state.get("run_id"))
        final_state = await self._compiled_graph.ainvoke(initial_state)
        logger.info(
            "Workflow completed",
            status=final_state.get("status"),
            iterations=final_state.get("research_iteration_count", 0),
            route=final_state.get("route"),
        )
        return final_state

    def health_check(self) -> bool:
        return self._compiled_graph is not None
