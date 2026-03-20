"""
ARTIST: Agentic Tool-Integrated Large Language Model
Main application entry point
"""

import os
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn

from .api.endpoints import workflow, agents, tools, monitoring, auth, rlhf, knowledge
from .api.endpoints.knowledge import set_rag_system
from .api.middleware import SecurityMiddleware, LoggingMiddleware
from .api.exceptions import (
    APIError,
    api_error_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from .orchestration.engine import OrchestrationEngine
from .knowledge.rag import RAGSystem
from .security.auth import AuthManager
from .core.logging_config import configure_logging
from .core.rate_limiter import RateLimitMiddleware
from .database.session import create_all_tables
from .config import settings

configure_logging(log_level=settings.log_level, log_format=settings.log_format)
logger = structlog.get_logger(__name__)

# Global components
orchestration_engine = None
rag_system = None
auth_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global orchestration_engine, rag_system, auth_manager

    logger.info("Starting ARTIST application...")

    try:
        # Validate LLM provider configuration before anything else
        provider = settings.default_llm_provider.lower()
        if provider == "nim" and not settings.nvidia_api_key:
            raise ValueError("DEFAULT_LLM_PROVIDER=nim but NVIDIA_API_KEY is not set in .env")
        if provider == "openai" and not settings.openai_api_key:
            raise ValueError("DEFAULT_LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env")
        if provider == "anthropic" and not settings.anthropic_api_key:
            raise ValueError("DEFAULT_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set in .env")

        emb_provider = settings.embedding_provider.lower()
        if emb_provider == "nim" and not settings.nvidia_api_key:
            raise ValueError("EMBEDDING_PROVIDER=nim but NVIDIA_API_KEY is not set in .env")
        if emb_provider == "openai" and not settings.openai_api_key:
            raise ValueError("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set in .env")

        create_all_tables()

        auth_manager = AuthManager()
        rag_system = RAGSystem()
        orchestration_engine = OrchestrationEngine(rag_system=rag_system)

        await rag_system.initialize()
        await orchestration_engine.initialize()

        # Make rag_system available to the knowledge upload endpoint
        set_rag_system(rag_system)

        logger.info("ARTIST application started successfully")

        yield

    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    finally:
        logger.info("Shutting down ARTIST application...")
        if orchestration_engine:
            await orchestration_engine.shutdown()
        if rag_system:
            await rag_system.shutdown()


# Create FastAPI application
app = FastAPI(
    title="ARTIST - Agentic Tool-Integrated LLM",
    description="Multi-agent orchestration system for complex workflow automation",
    version=settings.app_version,
    lifespan=lifespan,
    # Disable docs in production
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS — allow_origins must be explicit when allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

# Error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Static files — only mount if the directory exists
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(rlhf.router, prefix="/api/v1/rlhf", tags=["rlhf"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])


@app.get("/")
async def root():
    """Serve the main UI"""
    index = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    return FileResponse(index)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    import redis as _redis

    # Check Redis
    redis_ok = False
    try:
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    # Check Celery
    celery_ok = False
    try:
        from .worker.celery_app import celery_app
        celery_app.control.ping(timeout=1)
        celery_ok = True
    except Exception:
        pass

    components = {
        "orchestration_engine": orchestration_engine.health_check() if orchestration_engine else False,
        "rag_system": rag_system.health_check() if rag_system else False,
        "auth_manager": auth_manager.health_check() if auth_manager else False,
        "redis": redis_ok,
        "celery": celery_ok,
    }

    all_healthy = all(components.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": components,
    }


def main():
    """Main function to run the application"""
    uvicorn.run(
        "artist.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_config=None,  # Use structlog configuration
    )


if __name__ == "__main__":
    main()
