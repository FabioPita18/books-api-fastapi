"""
Redis Caching Service

This module provides caching utilities using Redis for improved API performance.

Features:
- Connection pooling to Redis
- Generic cache get/set/delete functions
- Cache key generation helpers
- Automatic JSON serialization/deserialization
- Graceful degradation when Redis is unavailable

Cache Strategy:
- Book lookups: 5 minute TTL
- Search results: 2 minute TTL
- Author/Genre lists: 10 minute TTL
- Cache invalidation on write operations
"""

import json
import logging
from typing import Any, Optional
from functools import wraps

import redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# Redis Connection
# =============================================================================

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create a Redis client connection.

    Uses a module-level singleton to maintain a single connection pool.
    Returns None if Redis is unavailable, allowing graceful degradation.

    Returns:
        Redis client instance or None if connection fails
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()

    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,  # Return strings instead of bytes
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test the connection
        _redis_client.ping()
        logger.info("Successfully connected to Redis")
        return _redis_client
    except RedisError as e:
        logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
        _redis_client = None
        return None


def close_redis_connection() -> None:
    """Close the Redis connection on shutdown."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


# =============================================================================
# Cache Key Generation
# =============================================================================

def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from prefix and arguments.

    Examples:
        make_cache_key("book", 1) -> "book:1"
        make_cache_key("books", page=1, per_page=10) -> "books:page=1:per_page=10"
        make_cache_key("search", q="orwell", genre_id=1) -> "search:genre_id=1:q=orwell"

    Args:
        prefix: Cache key prefix (e.g., "book", "books", "search")
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key (sorted for consistency)

    Returns:
        Cache key string
    """
    parts = [prefix]

    # Add positional args
    for arg in args:
        if arg is not None:
            parts.append(str(arg))

    # Add sorted kwargs (sorted for consistent key generation)
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if value is not None:
            parts.append(f"{key}={value}")

    return ":".join(parts)


# =============================================================================
# Core Cache Operations
# =============================================================================

def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from the cache.

    Args:
        key: Cache key

    Returns:
        Cached value (deserialized from JSON) or None if not found/error
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        value = client.get(key)
        if value is not None:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except RedisError as e:
        logger.warning(f"Cache get error for {key}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Cache JSON decode error for {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a value in the cache with optional TTL.

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (uses default if not specified)

    Returns:
        True if successfully cached, False otherwise
    """
    client = get_redis_client()
    if client is None:
        return False

    if ttl is None:
        ttl = get_settings().cache_ttl

    try:
        serialized = json.dumps(value, default=str)  # default=str handles dates, Decimals
        client.setex(key, ttl, serialized)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except RedisError as e:
        logger.warning(f"Cache set error for {key}: {e}")
        return False
    except (TypeError, ValueError) as e:
        logger.warning(f"Cache serialization error for {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    Delete a key from the cache.

    Args:
        key: Cache key to delete

    Returns:
        True if key was deleted, False otherwise
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except RedisError as e:
        logger.warning(f"Cache delete error for {key}: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Useful for cache invalidation when a resource is updated.

    Examples:
        cache_delete_pattern("book:*")  # Delete all book caches
        cache_delete_pattern("search:*")  # Delete all search caches

    Args:
        pattern: Redis key pattern (supports * wildcard)

    Returns:
        Number of keys deleted
    """
    client = get_redis_client()
    if client is None:
        return 0

    try:
        keys = client.keys(pattern)
        if keys:
            deleted = client.delete(*keys)
            logger.debug(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
            return deleted
        return 0
    except RedisError as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
        return 0


# =============================================================================
# Cache Invalidation Helpers
# =============================================================================

def invalidate_book_cache(book_id: Optional[int] = None) -> None:
    """
    Invalidate book-related caches.

    Called when a book is created, updated, or deleted.

    Args:
        book_id: Specific book ID to invalidate, or None for all books
    """
    if book_id:
        cache_delete(make_cache_key("book", book_id))

    # Always invalidate list and search caches since they may contain this book
    cache_delete_pattern("books:*")
    cache_delete_pattern("search:*")
    cache_delete_pattern("author:*:books:*")
    cache_delete_pattern("genre:*:books:*")


def invalidate_author_cache(author_id: Optional[int] = None) -> None:
    """
    Invalidate author-related caches.

    Called when an author is created, updated, or deleted.

    Args:
        author_id: Specific author ID to invalidate, or None for all authors
    """
    if author_id:
        cache_delete(make_cache_key("author", author_id))
        cache_delete_pattern(f"author:{author_id}:books:*")

    cache_delete_pattern("authors:*")
    # Books cache may contain author info
    cache_delete_pattern("books:*")
    cache_delete_pattern("book:*")
    cache_delete_pattern("search:*")


def invalidate_genre_cache(genre_id: Optional[int] = None) -> None:
    """
    Invalidate genre-related caches.

    Called when a genre is created, updated, or deleted.

    Args:
        genre_id: Specific genre ID to invalidate, or None for all genres
    """
    if genre_id:
        cache_delete(make_cache_key("genre", genre_id))
        cache_delete_pattern(f"genre:{genre_id}:books:*")

    cache_delete_pattern("genres:*")
    # Books cache may contain genre info
    cache_delete_pattern("books:*")
    cache_delete_pattern("book:*")
    cache_delete_pattern("search:*")


# =============================================================================
# Cache Statistics (for monitoring)
# =============================================================================

def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.

    Returns:
        Dictionary with cache statistics or empty dict if unavailable
    """
    client = get_redis_client()
    if client is None:
        return {"status": "disconnected"}

    try:
        info = client.info("stats")
        return {
            "status": "connected",
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "keys": client.dbsize(),
        }
    except RedisError:
        return {"status": "error"}
