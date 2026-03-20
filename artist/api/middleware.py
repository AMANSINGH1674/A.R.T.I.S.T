"""
Middleware for handling security, logging, and other cross-cutting concerns.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import time
import uuid

from ..security.auth import auth_manager

logger = structlog.get_logger()

# Paths that do not require a JWT — auth and monitoring are open
_PUBLIC_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/monitoring/health",
    "/api/v1/monitoring/metrics",
    "/health",
    "/",
    "/static",
)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Adds security response headers and populates request.state.user when a
    valid JWT is present.  Does NOT block requests — auth enforcement happens at
    the endpoint level via the get_current_user dependency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Attach a correlation ID for tracing
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Opportunistically decode the JWT so downstream code can access the user
        # without hitting the DB again; errors are silently ignored here.
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization[7:]
            try:
                payload = auth_manager.verify_token(token)
                request.state.user_id = payload.get("sub")
            except Exception:
                request.state.user_id = None
        else:
            request.state.user_id = None

        response = await call_next(request)

        # Security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        logger.info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            request_id=getattr(request.state, "request_id", None),
            user_id=getattr(request.state, "user_id", None),
        )

        return response

