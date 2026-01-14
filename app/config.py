"""
Application Configuration Module

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
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic Settings automatically:
    1. Reads from environment variables (case-insensitive)
    2. Falls back to .env file if env var not found
    3. Validates types and raises errors for invalid values

    Field(...) is used for required fields with descriptions.
    default=value is used for optional fields with defaults.
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
        default=8000,
        description="Port to bind the server to"
    )

    # -------------------------------------------------------------------------
    # Database Settings
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/books_db",
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
        description="Default cache time-to-live in seconds"
    )

    # -------------------------------------------------------------------------
    # Rate Limiting Settings
    # -------------------------------------------------------------------------
    rate_limit_requests: int = Field(
        default=100,
        description="Number of requests allowed per time window"
    )
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit time window in seconds"
    )

    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for cryptographic operations"
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
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
    def allowed_origins_list(self) -> List[str]:
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
