"""
API endpoints for RLHF training system.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import structlog
from typing import Dict, Any
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...security.auth import get_current_user
from ...rlhf.trainer import TrainingOrchestrator
from ...rlhf.feedback import router as feedback_router

router = APIRouter()
logger = structlog.get_logger()

# Include the feedback router
router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])


class TrainingRequest(BaseModel):
    """Request model for triggering training"""
    training_type: str  # "reward_model", "policy_optimization", "full_cycle"
    agent_name: str = None


@router.post("/train")
async def trigger_training(
    request: TrainingRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Trigger RLHF training cycle"""
    
    # Check if user has admin permissions
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    
    trainer = TrainingOrchestrator(db)
    
    try:
        if request.training_type == "full_cycle":
            await trainer.run_training_cycle()
            return {"status": "success", "message": "Full training cycle completed"}
        
        elif request.training_type == "reward_model":
            feedback_list = trainer._collect_feedback_from_db()
            reward_model = await trainer.train_reward_model(feedback_list)
            return {"status": "success", "message": "Reward model training completed"}
        
        elif request.training_type == "policy_optimization":
            if not request.agent_name:
                raise HTTPException(
                    status_code=400, 
                    detail="Agent name required for policy optimization"
                )
            # Load reward model and optimize policy
            # This is a placeholder - in a real system you'd load the trained reward model
            result = await trainer.optimize_policy(request.agent_name, None)
            return {"status": "success", "message": f"Policy optimization completed for {request.agent_name}"}
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid training type"
            )
    
    except Exception as e:
        logger.error("Training failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/training/status")
async def get_training_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get training status"""
    # This would typically track ongoing training jobs
    return {
        "status": "idle",
        "last_training": "2023-12-01T10:00:00Z",
        "reward_model_version": "1.0",
        "agents_trained": ["research", "synthesis"]
    }
