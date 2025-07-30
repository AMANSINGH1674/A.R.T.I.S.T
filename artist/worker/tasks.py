"""
Celery tasks for executing workflows asynchronously.
"""

import asyncio
import structlog
from celery import current_task
from typing import Dict, Any

from .celery_app import celery_app
from ..orchestration.engine import OrchestrationEngine
from ..orchestration.state import create_initial_state
from ..knowledge.rag import RAGSystem

logger = structlog.get_logger()


@celery_app.task(bind=True)
def execute_workflow_task(
    self, 
    user_request: str, 
    workflow_id: str = "default", 
    metadata: Dict[str, Any] = None,
    user_id: str = None
):
    """
    Execute a workflow asynchronously.
    
    Args:
        self: Celery task instance
        user_request: The user's request
        workflow_id: ID of the workflow to execute
        metadata: Additional metadata
        user_id: ID of the user making the request
    
    Returns:
        Dict containing the workflow execution result
    """
    logger.info("Starting asynchronous workflow execution", 
                task_id=self.request.id, 
                workflow_id=workflow_id,
                user_id=user_id)
    
    try:
        # Update task status
        self.update_state(state='PROCESSING', meta={'status': 'Initializing workflow...'})
        
        # Initialize components (in a production system, these would be injected or cached)
        rag_system = RAGSystem()
        orchestration_engine = OrchestrationEngine(rag_system=rag_system)
        
        # Initialize systems in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(rag_system.initialize())
            loop.run_until_complete(orchestration_engine.initialize())
            
            # Create initial state
            initial_state = create_initial_state(
                user_request=user_request,
                workflow_id=workflow_id,
                metadata=metadata or {},
                user_id=user_id
            )
            
            # Update task status
            self.update_state(state='PROCESSING', meta={'status': 'Executing workflow...'})
            
            # Execute workflow
            final_state = loop.run_until_complete(
                orchestration_engine.execute_workflow(workflow_id, initial_state)
            )
            
            # Clean up
            loop.run_until_complete(orchestration_engine.shutdown())
            loop.run_until_complete(rag_system.shutdown())
            
        finally:
            loop.close()
        
        logger.info("Workflow execution completed successfully", 
                   task_id=self.request.id,
                   workflow_id=workflow_id)
        
        return {
            "status": "completed",
            "result": final_state,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error("Workflow execution failed", 
                    task_id=self.request.id,
                    error=str(e))
        
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'status': 'Workflow execution failed'
            }
        )
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }
