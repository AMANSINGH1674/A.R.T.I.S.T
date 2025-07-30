"""
API endpoints for workflow management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import structlog
from typing import Dict, Any, Optional
from celery.result import AsyncResult

from ...worker.tasks import execute_workflow_task
from ...security.auth import get_current_user

router = APIRouter()
logger = structlog.get_logger()


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow"""
    user_request: str = Field(..., description="The user's request or prompt")
    workflow_id: str = Field(default="default", description="The ID of the workflow to execute")
    metadata: Dict[str, Any] = Field(default={}, description="Optional metadata for the request")


class WorkflowExecutionResponse(BaseModel):
    """Response model for starting a workflow execution"""
    task_id: str = Field(..., description="The ID of the asynchronous task")
    status_url: str = Field(..., description="URL to check the status of the task")
    result_url: str = Field(..., description="URL to retrieve the result of the task")


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def start_workflow(
    request: WorkflowExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start a new workflow execution asynchronously"""
    logger.info("Received workflow execution request", 
                user_request=request.user_request, 
                user_id=current_user.get("username"))
    
    try:
        task = execute_workflow_task.delay(
            user_request=request.user_request,
            workflow_id=request.workflow_id,
            metadata=request.metadata,
            user_id=current_user.get("username")
        )
        
        return {
            "task_id": task.id,
            "status_url": f"/api/v1/workflow/status/{task.id}",
            "result_url": f"/api/v1/workflow/result/{task.id}"
        }
    except Exception as e:
        logger.error("Failed to start workflow task", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start workflow execution")


@router.get("/status/{task_id}")
async def get_workflow_status(task_id: str):
    """Get the status of a workflow execution"""
    task = AsyncResult(task_id, app=execute_workflow_task.app)
    
    if task.state == 'PENDING':
        return {"status": "pending", "info": "Task is waiting to be processed"}
    
    if task.state == 'FAILURE':
        return {"status": "failed", "info": str(task.info)}
    
    return {"status": task.state, "info": task.info}


@router.get("/result/{task_id}")
async def get_workflow_result(task_id: str):
    """Get the result of a completed workflow execution"""
    task = AsyncResult(task_id, app=execute_workflow_task.app)
    
    if not task.ready():
        raise HTTPException(status_code=404, detail="Task not yet completed or does not exist")
    
    if task.state == 'FAILURE':
        raise HTTPException(status_code=500, detail=f"Task failed with error: {task.info}")
    
    return task.result

