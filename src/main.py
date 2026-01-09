"""
TodoApp Backend API - FastAPI Application Entry Point.

This module initializes and configures the FastAPI application with all
necessary middleware, routes, and lifecycle event handlers.
"""

import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging

from src.config import settings
from src.database import close_db, init_db

# Configure structured logging
def get_logging_level(level_str: str) -> int:
    """Map string log level to logging module constant."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        get_logging_level(settings.log_level)
    ),
    context_class=dict,
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application,
    including database initialization and cleanup.

    Args:
        app: FastAPI application instance

    Yields:
        None: Control to the application

    Raises:
        Exception: If startup or shutdown fails
    """
    # Startup
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        port=settings.port,
    )

    try:
        # Initialize database (only in development)
        if settings.environment == "development":
            # Only initialize if we can connect to the database
            from sqlalchemy.ext.asyncio import create_async_engine
            temp_engine = create_async_engine(settings.get_database_url())
            async with temp_engine.connect() as conn:
                logger.info("database_connected_successfully")
            await temp_engine.dispose()

            await init_db()
            logger.info("database_initialized")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        # Don't exit on DB connection error in development, just warn
        logger.warning("Continuing without database connection")

    yield

    # Shutdown
    logger.info("application_shutdown")
    try:
        await close_db()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("database_cleanup_failed", error=str(e))


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-user Todo Application Backend API",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Add trusted host middleware for production
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # Configure with actual domains in production
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests with correlation IDs.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware or route handler

    Returns:
        Response from the next handler

    Raises:
        Exception: Any exception from downstream handlers
    """
    import time
    import uuid

    # Generate correlation ID for request tracing
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.time()

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=round(duration, 3),
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_seconds=round(duration, 3),
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Args:
        request: HTTP request that caused the exception
        exc: Exception that was raised

    Returns:
        JSON response with error details
    """
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint is used by Koyeb and other platforms to verify
    that the application is running and healthy.

    Returns:
        dict: Health status information

    Example:
        ```json
        {
            "status": "healthy",
            "version": "0.1.0"
        }
        ```
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/", status_code=status.HTTP_200_OK, tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint providing API information.

    Returns:
        dict: API information and documentation links

    Example:
        ```json
        {
            "message": "TodoApp API",
            "version": "0.1.0",
            "docs": "/docs"
        }
        ```
    """
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if not settings.is_production else "disabled",
    }


# Import and include API routers here
from src.api import auth, tasks

app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
