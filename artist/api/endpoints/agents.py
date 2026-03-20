"""
API endpoints for agent management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog
from typing import List, Dict, Any

from ...security.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter()


class AgentInfo(BaseModel):
    """Model for agent information"""
    name: str
    description: str
    status: str
    tools: List[str] = []


@router.get("/list")
async def list_agents(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[AgentInfo]:
    """List all available agents"""
    return [
        AgentInfo(
            name="research",
            description="Conducts research and information gathering",
            status="active",
            tools=["web_search", "document_retrieval"],
        ),
        AgentInfo(
            name="synthesis",
            description="Synthesizes information from multiple sources",
            status="active",
            tools=["text_summarization", "data_analysis"],
        ),
        AgentInfo(
            name="fact_check",
            description="Verifies facts and checks accuracy",
            status="active",
            tools=["fact_verification", "source_validation"],
        ),
        AgentInfo(
            name="final_output",
            description="Formats and delivers final results",
            status="active",
            tools=["report_generation", "visualization"],
        ),
    ]


@router.get("/{agent_name}")
async def get_agent(
    agent_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AgentInfo:
    """Get information about a specific agent"""
    agents = await list_agents(current_user)
    for agent in agents:
        if agent.name == agent_name:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")


@router.get("/{agent_name}/status")
async def get_agent_status(
    agent_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the status of a specific agent"""
    # Validate agent exists first
    await get_agent(agent_name, current_user)
    return {
        "agent_name": agent_name,
        "status": "healthy",
        "success_rate": 0.95,
        "average_execution_time": 2.3,
    }
