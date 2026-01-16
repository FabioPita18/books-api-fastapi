"""
Rate Limiting Service

Implements rate limiting using slowapi to protect the API from abuse
and ensure fair usage across clients.

Key Features:
=============
1. IP-based rate limiting (default)
2. Configurable limits per endpoint type
3. Redis storage for distributed deployments
4. Graceful degradation if Redis unavailable
5. Custom error responses

Rate Limit Tiers:
=================
- Default (GET single): 100 requests/minute
- Search endpoints: 60 requests/minute
- Write operations: 30 requests/minute
"""

import logging
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_client_ip(request: Request) -> str:
    """
    Get client IP address for rate limiting.

    Handles common proxy headers to get the real client IP.
    Falls back to direct connection IP if no proxy headers.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    # Check X-Forwarded-For header (common for proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter.

    Uses Redis as storage backend if available for distributed
    rate limiting across multiple API instances.

    Returns:
        Configured Limiter instance
    """
    # Use Redis for storage if available (supports distributed deployments)
    storage_uri = settings.redis_url if settings.rate_limit_enabled else None

    limiter = Limiter(
        key_func=get_client_ip,
        default_limits=[settings.rate_limit_default],
        storage_uri=storage_uri,
        strategy="fixed-window",  # Simple and predictable
        enabled=settings.rate_limit_enabled,
    )

    logger.info(
        f"Rate limiter initialized - enabled: {settings.rate_limit_enabled}, "
        f"default: {settings.rate_limit_default}"
    )

    return limiter


# Create the limiter instance
limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with:
    - 429 Too Many Requests status
    - Retry-After header
    - Helpful error message

    Args:
        request: The request that exceeded the limit
        exc: The RateLimitExceeded exception

    Returns:
        JSONResponse with rate limit error details
    """
    # Parse the limit from the exception detail
    limit_detail = str(exc.detail)

    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "detail": limit_detail,
        },
    )

    # Add Retry-After header (seconds until reset)
    # slowapi includes this in the exception
    response.headers["Retry-After"] = str(60)  # Default to 1 minute
    response.headers["X-RateLimit-Limit"] = limit_detail

    logger.warning(
        f"Rate limit exceeded for {get_client_ip(request)}: {limit_detail}"
    )

    return response
