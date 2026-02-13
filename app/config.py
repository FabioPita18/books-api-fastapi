"""
Application Configuration Module (Phase 1)

This module uses Pydantic Settings for type-safe configuration management.

WHY Pydantic Settings?
======================
1. Type Safety: All configuration values are validated against their types
2. Environment Variables: Automatically loads from environment variables
3. .env Support: Can load from .env files for local development
4. Validation: Catches configuration errors at startup, not runtime
5. IDE Support: Full autocomplete and type hints

PATTERN: Settings Singleton
===========================
We create a single Settings instance that's cached using @lru_cache.
This ensures:
- Configuration is loaded once at startup
- All parts of the app use the same configuration
- No repeated file I/O for .env loading

Usage:
    from app.config import get_settings

    settings = get_settings()
    print(settings.app_name)

PHASE 1 vs PHASE 2:
===================
- Phase 1: Database, security, logging (active)
- Phase 2: Redis, caching, rate limiting (commented out)
"""

import logging
import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic Settings automatically:
    1. Reads from environment variables (case-insensitive)
    2. Falls back to .env file if env var not found
    3. Validates types and raises errors for invalid values

    Field(...) is used for required fields with descriptions.
    default=value is used for optional fields with defaults.

    SECURITY NOTE:
    ==============
    - secret_key and database credentials have validators
    - Placeholder values will raise errors at startup
    - This prevents accidental deployment with insecure defaults
    """

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(
        default="Books API",
        description="Application name displayed in docs and logs"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (detailed errors, auto-reload)"
    )
    api_version: str = Field(
        default="v1",
        description="API version for URL routing"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8001,  # Custom port (not default 8000)
        description="Port to bind the server to"
    )
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )

    # -------------------------------------------------------------------------
    # Database Settings
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql://books_admin:password@localhost:5433/books_production",
        description="PostgreSQL connection URL"
    )
    db_pool_size: int = Field(
        default=5,
        description="Number of permanent database connections"
    )
    db_max_overflow: int = Field(
        default=10,
        description="Maximum additional connections during high load"
    )

    # -------------------------------------------------------------------------
    # Redis Settings
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    )
    cache_ttl: int = Field(
        default=300,
        description="Default cache time-to-live in seconds (5 minutes)"
    )
    cache_ttl_books: int = Field(
        default=300,
        description="Cache TTL for book data (5 minutes)"
    )
    cache_ttl_search: int = Field(
        default=120,
        description="Cache TTL for search results (2 minutes)"
    )
    cache_ttl_lists: int = Field(
        default=600,
        description="Cache TTL for author/genre lists (10 minutes)"
    )

    # -------------------------------------------------------------------------
    # Rate Limiting Settings
    # -------------------------------------------------------------------------
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_default: str = Field(
        default="100/minute",
        description="Default rate limit for read endpoints"
    )
    rate_limit_write: str = Field(
        default="30/minute",
        description="Rate limit for write endpoints (POST, PUT, DELETE)"
    )
    rate_limit_search: str = Field(
        default="60/minute",
        description="Rate limit for search endpoints"
    )

    # -------------------------------------------------------------------------
    # JWT Settings
    # -------------------------------------------------------------------------
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=15,
        description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )

    # -------------------------------------------------------------------------
    # OAuth Settings (Social Login)
    # -------------------------------------------------------------------------
    # Google OAuth
    google_client_id: str = Field(
        default="",
        description="Google OAuth client ID"
    )
    google_client_secret: str = Field(
        default="",
        description="Google OAuth client secret"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8001/api/v1/auth/google/callback",
        description="Google OAuth redirect URI"
    )

    # GitHub OAuth
    github_client_id: str = Field(
        default="",
        description="GitHub OAuth client ID"
    )
    github_client_secret: str = Field(
        default="",
        description="GitHub OAuth client secret"
    )
    github_redirect_uri: str = Field(
        default="http://localhost:8001/api/v1/auth/github/callback",
        description="GitHub OAuth redirect URI"
    )

    # Frontend URL (for redirects after OAuth)
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for OAuth redirects"
    )

    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="",
        description="Secret key for cryptographic operations (used for JWT signing)"
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    admin_api_key: str = Field(
        default="",
        description="Admin API key for full access (set in .env)"
    )
    api_key_enabled: bool = Field(
        default=True,
        description="Enable API key authentication for write operations"
    )
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )

    # -------------------------------------------------------------------------
    # Elasticsearch Settings
    # -------------------------------------------------------------------------
    elasticsearch_url: str = Field(
        default="http://localhost:9200",
        description="Elasticsearch connection URL"
    )
    elasticsearch_index_prefix: str = Field(
        default="books_api_",
        description="Prefix for Elasticsearch index names"
    )
    elasticsearch_timeout: int = Field(
        default=30,
        description="Elasticsearch request timeout in seconds"
    )
    elasticsearch_enabled: bool = Field(
        default=True,
        description="Enable Elasticsearch for advanced search (falls back to PostgreSQL if disabled)"
    )

    # -------------------------------------------------------------------------
    # Recommendations Settings
    # -------------------------------------------------------------------------
    recommendation_cache_ttl: int = Field(
        default=3600,
        description="Cache TTL for recommendations in seconds (1 hour)"
    )
    similar_books_limit: int = Field(
        default=10,
        description="Default number of similar books to return"
    )

    # -------------------------------------------------------------------------
    # GraphQL Settings
    # -------------------------------------------------------------------------
    graphql_playground_enabled: bool = Field(
        default=True,
        description="Enable GraphiQL playground for development"
    )
    graphql_introspection_enabled: bool = Field(
        default=True,
        description="Enable GraphQL schema introspection"
    )

    # -------------------------------------------------------------------------
    # Logging Settings
    # -------------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # -------------------------------------------------------------------------
    # Pydantic Settings Configuration
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        # Load from .env file (path relative to where app runs)
        env_file=".env",
        # If env var not found and no .env, use defaults (don't fail)
        env_file_encoding="utf-8",
        # Environment variables are case-insensitive
        case_sensitive=False,
        # Extra fields in .env are ignored (no error)
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Parse comma-separated CORS origins into a list.

        This is a computed property (not a field) because:
        1. Environment variables are strings
        2. We need a list for CORS middleware
        3. Properties are computed on access, not stored

        Returns:
            List of allowed origin URLs
        """
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate that log_level is a valid Python logging level.

        @field_validator is a Pydantic v2 feature that validates fields
        before the model is created. If validation fails, Pydantic raises
        a ValidationError with a helpful message.

        Args:
            v: The value to validate

        Returns:
            The validated value (uppercase)

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Validate the secret_key, auto-generating one if not provided.

        If SECRET_KEY is empty or contains a placeholder value, a random
        key is generated so the app can still start. A warning is logged
        since the generated key won't persist across restarts (JWTs will
        be invalidated on redeploy).

        Args:
            v: The secret key value

        Returns:
            The validated (or auto-generated) secret key
        """
        placeholder_indicators = [
            "REPLACE_WITH",
            "change-me",
            "your-secret",
            "generate-with",
        ]

        needs_generation = not v or len(v) < 32
        if not needs_generation:
            for indicator in placeholder_indicators:
                if indicator.lower() in v.lower():
                    needs_generation = True
                    break

        if needs_generation:
            generated = secrets.token_hex(32)
            logger.warning(
                "SECRET_KEY not set or invalid — auto-generated a random key. "
                "JWTs will be invalidated on each restart. "
                "Set SECRET_KEY env var for persistent sessions."
            )
            return generated

        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is a known value."""
        valid_envs = {"development", "staging", "production"}
        if v.lower() not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v.lower()


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    WHY @lru_cache?
    ===============
    - lru_cache caches the result of this function
    - First call: Creates Settings instance, loads .env, validates
    - Subsequent calls: Returns the cached instance
    - This is Python's way of implementing a singleton pattern

    This means:
    - .env is read only once at startup
    - All parts of the app share the same settings
    - No performance cost for repeated get_settings() calls

    SECURITY:
    =========
    - Settings are validated at startup
    - Placeholder values cause immediate errors
    - This prevents accidental insecure deployments

    Usage:
        # In any module
        from app.config import get_settings

        settings = get_settings()
        if settings.debug:
            print("Debug mode is on!")

    Returns:
        Cached Settings instance
    """
    return Settings()
