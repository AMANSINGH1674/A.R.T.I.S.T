"""
Synthesis agent for processing and combining information from multiple sources.
"""

import structlog
from typing import Dict, Any

from .base import BaseAgent
from ..orchestration.state import WorkflowState

logger = structlog.get_logger()

class SynthesisAgent(BaseAgent):
    """Agent specialized in synthesizing information from multiple sources"""

    def __init__(self):
        super().__init__(
            name="synthesis",
            description="Synthesizes and combines information from multiple sources into coherent insights"
        )

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        """Execute synthesis tasks and update the workflow state"""
        self.logger.info("Starting synthesis phase")
        
        try:
            # Get the retrieved documents from the research phase
            retrieved_documents = state.get("retrieved_documents", [])
            
            if not retrieved_documents:
                self.logger.warning("No documents available for synthesis")
                state["intermediate_results"]["synthesis"] = {
                    "status": "no_data",
                    "message": "No documents were available for synthesis"
                }
            else:
                # In a real implementation, this would use an LLM to synthesize the information
                # For now, we'll create a simple summary
                combined_text = " ".join([doc["text"][:200] for doc in retrieved_documents[:5]])
                
                synthesis_result = {
                    "summary": f"Based on {len(retrieved_documents)} sources, key findings include: {combined_text[:500]}...",
                    "sources_used": len(retrieved_documents),
                    "confidence_score": 0.85,
                    "key_points": [
                        "Information gathered from multiple sources",
                        "Cross-referenced for consistency",
                        "Synthesized into actionable insights"
                    ]
                }
                
                state["intermediate_results"]["synthesis"] = synthesis_result
                self.logger.info("Synthesis completed", sources_used=len(retrieved_documents))
            
            # Update execution tracking
            state["completed_steps"].append("synthesis")
            state["current_step"] = "synthesis"
            state["history"].append(f"Synthesis agent processed {len(retrieved_documents)} documents")
            
        except Exception as e:
            error_info = {
                "agent": self.name,
                "error": str(e),
                "step": "synthesis"
            }
            state["errors"].append(error_info)
            state["status"] = "failed"
            self.logger.error("Synthesis agent failed", error=str(e))
        
        return state
