"""
FastAPI Application Entry Point

This module creates and configures the FastAPI application.

Key Concepts:
=============

1. Application Factory Pattern
   - create_app() function returns configured app
   - Easier to test (can create multiple instances)
   - Can configure differently for dev/test/prod

2. Lifespan Events
   - startup: Run before accepting requests (db connection, etc.)
   - shutdown: Clean up resources (close connections)
   - Uses async context manager in FastAPI 0.109+

3. Middleware Stack
   - CORS: Allow cross-origin requests
   - Security headers: Add protective headers
   - Request ID: Track requests for debugging

4. Exception Handlers
   - Convert database errors to HTTP responses
   - Standardize error format
   - Log errors for debugging
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.graphql import create_graphql_router
from app.routers import (
    api_keys_router,
    auth_router,
    authors_router,
    books_router,
    genres_router,
    recommendations_router,
    reviews_router,
    search_router,
    users_router,
)
from app.routers.websocket import router as websocket_router
from app.services.cache import close_redis_connection, get_cache_stats, get_redis_client
from app.services.elasticsearch import (
    close_elasticsearch,
    get_document_count,
    init_elasticsearch,
    is_elasticsearch_healthy,
)
from app.services.rate_limiter import limiter, rate_limit_exceeded_handler
from app.services.websocket import get_connection_manager

# =============================================================================
# Logging Configuration
# =============================================================================
# Configure logging before creating the app
settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Events
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    This replaces the old @app.on_event("startup") and @app.on_event("shutdown")
    decorators with a more Pythonic context manager approach.

    Code before yield: Runs on startup
    Code after yield: Runs on shutdown

    Usage:
        - Initialize database connections
        - Set up caching
        - Load configuration
        - Clean up resources on shutdown
    """
    # ----- STARTUP -----
    logger.info(f"Starting {settings.app_name}...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API version: {settings.api_version}")

    # Initialize Redis connection
    redis_client = get_redis_client()
    if redis_client:
        logger.info("Redis caching enabled")
    else:
        logger.warning("Redis unavailable - caching disabled")

    # Initialize Elasticsearch
    es_connected = await init_elasticsearch()
    if es_connected:
        logger.info("Elasticsearch connected - advanced search enabled")
    else:
        logger.warning("Elasticsearch unavailable - falling back to PostgreSQL search")

    yield  # Application runs here

    # ----- SHUTDOWN -----
    logger.info(f"Shutting down {settings.app_name}...")

    # Close Elasticsearch connection
    await close_elasticsearch()

    # Close Redis connection
    close_redis_connection()


# =============================================================================
# Application Factory
# =============================================================================
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory pattern allows:
    - Creating multiple app instances (useful for testing)
    - Configuring differently based on environment
    - Lazy initialization

    Returns:
        Configured FastAPI application instance
    """
    # Create the FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="""
## Books API

A RESTful API for managing a book library.

### Features
- **Books**: Full CRUD operations for books
- **Authors**: Manage book authors
- **Genres**: Categorize books by genre

### Authentication
Currently open access. API key authentication coming soon.

