"""
Structured logging configuration for ARTIST application.
"""

import logging
import sys
import os
import structlog
from structlog.types import Processor


def configure_logging(
    log_level: str = "INFO", 
    log_format: str = "json", 
    service_name: str = "artist"
):
    """
    Configure structured logging for the application.
    
    Args:
        log_level (str): The minimum log level to output (e.g., "INFO", "DEBUG").
        log_format (str): The format of the logs ("json" or "console").
    """
    numeric_log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Define processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]
    
    if log_format == "json":
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_log_level)
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler)

    # Set service name for all logs
    structlog.contextvars.bind_contextvars(service=service_name)

    # Configure other loggers
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.error").disabled = True
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger with the specified name.
    
    Args:
        name (str): The name of the logger.
    
    Returns:
        structlog.stdlib.BoundLogger: A bound logger instance.
    """
    return structlog.get_logger(name)

