"""
Centralized error handling for ARTIST API.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog
from typing import Dict, Any, Optional
from enum import Enum

logger = structlog.get_logger()

class ErrorCode(str, Enum):
    """Standard error codes"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    AGENT_ERROR = "AGENT_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class APIError(Exception):
    """Base API error"""
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode, 
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(APIError):
    """Validation error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 422, details)

class AuthenticationError(APIError):
    """Authentication error"""
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.AUTHENTICATION_ERROR, 401, details)

class AuthorizationError(APIError):
    """Authorization error"""
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.AUTHORIZATION_ERROR, 403, details)

class ResourceNotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(message, ErrorCode.RESOURCE_NOT_FOUND, 404)

class WorkflowError(APIError):
    """Workflow execution error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.WORKFLOW_ERROR, 500, details)

class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.RATE_LIMIT_ERROR, 429, details)

def format_error_response(error: APIError, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Format error response"""
    response = {
        "error": {
            "code": error.error_code.value,
            "message": error.message,
            "status_code": error.status_code
        }
    }
    
    if error.details:
        response["error"]["details"] = error.details
    
    if request_id:
        response["request_id"] = request_id
    
    return response

async def api_error_handler(request: Request, exc: APIError):
    """Handle API errors"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        "API error occurred",
        error_code=exc.error_code.value,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc, request_id)
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        request_id=request_id,
        path=request.url.path
    )
    
    api_error = ValidationError(
        "Request validation failed",
        details={"validation_errors": exc.errors()}
    )
    
    return JSONResponse(
        status_code=422,
        content=format_error_response(api_error, request_id)
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=request_id,
        path=request.url.path
    )
    
    api_error = APIError(
        "An unexpected error occurred",
        ErrorCode.INTERNAL_ERROR,
        500
    )
    
    return JSONResponse(
        status_code=500,
        content=format_error_response(api_error, request_id)
    )
