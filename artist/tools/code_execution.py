"""
Code execution tool — delegates to the Docker-based SecureCodeSandbox.
The previous exec()-based approach was bypassable and is removed.
"""

import structlog
from typing import Dict, Any

from .base import BaseTool
from ..security.sandbox import SecureCodeSandbox

logger = structlog.get_logger()


class CodeExecutionTool(BaseTool):
    """Tool for executing Python code inside a Docker sandbox"""

    def __init__(self, timeout: int = 30, memory_limit: str = "128m"):
        super().__init__(
            name="code_execution",
            description="Execute Python code in a secure Docker sandbox",
        )
        self.sandbox = SecureCodeSandbox(timeout=timeout, memory_limit=memory_limit)

    async def execute(self, code: str, user_id: str = None) -> Dict[str, Any]:
        """Execute Python code and return the result"""
        self.logger.info("Executing Python code via sandbox", user_id=user_id)
        return await self.sandbox.execute_python_code(code, user_id=user_id)
