"""
Security Service

Handles password hashing and JWT token operations.

Security Features:
==================
1. Password hashing with bcrypt (passlib)
2. JWT token generation and validation
3. Secure password verification

Usage:
    from app.services.security import hash_password, verify_password

    # Hash a password
    hashed = hash_password("SecurePass123")

    # Verify a password
    is_valid = verify_password("SecurePass123", hashed)
"""

import logging
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# -------------------------------------------------------------------------
# Password Hashing Configuration
# -------------------------------------------------------------------------
# CryptContext handles password hashing with bcrypt
# - schemes: List of hashing algorithms (bcrypt is industry standard)
# - deprecated: "auto" means old hashes are automatically upgraded
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash of the password

    Example:
        >>> hashed = hash_password("SecurePass123")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        plain_password: The password to verify
        hashed_password: The stored bcrypt hash

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("SecurePass123")
        >>> verify_password("SecurePass123", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# -------------------------------------------------------------------------
# JWT Token Configuration
# -------------------------------------------------------------------------
# These will be used in Phase 3B for JWT authentication

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> token.count(".") == 2  # JWT format: header.payload.signature
        True
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token (longer-lived than access token).

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string

    Returns:
        Decoded payload if valid, None if invalid or expired

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user@example.com'
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def verify_token_type(token: str, expected_type: str) -> dict | None:
    """
    Decode a token and verify its type.

    Args:
        token: The JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded payload if valid and correct type, None otherwise
    """
    payload = decode_token(token)

    if payload is None:
        return None

    if payload.get("type") != expected_type:
        logger.warning(f"Token type mismatch: expected {expected_type}")
        return None

    return payload
