"""
Workflow state management for the orchestration engine.
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4


class WorkflowState(TypedDict):
    """State object passed between agents in the LangGraph workflow."""

    # Workflow metadata
    workflow_id: str
    run_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Request information
    user_request: str
    request_metadata: Dict[str, Any]

    # Dynamic routing — set by PlannerAgent
    route: str              # "simple_factual" | "complex_research" | "code"
    query_complexity: str   # mirrors route, used for logging/metrics

    # Cycle control — incremented each time research runs
    research_iteration_count: int

    # Execution state
    current_step: str
    completed_steps: List[str]
    history: List[str]

    # Data and context
    context: Dict[str, Any]
    kb_results: List[Dict[str, Any]]       # results from Milvus KB search
    web_results: List[Dict[str, Any]]      # results from web search
    retrieved_documents: List[Dict[str, Any]]  # merged KB + web results

    # Long-term memory — injected from PostgreSQL before workflow starts
    conversation_history: List[Dict[str, Any]]

    # Per-agent outputs
    intermediate_results: Dict[str, Any]

    # Structured final output — set by FinalOutputAgent
    final_output: Optional[Dict[str, Any]]

    # Error handling
    errors: List[Dict[str, Any]]
    status: str  # "running" | "completed" | "failed" | "paused"


def create_initial_state(
    user_request: str,
    user_id: Optional[str] = None,
    workflow_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> WorkflowState:
    """Create an initial workflow state."""
    now = datetime.utcnow()
    return WorkflowState(
        workflow_id=workflow_id,
        run_id=str(uuid4()),
        user_id=user_id,
        created_at=now,
        updated_at=now,
        user_request=user_request,
        request_metadata=metadata or {},
        route="",
        query_complexity="",
        research_iteration_count=0,
        current_step="",
        completed_steps=[],
        history=[],
        context={},
        kb_results=[],
        web_results=[],
        retrieved_documents=[],
        conversation_history=conversation_history or [],
        intermediate_results={},
        final_output=None,
        errors=[],
        status="running",
    )
