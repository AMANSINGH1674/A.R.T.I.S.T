"""
Code execution tool for running Python code in a sandboxed environment.
"""

import asyncio
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
import structlog
from typing import Dict, Any

from .base import BaseTool

logger = structlog.get_logger()


class CodeExecutionTool(BaseTool):
    """Tool for executing Python code in a sandboxed environment"""

    def __init__(self, timeout: int = 30):
        super().__init__(
            name="code_execution",
            description="Execute Python code in a sandboxed environment"
        )
        self.timeout = timeout

    async def execute(self, code: str) -> Dict[str, Any]:
        """Execute Python code and return the result"""
        self.logger.info("Executing Python code")
        
        # Prepare execution environment
        exec_globals = {
            "__builtins__": {
                # Safe builtins only
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "round": round,
            }
        }
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = {
            "success": False,
            "output": "",
            "error": "",
            "execution_time": 0
        }
        
        try:
            import time
            start_time = time.time()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Use asyncio.wait_for to enforce timeout
                await asyncio.wait_for(
                    self._safe_exec(code, exec_globals),
                    timeout=self.timeout
                )
            
            execution_time = time.time() - start_time
            
            result.update({
                "success": True,
                "output": stdout_capture.getvalue(),
                "execution_time": execution_time
            })
                        
            self.logger.info("Code execution completed successfully", 
                           execution_time=execution_time)
            
        except asyncio.TimeoutError:
            result["error"] = f"Code execution timed out after {self.timeout} seconds"
            self.logger.warning("Code execution timed out")
            
        except Exception as e:
            result["error"] = str(e)
            stderr_output = stderr_capture.getvalue()
            if stderr_output:
                result["error"] += f"\n{stderr_output}"
            self.logger.error("Code execution failed", error=str(e))
        
        return result

    async def _safe_exec(self, code: str, exec_globals: Dict[str, Any]):
        """Safely execute code in a controlled environment"""
        # Execute the code in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, exec, code, exec_globals)
