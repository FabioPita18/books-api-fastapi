"""
Users Router

User profile management endpoints.

Endpoints:
- GET /users/me - Current user's profile (same as /auth/me)
- PUT /users/me - Update current user's profile
- PUT /users/me/password - Change password
- GET /users/me/reviews - Current user's reviews
- GET /users/{user_id} - Public user profile

Business Rules:
- Users can only update their own profile
- Password change requires current password verification
- Public profiles show limited information
"""

import math

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import ActiveUser, DbSession, Pagination, get_user_or_404
from app.models.review import Review
from app.schemas.review import ReviewListResponse, ReviewResponse
from app.schemas.user import (
    PasswordChange,
    UserPublicResponse,
    UserResponse,
    UserUpdate,
)
from app.services.rate_limiter import limiter
from app.services.security import hash_password, verify_password

settings = get_settings()

# =============================================================================
# Router Configuration
# =============================================================================

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)


# =============================================================================
# Helper Functions
# =============================================================================
# Note: get_user_or_404 is imported from app.dependencies (shared helper)


# =============================================================================
# Current User Endpoints (/users/me/...)
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the authenticated user's full profile.",
)
@limiter.limit(settings.rate_limit_default)
def get_current_user_profile(
    request: Request,
    current_user: ActiveUser,
) -> UserResponse:
    """
    Get the current authenticated user's profile.

    This is equivalent to /auth/me but placed here for REST consistency.
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update the authenticated user's profile information.",
)
@limiter.limit(settings.rate_limit_write)
def update_current_user_profile(
    request: Request,
    user_data: UserUpdate,
    db: DbSession,
    current_user: ActiveUser,
) -> UserResponse:
    """
    Update the current user's profile.

    Updatable fields:
    - full_name
    - bio
    - avatar_url

    Email and username changes are not allowed through this endpoint
    for security reasons.
    """
    # Update only provided fields
    update_data = user_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change the current user's password. Requires current password verification.",
)
@limiter.limit("5/minute")  # Strict rate limit for password changes
def change_password(
    request: Request,
    password_data: PasswordChange,
    db: DbSession,
    current_user: ActiveUser,
) -> None:
    """
    Change the current user's password.

    Requirements:
    - Must provide current password for verification
    - New password must meet strength requirements
    - Cannot be used by OAuth-only accounts (no password set)
    """
    # Check if user has a password (not OAuth-only)
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts. "
                   "Your account uses social login.",
        )

    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()


@router.get(
    "/me/reviews",
    response_model=ReviewListResponse,
    summary="Get current user's reviews",
    description="Get a paginated list of reviews written by the current user.",
)
@limiter.limit(settings.rate_limit_default)
def get_my_reviews(
    request: Request,
    db: DbSession,
    current_user: ActiveUser,
    pagination: Pagination,
) -> ReviewListResponse:
    """
    Get all reviews written by the current user.

    Returns paginated results with book information included.
    """
    # Count total reviews
    count_stmt = select(func.count()).where(Review.user_id == current_user.id)
    total = db.execute(count_stmt).scalar() or 0

    # Calculate pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch reviews with relationships
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.user_id == current_user.id)
        .offset(pagination.skip)
        .limit(pagination.per_page)
        .order_by(Review.created_at.desc())
    )
    reviews = db.execute(stmt).scalars().all()

    return ReviewListResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=pages,
    )


# =============================================================================
# Public User Endpoints (/users/{user_id})
# =============================================================================


@router.get(
    "/{user_id}",
    response_model=UserPublicResponse,
    summary="Get public user profile",
    description="Get a user's public profile by ID. Shows limited information.",
)
@limiter.limit(settings.rate_limit_default)
def get_public_user_profile(
    request: Request,
    user_id: int,
    db: DbSession,
) -> UserPublicResponse:
    """
    Get a user's public profile.

    Returns limited information suitable for public viewing:
    - id, username, full_name, avatar_url, bio, created_at

    Does NOT expose:
    - email, is_active, is_verified, auth_provider
    """
    user = get_user_or_404(db, user_id)

    # Check if user is active (don't expose inactive profiles)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    return UserPublicResponse.model_validate(user)
