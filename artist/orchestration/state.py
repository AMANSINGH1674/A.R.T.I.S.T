"""
Workflow state management for the orchestration engine.
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

class WorkflowState(TypedDict):
    """State object for workflow execution"""
    
    # Workflow metadata
    workflow_id: str
    run_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Request information
    user_request: str
    request_metadata: Dict[str, Any]
    
    # Execution state
    current_step: str
    completed_steps: List[str]
    history: List[str]
    
    # Data and context
    context: Dict[str, Any]
    retrieved_documents: List[Dict[str, Any]]
    intermediate_results: Dict[str, Any]
    
    # Final output
    final_output: Optional[Dict[str, Any]]
    
    # Error handling
    errors: List[Dict[str, Any]]
    status: str  # "running", "completed", "failed", "paused"


def create_initial_state(
    user_request: str,
    user_id: Optional[str] = None,
    workflow_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None
) -> WorkflowState:
    """Create an initial workflow state"""
    
    now = datetime.utcnow()
    run_id = str(uuid4())
    
    return WorkflowState(
        workflow_id=workflow_id,
        run_id=run_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        user_request=user_request,
        request_metadata=metadata or {},
        current_step="",
        completed_steps=[],
        history=[],
        context={},
        retrieved_documents=[],
        intermediate_results={},
        final_output=None,
        errors=[],
        status="running"
    )
