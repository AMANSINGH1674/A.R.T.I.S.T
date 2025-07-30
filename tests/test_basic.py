"""
Basic tests for the ARTIST system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from artist.orchestration.state import create_initial_state
from artist.orchestration.engine import OrchestrationEngine
from artist.knowledge.rag import RAGSystem
from artist.agents.research import ResearchAgent
from artist.agents.synthesis import SynthesisAgent
from artist.agents.fact_check import FactCheckAgent


class TestWorkflowState:
    """Test workflow state management"""

    def test_create_initial_state(self):
        """Test creating an initial workflow state"""
        state = create_initial_state(
            user_request="Test request",
            workflow_id="test_workflow"
        )
        
        assert state["user_request"] == "Test request"
        assert state["workflow_id"] == "test_workflow"
        assert state["status"] == "running"
        assert len(state["history"]) == 0
        assert len(state["completed_steps"]) == 0


class TestOrchestrationEngine:
    """Test orchestration engine"""

    @pytest.fixture
    def mock_rag_system(self):
        """Create a mock RAG system"""
        rag_system = Mock(spec=RAGSystem)
        rag_system.health_check.return_value = True
        return rag_system

    def test_engine_initialization(self, mock_rag_system):
        """Test engine initialization"""
        engine = OrchestrationEngine(rag_system=mock_rag_system)
        assert engine.rag_system == mock_rag_system
        assert isinstance(engine.workflows, dict)
        assert isinstance(engine.running_workflows, dict)

    def test_load_workflow_definitions(self, mock_rag_system):
        """Test loading workflow definitions"""
        engine = OrchestrationEngine(rag_system=mock_rag_system)
        engine.load_workflow_definitions()
        
        assert "default" in engine.workflow_definitions
        definition = engine.workflow_definitions["default"]
        assert "nodes" in definition
        assert "edges" in definition
        assert "entry_point" in definition
        assert "end_point" in definition


class TestAgents:
    """Test agents"""

    @pytest.fixture
    def mock_rag_system(self):
        """Create a mock RAG system"""
        rag_system = Mock(spec=RAGSystem)
        rag_system.search.return_value = [
            {
                "text": "Sample document content",
                "metadata": {"source": "test_source"},
                "score": 0.95
            }
        ]
        return rag_system

    @pytest.mark.asyncio
    async def test_research_agent(self, mock_rag_system):
        """Test research agent execution"""
        agent = ResearchAgent(rag_system=mock_rag_system)
        state = create_initial_state("Test research request")
        
        result_state = await agent.execute(state)
        
        assert "research" in result_state["completed_steps"]
        assert "research" in result_state["intermediate_results"]
        assert len(result_state["retrieved_documents"]) > 0

    @pytest.mark.asyncio
    async def test_synthesis_agent(self):
        """Test synthesis agent execution"""
        agent = SynthesisAgent()
        state = create_initial_state("Test synthesis request")
        state["retrieved_documents"] = [
            {"text": "Test document", "metadata": {"source": "test"}}
        ]
        
        result_state = await agent.execute(state)
        
        assert "synthesis" in result_state["completed_steps"]
        assert "synthesis" in result_state["intermediate_results"]

    @pytest.mark.asyncio
    async def test_fact_check_agent(self):
        """Test fact-check agent execution"""
        agent = FactCheckAgent()
        state = create_initial_state("Test fact-check request")
        state["intermediate_results"]["synthesis"] = {
            "confidence_score": 0.8,
            "sources_used": 5
        }
        
        result_state = await agent.execute(state)
        
        assert "fact_check" in result_state["completed_steps"]
        assert "fact_check" in result_state["intermediate_results"]
        fact_check_result = result_state["intermediate_results"]["fact_check"]
        assert "verified" in fact_check_result
        assert "confidence_score" in fact_check_result


if __name__ == "__main__":
    pytest.main([__file__])
