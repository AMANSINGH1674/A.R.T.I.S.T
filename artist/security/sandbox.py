"""
Secure code execution sandbox with enhanced security measures.
"""

import docker
import asyncio
import tempfile
import os
import structlog
from typing import Dict, Any
import uuid

logger = structlog.get_logger()


class SecureCodeSandbox:
    """Secure code execution using Docker containers"""

    def __init__(self, timeout: int = 30, memory_limit: str = "128m"):
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.docker_client = docker.from_env()

    async def execute_python_code(self, code: str, user_id: str = None) -> Dict[str, Any]:
        """Execute Python code in a secure Docker container"""
        execution_id = str(uuid.uuid4())
        logger.info("Starting secure code execution", execution_id=execution_id, user_id=user_id)

        # Validate the code for dangerous operations
        if self._is_dangerous_code(code):
            return {
                "success": False,
                "error": "Code contains potentially dangerous operations",
                "output": "",
                "execution_time": 0
            }

        result = {
            "success": False,
            "output": "",
            "error": "",
            "execution_time": 0
        }

        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file_path = f.name

        try:
            import time
            start_time = time.time()

            # Run code in Docker container
            container = self.docker_client.containers.run(
                "python:3.11-alpine",  # Minimal Python image
                command=f"python /code/{os.path.basename(temp_file_path)}",
                volumes={
                    os.path.dirname(temp_file_path): {
                        'bind': '/code',
                        'mode': 'ro'  # Read-only
                    }
                },
                mem_limit=self.memory_limit,
                network_disabled=True,  # No network access
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                timeout=self.timeout,
                user="nobody",  # Run as non-root user
                security_opt=["no-new-privileges"],  # Prevent privilege escalation
                read_only=True,  # Read-only filesystem
                tmpfs={"/tmp": "noexec,nosuid,size=100m"}  # Temporary filesystem with restrictions
            )

            execution_time = time.time() - start_time

            result.update({
                "success": True,
                "output": container.decode('utf-8') if container else "",
                "execution_time": execution_time
            })

            logger.info("Code execution completed successfully", 
                       execution_id=execution_id,
                       execution_time=execution_time)

        except docker.errors.ContainerError as e:
            result["error"] = f"Container error: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
            logger.error("Container execution failed", 
                        execution_id=execution_id, 
                        error=str(e))

        except Exception as e:
            result["error"] = f"Execution failed: {str(e)}"
            logger.error("Code execution failed", 
                        execution_id=execution_id, 
                        error=str(e))

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

        return result

    def _is_dangerous_code(self, code: str) -> bool:
        """Check for potentially dangerous code patterns"""
        dangerous_patterns = [
            "import os",
            "import subprocess",
            "import sys",
            "import socket",
            "import urllib",
            "import requests",
            "import http",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",
            "file(",
            "input(",
            "raw_input(",
            "exit(",
            "quit(",
            "globals(",
            "locals(",
            "vars(",
            "dir(",
            "delattr",
            "setattr",
            "getattr",
            "hasattr"
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                logger.warning("Dangerous code pattern detected", pattern=pattern)
                return True

        return False

    def get_allowed_modules(self):
        """Get list of allowed Python modules"""
        return [
            "math",
            "random",
            "datetime",
            "json",
            "re",
            "string",
            "collections",
            "itertools",
            "functools",
            "operator",
            "statistics",
            "numpy",
            "pandas",
            "matplotlib.pyplot"
        ]
