"""
Middleware for handling security, logging, and other cross-cutting concerns.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import time

from ..security.auth import AuthManager

logger = structlog.get_logger()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for handling security and authentication"""

    def __init__(self, app):
        super().__init__(app)
        self.auth_manager = AuthManager()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/v1/monitoring/health") or \
           request.url.path.startswith("/api/v1/monitoring/metrics"):  # Public endpoints
            return await call_next(request)
        
        # Add authentication logic here if needed
        # For example, to verify a token from the header:
        # authorization: str = request.headers.get("Authorization")
        # if authorization:
        #     try:
        #         token_type, token = authorization.split()
        #         if token_type.lower() == "bearer":
        #             user = self.auth_manager.verify_token(token)
        #             request.state.user = user
        #     except Exception as e:
        #         logger.warning("Invalid token", error=str(e))
        
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        logger.info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        return response

