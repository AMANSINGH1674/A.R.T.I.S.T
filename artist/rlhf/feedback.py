"""
Feedback collection service and API endpoint.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..database.session import get_db
from ..database.models import User, WorkflowExecution, AuditLog
from .base import HumanFeedback, FeedbackType
from ..security.auth import get_current_user

router = APIRouter()
logger = structlog.get_logger()


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback"""
    workflow_id: str
    run_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)
    text_feedback: Optional[str] = None
    comparison_preference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FeedbackService:
    """Service for collecting and processing user feedback"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def save_feedback(self, feedback: HumanFeedback, user: Dict[str, Any]):
        """Save human feedback to the database"""
        try:
            # In a real system, you would store this in a dedicated feedback table
            # For now, we'll log it and associate it with the workflow execution
            workflow_execution = (
                self.db.query(WorkflowExecution)
                .filter(WorkflowExecution.id == feedback.run_id)
                .first()
            )

            if not workflow_execution:
                raise HTTPException(status_code=404, detail="Workflow execution not found")
            
            # Mutating a JSON column in-place is not tracked by SQLAlchemy —
            # reassign the whole dict and call flag_modified so the change is flushed.
            metadata = dict(workflow_execution.request_metadata or {})
            existing_feedback = list(metadata.get("feedback") or [])

            feedback_data = {
                k: (v.value if hasattr(v, "value") else v)
                for k, v in feedback.__dict__.items()
            }
            feedback_data["user_id"] = user["id"]
            feedback_data["timestamp"] = datetime.now(timezone.utc).isoformat()

            existing_feedback.append(feedback_data)
            metadata["feedback"] = existing_feedback
            workflow_execution.request_metadata = metadata
            flag_modified(workflow_execution, "request_metadata")
            
            # Log the feedback
            audit_log = AuditLog(
                user_id=user["id"],
                action="submit_feedback",
                resource_type="workflow_execution",
                resource_id=feedback.run_id,
                details=feedback_data,
                ip_address=user.get("ip_address")
            )
            self.db.add(audit_log)
            self.db.commit()

            logger.info("Feedback saved successfully", 
                        run_id=feedback.run_id,
                        feedback_type=feedback.feedback_type.value)

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to save feedback", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to save feedback")


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit feedback for a workflow execution"""
    feedback_service = FeedbackService(db)
    
    feedback = HumanFeedback(
        workflow_id=request.workflow_id,
        run_id=request.run_id,
        user_id=current_user["username"],
        feedback_type=request.feedback_type,
        rating=request.rating,
        text_feedback=request.text_feedback,
        comparison_preference=request.comparison_preference,
        metadata=request.metadata or {}
    )
    
    await feedback_service.save_feedback(feedback, current_user)
    
    return {"status": "success", "message": "Feedback submitted successfully"}
