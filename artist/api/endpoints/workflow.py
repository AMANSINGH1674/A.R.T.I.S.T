"""
API endpoints for workflow management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
import structlog
from typing import Dict, Any, Optional
from celery.result import AsyncResult

from ...worker.tasks import execute_workflow_task
from ...security.auth import get_current_user
from ...config import settings

router = APIRouter()
logger = structlog.get_logger()


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow"""
    user_request: str = Field(..., description="The user's request or prompt", min_length=1)
    workflow_id: str = Field(default="default", description="The ID of the workflow to execute", max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata for the request")

    @field_validator("user_request")
    @classmethod
    def validate_request_length(cls, v: str) -> str:
        max_len = settings.max_request_length
        if len(v) > max_len:
            raise ValueError(f"user_request must not exceed {max_len} characters")
        return v


class WorkflowExecutionResponse(BaseModel):
    """Response model for starting a workflow execution"""
    task_id: str = Field(..., description="The ID of the asynchronous task")
    status_url: str = Field(..., description="URL to check the status of the task")
    result_url: str = Field(..., description="URL to retrieve the result of the task")


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def start_workflow(
    request: WorkflowExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Start a new workflow execution asynchronously"""
    logger.info(
        "Received workflow execution request",
        workflow_id=request.workflow_id,
        user_id=current_user.get("username"),
    )

    try:
        task = execute_workflow_task.delay(
            user_request=request.user_request,
            workflow_id=request.workflow_id,
            metadata=request.metadata,
            user_id=current_user.get("username"),
        )

        return {
            "task_id": task.id,
            "status_url": f"/api/v1/workflow/status/{task.id}",
            "result_url": f"/api/v1/workflow/result/{task.id}",
        }
    except Exception as e:
        logger.error("Failed to start workflow task", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start workflow execution")


@router.get("/status/{task_id}")
async def get_workflow_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the status of a workflow execution"""
    task = AsyncResult(task_id, app=execute_workflow_task.app)

    if task.state == "PENDING":
        return {"status": "pending", "info": "Task is waiting to be processed"}

    if task.state == "FAILURE":
        return {"status": "failed", "info": str(task.info)}

    return {"status": task.state, "info": task.info}


@router.get("/result/{task_id}")
async def get_workflow_result(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the result of a completed workflow execution"""
    task = AsyncResult(task_id, app=execute_workflow_task.app)

    if not task.ready():
        raise HTTPException(status_code=404, detail="Task not yet completed or does not exist")

    if task.state == "FAILURE":
        raise HTTPException(status_code=500, detail="Task failed during execution")

    return task.result

