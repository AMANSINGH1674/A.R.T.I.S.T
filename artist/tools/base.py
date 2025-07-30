"""
Base class for tools in the ARTIST system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class BaseTool(ABC):
    """Abstract base class for all tools"""

    def __init__(
        self,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.config = config or {}
        self.logger = logger.bind(tool_name=self.name)

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with provided arguments"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', description='{self.description}')>"

