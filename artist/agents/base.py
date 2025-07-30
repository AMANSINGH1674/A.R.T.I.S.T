"""
Base classes for agents in the ARTIST system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import structlog

from ..tools.base import BaseTool
from ..orchestration.state import WorkflowState

logger = structlog.get_logger()

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(
        self,
        name: str,
        description: str,
        tools: Optional[List[BaseTool]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.tools = tools or []
        self.llm_config = llm_config or {}
        self.logger = logger.bind(agent_name=self.name)

    @abstractmethod
    async def execute(
        self, state: WorkflowState, **kwargs: Any
    ) -> WorkflowState:
        """Execute the agent's logic and return the updated state"""
        pass

    def add_tool(self, tool: BaseTool):
        """Adds a tool to the agent's toolset"""
        if tool not in self.tools:
            self.tools.append(tool)
            self.logger.info(f"Added tool '{tool.name}' to agent '{self.name}'")

    def remove_tool(self, tool_name: str):
        """Removes a tool from the agent's toolset"""
        initial_tool_count = len(self.tools)
        self.tools = [t for t in self.tools if t.name != tool_name]
        if len(self.tools) < initial_tool_count:
            self.logger.info(f"Removed tool '{tool_name}' from agent '{self.name}'")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Gets a tool by its name"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', description='{self.description}')>"
