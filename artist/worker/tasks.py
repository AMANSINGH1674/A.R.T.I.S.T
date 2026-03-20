"""
Celery tasks for executing workflows asynchronously.
"""

import asyncio
import structlog
from typing import Dict, Any, Optional

from .celery_app import celery_app
from ..orchestration.engine import OrchestrationEngine
from ..orchestration.state import create_initial_state
from ..knowledge.rag import RAGSystem
from ..database.session import SessionLocal
from ..core.memory import MemoryService

logger = structlog.get_logger()


@celery_app.task(bind=True)
def execute_workflow_task(
    self,
    user_request: str,
    workflow_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
):
    """
    Execute a workflow asynchronously via Celery.

    Retrieves the user's conversation history before execution and persists
    the new exchange afterward — enabling long-term memory across sessions.
    """
    logger.info(
        "Starting async workflow execution",
        task_id=self.request.id,
        workflow_id=workflow_id,
        user_id=user_id,
    )

    try:
        self.update_state(state="PROCESSING", meta={"status": "Initializing workflow..."})

        rag_system = RAGSystem()
        orchestration_engine = OrchestrationEngine(rag_system=rag_system)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(rag_system.initialize())
            loop.run_until_complete(orchestration_engine.initialize())

            # --- Long-term memory: retrieve history before execution ---
            conversation_history = []
            db = SessionLocal()
            try:
                if user_id:
                    memory_service = MemoryService(db)
                    conversation_history = memory_service.get_history(user_id)
                    logger.info(
                        "Injecting conversation history",
                        user_id=user_id,
                        turns=len(conversation_history),
                    )
            finally:
                db.close()

            initial_state = create_initial_state(
                user_request=user_request,
                workflow_id=workflow_id,
                metadata=metadata or {},
                user_id=user_id,
                conversation_history=conversation_history,
            )

            self.update_state(state="PROCESSING", meta={"status": "Executing workflow..."})

            final_state = loop.run_until_complete(
                orchestration_engine.execute_workflow(workflow_id, initial_state)
            )

            # --- Long-term memory: persist this exchange ---
            if user_id and final_state.get("final_output"):
                db = SessionLocal()
                try:
                    memory_service = MemoryService(db)
                    assistant_reply = final_state["final_output"].get("summary", "")
                    memory_service.save_turn(
                        user_id=user_id,
                        run_id=final_state.get("run_id", self.request.id),
                        user_message=user_request,
                        assistant_message=assistant_reply,
                    )
                finally:
                    db.close()

            loop.run_until_complete(orchestration_engine.shutdown())
            loop.run_until_complete(rag_system.shutdown())

        finally:
            loop.close()

        logger.info("Workflow execution completed", task_id=self.request.id)
        return {
            "status": "completed",
            "result": final_state,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error("Workflow execution failed", task_id=self.request.id, error=str(e))
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id,
        }
