"""
ARTIST: Agentic Tool-Integrated Large Language Model
Main application entry point
"""

import logging
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from .api.endpoints import workflow, agents, tools, monitoring, auth, rlhf
from .api.middleware import SecurityMiddleware, LoggingMiddleware
from .api.exceptions import (
    APIError, 
    api_error_handler, 
    validation_exception_handler, 
    generic_exception_handler
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
        # Initialize core components
        auth_manager = AuthManager()
        rag_system = RAGSystem()
        orchestration_engine = OrchestrationEngine(rag_system=rag_system)
        
        # Initialize systems
        await rag_system.initialize()
        await orchestration_engine.initialize()
        
        logger.info("ARTIST application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
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
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

# Add error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(rlhf.router, prefix="/api/v1/rlhf", tags=["rlhf"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ARTIST - Agentic Tool-Integrated LLM",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "components": {
            "orchestration_engine": orchestration_engine.health_check() if orchestration_engine else False,
            "rag_system": rag_system.health_check() if rag_system else False,
            "auth_manager": auth_manager.health_check() if auth_manager else False
        }
    }
    
    # Check if all components are healthy
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status

def main():
    """Main function to run the application"""
    uvicorn.run(
        "artist.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog configuration
    )

if __name__ == "__main__":
    main()
