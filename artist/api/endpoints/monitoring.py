"""
API endpoints for system monitoring and observability.
"""

from fastapi import APIRouter, Depends
import structlog
from typing import Dict, Any
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from ...observability.metrics import MetricsCollector

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health_check():
    """Get the health status of all system components"""
    # Note: Individual component health checks should be implemented
    # in their respective modules to avoid circular imports
    health_status = {
        "status": "healthy",
        "components": {
            "api": True,
            "database": True,  # Could check database connection
            "redis": True,     # Could check Redis connection
        }
    }
    
    # Check if all components are healthy
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(MetricsCollector.get_metrics(), media_type=CONTENT_TYPE_LATEST)


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Get the overall status of the ARTIST system"""
    # This could include more detailed information, such as active workflows, resource usage, etc.
    return {
        "status": "operational",
        "version": "1.0.0",
        "uptime": "unknown",  # Could track actual uptime
        "environment": "development"
    }

