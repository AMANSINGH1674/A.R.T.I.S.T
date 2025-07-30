"""
Research agent for information gathering and retrieval.
"""

import structlog
from typing import Dict, Any

from .base import BaseAgent
from ..orchestration.state import WorkflowState
from ..knowledge.rag import RAGSystem

logger = structlog.get_logger()

class ResearchAgent(BaseAgent):
    """Agent specialized in conducting research and information gathering"""

    def __init__(self, rag_system: RAGSystem):
        super().__init__(
            name="research",
            description="Conducts research and information gathering using various sources"
        )
        self.rag_system = rag_system

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        """Execute research tasks and update the workflow state"""
        self.logger.info("Starting research phase", user_request=state["user_request"])
        
        try:
            # Extract the user's request
            user_request = state["user_request"]
            
            # Search the knowledge base for relevant information
            search_results = await self.rag_system.search(user_request, k=10)
            
            # Update the state with retrieved documents
            state["retrieved_documents"] = search_results
            state["intermediate_results"]["research"] = {
                "documents_found": len(search_results),
                "search_query": user_request,
                "top_sources": [doc["metadata"].get("source", "unknown") for doc in search_results[:3]]
            }
            
            # Update execution tracking
            state["completed_steps"].append("research")
            state["current_step"] = "research"
            state["history"].append(f"Research agent found {len(search_results)} relevant documents")
            
            self.logger.info("Research phase completed", documents_found=len(search_results))
            
        except Exception as e:
            error_info = {
                "agent": self.name,
                "error": str(e),
                "step": "research"
            }
            state["errors"].append(error_info)
            state["status"] = "failed"
            self.logger.error("Research agent failed", error=str(e))
        
        return state
