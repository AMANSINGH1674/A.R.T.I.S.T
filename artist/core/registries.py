"""
Dynamic registries for agents and tools.
"""

import importlib
from typing import Dict, Type
import structlog
from sqlalchemy.orm import Session

from ..agents.base import BaseAgent
from ..tools.base import BaseTool
from ..database.models import AgentRegistry as AgentModel, ToolRegistry as ToolModel

logger = structlog.get_logger()


class AgentRegistry:
    """Dynamically loads and manages agents from a database registry"""

    def __init__(self, db_session: Session):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._db_session = db_session
        self.load_agents_from_db()

    def load_agents_from_db(self):
        """Load agents from the database"""
        try:
            agents_from_db = self._db_session.query(AgentModel).filter(AgentModel.is_active == True).all()
            for agent_info in agents_from_db:
                self.register_agent(agent_info.name, agent_info.class_path)
        except Exception as e:
            logger.error("Failed to load agents from database", error=str(e))

    def register_agent(self, name: str, class_path: str):
        """Register an agent by its class path"""
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            if issubclass(agent_class, BaseAgent):
                self._agents[name] = agent_class
                logger.info("Registered agent", name=name, class_path=class_path)
            else:
                logger.warning(f"Class {class_path} is not a subclass of BaseAgent")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to register agent '{name}'", error=str(e))

    def get_agent(self, name: str, **kwargs) -> BaseAgent:
        """Get an instance of a registered agent"""
        agent_class = self._agents.get(name)
        if agent_class:
            return agent_class(**kwargs)
        else:
            raise ValueError(f"Agent '{name}' not found in registry")

    def list_agents(self) -> Dict[str, Type[BaseAgent]]:
        """List all registered agents"""
        return self._agents


class ToolRegistry:
    """Dynamically loads and manages tools from a database registry"""

    def __init__(self, db_session: Session):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._db_session = db_session
        self.load_tools_from_db()

    def load_tools_from_db(self):
        """Load tools from the database"""
        try:
            tools_from_db = self._db_session.query(ToolModel).filter(ToolModel.is_active == True).all()
            for tool_info in tools_from_db:
                self.register_tool(tool_info.name, tool_info.class_path)
        except Exception as e:
            logger.error("Failed to load tools from database", error=str(e))

    def register_tool(self, name: str, class_path: str):
        """Register a tool by its class path"""
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            if issubclass(tool_class, BaseTool):
                self._tools[name] = tool_class
                logger.info("Registered tool", name=name, class_path=class_path)
            else:
                logger.warning(f"Class {class_path} is not a subclass of BaseTool")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to register tool '{name}'", error=str(e))

    def get_tool(self, name: str, **kwargs) -> BaseTool:
        """Get an instance of a registered tool"""
        tool_class = self._tools.get(name)
        if tool_class:
            return tool_class(**kwargs)
        else:
            raise ValueError(f"Tool '{name}' not found in registry")

    def list_tools(self) -> Dict[str, Type[BaseTool]]:
        """List all registered tools"""
        return self._tools

