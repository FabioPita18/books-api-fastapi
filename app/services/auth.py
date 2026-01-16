"""
Authentication Service

Handles API key generation, hashing, and validation.

Security Features:
=================
1. Keys are hashed with SHA-256 before storage
2. Plain keys are only shown once during creation
3. Supports admin key from environment variable
4. Tracks key usage for auditing
"""

import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import APIKey

logger = logging.getLogger(__name__)
settings = get_settings()

# Key prefix for identification
KEY_PREFIX = "bk_"


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
        - full_key: The complete key to show the user (only once!)
        - key_hash: SHA-256 hash to store in database
        - key_prefix: First 12 chars for identification

    Example:
        >>> key, hash, prefix = generate_api_key()
        >>> key
        'bk_a1b2c3d4e5f6g7h8i9j0...'
        >>> prefix
        'bk_a1b2c3d4'
    """
    # Generate 32 random bytes, encode as hex (64 chars)
    random_part = secrets.token_hex(32)
    full_key = f"{KEY_PREFIX}{random_part}"

    # Hash the key for storage
    key_hash = hash_api_key(full_key)

    # Store prefix for identification (first 12 chars including prefix)
    key_prefix = full_key[:12]

    return full_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        key: The plain API key

    Returns:
        SHA-256 hash of the key (64 hex characters)
    """
    return hashlib.sha256(key.encode()).hexdigest()


def validate_api_key(db: Session, key: str) -> Optional[APIKey]:
    """
    Validate an API key and return the associated record.

    Checks:
    1. Key hash exists in database
    2. Key is active
    3. Key is not expired

    Args:
        db: Database session
        key: The plain API key to validate

    Returns:
        APIKey record if valid, None otherwise
    """
    # First check if it's the admin key
    if settings.admin_api_key and key == settings.admin_api_key:
        logger.debug("Admin API key used")
        return _create_admin_key_record()

    # Hash the provided key
    key_hash = hash_api_key(key)

    # Look up in database
    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True,
    )
    api_key = db.execute(stmt).scalar_one_or_none()

    if api_key is None:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        logger.warning(f"Expired API key used: {api_key.key_prefix}...")
        return None

    # Update last used timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return api_key


def _create_admin_key_record() -> APIKey:
    """
    Create a virtual APIKey record for the admin key.

    This is used when the admin key from .env is used,
    so the authentication flow can work consistently.

    Returns:
        Virtual APIKey record (not persisted)
    """
    return APIKey(
        id=0,
        name="Admin",
        key_hash="admin",
        key_prefix="admin",
        is_active=True,
        description="Environment admin key",
    )


def create_api_key(
    db: Session,
    name: str,
    description: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> Tuple[str, APIKey]:
    """
    Create a new API key in the database.

    Args:
        db: Database session
        name: Human-readable name for the key
        description: Optional description
        expires_at: Optional expiration datetime

    Returns:
        Tuple of (plain_key, api_key_record)
        - plain_key: Show this to the user ONCE
        - api_key_record: The database record
    """
    # Generate the key
    plain_key, key_hash, key_prefix = generate_api_key()

    # Create database record
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        description=description,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"Created API key: {key_prefix}... for '{name}'")

    return plain_key, api_key


def revoke_api_key(db: Session, key_id: int) -> Optional[APIKey]:
    """
    Revoke an API key by ID.

    Args:
        db: Database session
        key_id: ID of the key to revoke

    Returns:
        The revoked APIKey record, or None if not found
    """
    stmt = select(APIKey).where(APIKey.id == key_id)
    api_key = db.execute(stmt).scalar_one_or_none()

    if api_key is None:
        return None

    api_key.is_active = False
    db.commit()
    db.refresh(api_key)

    logger.info(f"Revoked API key: {api_key.key_prefix}...")

    return api_key