### Rate Limiting
Rate limiting will be implemented to ensure fair usage.
        """,
        version=settings.api_version,
        # OpenAPI documentation URLs
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc alternative
        openapi_url="/openapi.json",  # OpenAPI schema
        # Lifespan handler for startup/shutdown
        lifespan=lifespan,
        # Only show docs in debug mode (production consideration)
        # docs_url="/docs" if settings.debug else None,
    )

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    # Attach the limiter to the app state so it can be accessed by decorators
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # -------------------------------------------------------------------------
    # CORS Middleware
    # -------------------------------------------------------------------------
    # CORS (Cross-Origin Resource Sharing) allows web browsers
    # from different domains to make requests to your API.
    #
    # Without CORS:
    #   - Frontend at http://localhost:3000
    #   - API at http://localhost:8000
    #   - Browser blocks requests (security feature)
    #
    # With CORS:
    #   - API tells browser which origins are allowed
    #   - Browser permits the cross-origin requests

    app.add_middleware(
        CORSMiddleware,
        # Which origins can make requests
        allow_origins=settings.allowed_origins_list,
        # Allow credentials (cookies, auth headers)
        allow_credentials=True,
        # Which HTTP methods are allowed
        allow_methods=["*"],
        # Which headers can be sent
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """
        Handle SQLAlchemy database errors.

        Converts database exceptions to user-friendly HTTP responses.
        Logs the actual error for debugging while hiding details from users.
        """
        logger.error(f"Database error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "A database error occurred. Please try again later."
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Catch-all exception handler.

        In production, hide internal errors from users.
        In debug mode, show more details.
        """
        logger.error(f"Unhandled error: {exc}", exc_info=True)

        if settings.debug:
            return JSONResponse(
                status_code=500,
                content={"detail": str(exc)},
            )

        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred."},
        )

    # -------------------------------------------------------------------------
    # Register Routers
    # -------------------------------------------------------------------------
    # Routers group related endpoints together
    # prefix="/api/v1" creates versioned URLs: /api/v1/books, /api/v1/authors
    api_prefix = f"/api/{settings.api_version}"

    # Recommendations router must come before books router
    # so that /books/trending and /books/new-releases match before /books/{book_id}
    app.include_router(recommendations_router, prefix=api_prefix)
    app.include_router(books_router, prefix=api_prefix)
    app.include_router(authors_router, prefix=api_prefix)
    app.include_router(genres_router, prefix=api_prefix)
    app.include_router(api_keys_router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    # Users router must come before reviews router
    # so that /users/me/reviews is matched before /users/{user_id}/reviews
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(reviews_router, prefix=api_prefix)
    app.include_router(search_router, prefix=api_prefix)

    # -------------------------------------------------------------------------
    # GraphQL Endpoint
    # -------------------------------------------------------------------------
    # GraphQL provides an alternative API paradigm with flexible queries.
    # Available at /graphql with GraphiQL playground for development.
    graphql_router = create_graphql_router()
    app.include_router(graphql_router, prefix="/graphql", tags=["GraphQL"])

    # -------------------------------------------------------------------------
    # WebSocket Endpoint
    # -------------------------------------------------------------------------
    # WebSocket provides real-time updates for books, reviews, and user events.
    # Available at /ws/{channel} with channel-based subscriptions.
    app.include_router(websocket_router)

    # -------------------------------------------------------------------------
    # Health Check Endpoint
    # -------------------------------------------------------------------------
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        description="Check if the API is running and healthy.",
    )
    async def health_check() -> dict:
        """
        Health check endpoint.

        Used by:
        - Load balancers to check if instance is healthy
        - Kubernetes liveness/readiness probes
        - Monitoring systems

        Returns API status including cache connectivity and rate limiting.
        """
        cache_stats = get_cache_stats()
        es_healthy = await is_elasticsearch_healthy()
        es_doc_count = await get_document_count() if es_healthy else 0
        ws_manager = get_connection_manager()
        ws_stats = ws_manager.get_stats()

        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.api_version,
            "cache": cache_stats,
            "elasticsearch": {
                "enabled": settings.elasticsearch_enabled,
                "healthy": es_healthy,
                "document_count": es_doc_count,
            },
            "rate_limiting": {
                "enabled": settings.rate_limit_enabled,
                "default_limit": settings.rate_limit_default,
            },
            "authentication": {
                "enabled": settings.api_key_enabled,
                "header": settings.api_key_header,
            },
            "graphql": {
                "enabled": True,
                "endpoint": "/graphql",
                "playground_enabled": settings.graphql_playground_enabled,
            },
            "websocket": {
                "enabled": True,
                "endpoint": "/ws/{channel}",
                "connections": ws_stats["total_connections"],
                "channels": ws_stats["channels"],
            },
        }

    @app.get(
        "/",
        tags=["Root"],
        summary="API root",
        description="Welcome message and API information.",
    )
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.api_version,
            "docs": "/docs",
            "graphql": "/graphql",
            "health": "/health",
        }

    return app


# =============================================================================
# Application Instance
# =============================================================================
# Create the app instance
# This is what uvicorn imports: uvicorn app.main:app

app = create_app()


# =============================================================================
# Development Server
# =============================================================================
# This allows running the app directly with: python -m app.main
# In production, use: uvicorn app.main:app --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,  # Auto-reload on code changes
    )
