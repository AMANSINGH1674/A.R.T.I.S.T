"""
LangSmith integration for tracing and debugging agent actions.
"""

import os
from typing import Dict, Any, Optional
import structlog
from langsmith import Client
from langsmith.run_trees import RunTree
from contextlib import asynccontextmanager

from ..config import settings

logger = structlog.get_logger()


class LangSmithTracer:
    """LangSmith tracing integration for ARTIST"""

    def __init__(self):
        self.client = None
        self.enabled = bool(settings.langsmith_api_key)
        if self.enabled:
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
            self.client = Client()
            logger.info("LangSmith tracing enabled", project=settings.langsmith_project)
        else:
            logger.info("LangSmith tracing disabled (no API key provided)")

    @asynccontextmanager
    async def trace_workflow(self, workflow_id: str, run_id: str, user_request: str):
        """Trace a complete workflow execution"""
        if not self.enabled:
            yield None
            return

        run_tree = RunTree(
            name=f"workflow_{workflow_id}",
            run_type="chain",
            inputs={"user_request": user_request, "workflow_id": workflow_id},
            extra={"run_id": run_id}
        )
        
        try:
            yield run_tree
        except Exception as e:
            run_tree.end(error=str(e))
            raise
        else:
            run_tree.end()
        finally:
            if run_tree:
                run_tree.post()

    @asynccontextmanager
    async def trace_agent(
        self, 
        agent_name: str, 
        inputs: Dict[str, Any], 
        parent_run: Optional[RunTree] = None
    ):
        """Trace an agent execution"""
        if not self.enabled:
            yield None
            return

        run_tree = RunTree(
            name=f"agent_{agent_name}",
            run_type="llm",
            inputs=inputs,
            parent=parent_run
        )
        
        try:
            yield run_tree
        except Exception as e:
            run_tree.end(error=str(e))
            raise
        else:
            run_tree.end()

    @asynccontextmanager
    async def trace_tool(
        self, 
        tool_name: str, 
        inputs: Dict[str, Any], 
        parent_run: Optional[RunTree] = None
    ):
        """Trace a tool execution"""
        if not self.enabled:
            yield None
            return

        run_tree = RunTree(
            name=f"tool_{tool_name}",
            run_type="tool",
            inputs=inputs,
            parent=parent_run
        )
        
        try:
            yield run_tree
        except Exception as e:
            run_tree.end(error=str(e))
            raise
        else:
            run_tree.end()

    def log_feedback(self, run_id: str, feedback: Dict[str, Any]):
        """Log human feedback to LangSmith"""
        if not self.enabled:
            return

        try:
            self.client.create_feedback(
                run_id=run_id,
                key="human_feedback",
                score=feedback.get("rating"),
                value=feedback.get("text_feedback"),
                comment=feedback.get("comment")
            )
            logger.info("Feedback logged to LangSmith", run_id=run_id)
        except Exception as e:
            logger.error("Failed to log feedback to LangSmith", error=str(e))


# Global tracer instance
langsmith_tracer = LangSmithTracer()
