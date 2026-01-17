"""
Authentication Router

Handles user authentication endpoints:
- Registration (email/password)
- Login (Phase 3B)
- Token refresh (Phase 3B)
- OAuth callbacks (Phase 3C)

Security:
=========
- Passwords are hashed with bcrypt before storage
- Plain text passwords are never logged or stored
- JWT tokens are used for session management
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbSession
from app.models.user import AuthProvider, User
from app.schemas.user import UserCreate, UserResponse
from app.services.rate_limiter import limiter
from app.services.security import hash_password

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        409: {"description": "Conflict (email/username already exists)"},
    },
)


# -------------------------------------------------------------------------
# Registration Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Create a new user account with email and password.

    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    **Username Requirements:**
    - 3-50 characters
    - Must start with a letter
    - Only letters, numbers, and underscores
    """,
)
@limiter.limit("5/minute")  # Strict rate limit to prevent spam registrations
def register(
    request: Request,
    user_data: UserCreate,
    db: DbSession,
) -> UserResponse:
    """
    Register a new user with email and password.

    1. Validates email and password format (handled by Pydantic)
    2. Checks for duplicate email/username
    3. Hashes password with bcrypt
    4. Creates user record
    5. Returns user data (without password)
    """
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    existing_email = db.execute(stmt).scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username already exists
    stmt = select(User).where(User.username == user_data.username.lower())
    existing_username = db.execute(stmt).scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create new user with hashed password
    user = User(
        email=user_data.email,
        username=user_data.username.lower(),  # Normalize to lowercase
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        auth_provider=AuthProvider.LOCAL.value,
        is_active=True,
        is_verified=False,  # Email verification not implemented yet
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    return UserResponse.model_validate(user)


# -------------------------------------------------------------------------
# Placeholder endpoints for Phase 3B
# -------------------------------------------------------------------------
# These will be implemented in Phase 3B:
# - POST /auth/login - Email/password login
# - POST /auth/refresh - Refresh access token
# - POST /auth/logout - Invalidate refresh token
# - GET /auth/me - Get current user from token
