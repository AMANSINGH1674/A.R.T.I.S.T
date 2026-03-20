"""
API endpoints for system monitoring and observability.
"""

import time
from fastapi import APIRouter
import structlog
from typing import Dict, Any
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import Response

from ...observability.metrics import MetricsCollector
from ...config import settings

router = APIRouter()
logger = structlog.get_logger()

# Track process start time for uptime reporting
_START_TIME = time.time()


@router.get("/health")
async def health_check():
    """Get the health status of all system components"""
    import redis as _redis
    from sqlalchemy import text
    from ...database.session import engine

    # Database check
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Redis check
    redis_ok = False
    try:
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    components = {
        "api": True,
        "database": db_ok,
        "redis": redis_ok,
    }

    all_healthy = all(components.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": components,
    }


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(MetricsCollector.get_metrics(), media_type=CONTENT_TYPE_LATEST)


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Get the overall status of the ARTIST system"""
    uptime_seconds = int(time.time() - _START_TIME)
    return {
        "status": "operational",
        "version": settings.app_version,
        "uptime_seconds": uptime_seconds,
        "environment": settings.environment,
    }

