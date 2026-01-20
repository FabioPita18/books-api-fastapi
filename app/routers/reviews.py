"""
Reviews Router

CRUD endpoints for book reviews.

Endpoints:
- GET /books/{book_id}/reviews - List reviews for a book
- POST /books/{book_id}/reviews - Create a review (authenticated)
- GET /reviews/{review_id} - Get a specific review
- PUT /reviews/{review_id} - Update a review (owner only)
- DELETE /reviews/{review_id} - Delete a review (owner or superuser)
- GET /books/{book_id}/rating - Get book rating statistics
- GET /users/{user_id}/reviews - Get reviews by a user

Business Rules:
- One review per user per book (enforced by database constraint)
- Only the review author can update their review
- Only the review author or superusers can delete a review
"""

import logging
import math

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import (
    ActiveUser,
    DbSession,
    Pagination,
    SuperUser,
    get_book_or_404,
    get_user_or_404,
)
from app.models.review import Review
from app.schemas.review import (
    BookRatingStats,
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewUpdate,
)
from app.services.events import EventType, publish_review_event_async
from app.services.rate_limiter import limiter
from app.services.ratings import recalculate_book_rating

logger = logging.getLogger(__name__)

settings = get_settings()

# =============================================================================
# Router Configuration
# =============================================================================

router = APIRouter(
    tags=["Reviews"],
    responses={
        404: {"description": "Review or book not found"},
    },
)


# =============================================================================
# Helper Functions
# =============================================================================
# Note: get_book_or_404 and get_user_or_404 are imported from app.dependencies


def get_review_or_404(db: DbSession, review_id: int) -> Review:
    """Get a review by ID with user and book loaded, or raise 404."""
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.id == review_id)
    )
    review = db.execute(stmt).scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return review


# =============================================================================
# Book Review Endpoints
# =============================================================================


@router.get(
    "/books/{book_id}/reviews",
    response_model=ReviewListResponse,
    summary="List reviews for a book",
    description="Get a paginated list of reviews for a specific book.",
)
@limiter.limit(settings.rate_limit_default)
def list_book_reviews(
    request: Request,
    book_id: int,
    db: DbSession,
    pagination: Pagination,
) -> ReviewListResponse:
    """
    List all reviews for a specific book.

    Args:
        book_id: ID of the book to get reviews for
        pagination: Pagination parameters

    Returns:
        Paginated list of reviews with user info
    """
    # Verify book exists
    get_book_or_404(db, book_id)

    # Count total reviews
    count_stmt = select(func.count()).where(Review.book_id == book_id)
    total = db.execute(count_stmt).scalar() or 0

    # Calculate pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch reviews with relationships
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.book_id == book_id)
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


@router.post(
    "/books/{book_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review",
    description="Create a new review for a book. Requires authentication. One review per book per user.",
)
@limiter.limit(settings.rate_limit_write)
def create_review(
    request: Request,
    book_id: int,
    review_data: ReviewCreate,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
) -> ReviewResponse:
    """
    Create a new review for a book.

    Args:
        book_id: ID of the book to review
        review_data: Review content (rating, title, content)
        current_user: Authenticated user creating the review

    Returns:
        Created review with user info

    Raises:
        HTTPException: 404 if book not found
        HTTPException: 400 if user already reviewed this book
    """
    # Verify book exists
    book = get_book_or_404(db, book_id)

    # Check if user already reviewed this book
    existing_stmt = select(Review).where(
        Review.book_id == book_id,
        Review.user_id == current_user.id,
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this book. You can update your existing review.",
        )

    # Create review
    review = Review(
        book_id=book_id,
        user_id=current_user.id,
        rating=review_data.rating,
        title=review_data.title,
        content=review_data.content,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    # Update book rating aggregations
    recalculate_book_rating(db, book_id)

    # Load relationships for response
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.id == review.id)
    )
    review = db.execute(stmt).scalar_one()

    # Publish event for WebSocket clients (background task)
    async def publish_event():
        await publish_review_event_async(
            EventType.REVIEW_CREATED,
            book_id,
            review.id,
            {
                "rating": review.rating,
                "title": review.title,
                "book_title": book.title,
                "user_name": current_user.full_name or current_user.username,
            },
        )

    background_tasks.add_task(publish_event)

    return ReviewResponse.model_validate(review)


@router.get(
    "/books/{book_id}/rating",
    response_model=BookRatingStats,
    summary="Get book rating statistics",
    description="Get aggregated rating statistics for a book.",
)
@limiter.limit(settings.rate_limit_default)
def get_book_rating_stats(
    request: Request,
    book_id: int,
    db: DbSession,
) -> BookRatingStats:
    """
    Get rating statistics for a book.

    Returns:
        - Average rating
        - Total review count
        - Rating distribution (count of each rating 1-5)
    """
    # Verify book exists
    get_book_or_404(db, book_id)

    # Get average rating and count
    stats_stmt = select(
        func.avg(Review.rating),
        func.count(Review.id),
    ).where(Review.book_id == book_id)
    result = db.execute(stats_stmt).one()
    avg_rating = float(result[0]) if result[0] else 0.0
    total_reviews = result[1]

    # Get rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    if total_reviews > 0:
        dist_stmt = (
            select(Review.rating, func.count(Review.id))
            .where(Review.book_id == book_id)
            .group_by(Review.rating)
        )
        for rating, count in db.execute(dist_stmt).all():
            distribution[rating] = count

    return BookRatingStats(
        book_id=book_id,
        average_rating=round(avg_rating, 2),
        total_reviews=total_reviews,
        rating_distribution=distribution,
    )


# =============================================================================
# Reported Reviews (must come before /reviews/{review_id} for route matching)
# =============================================================================


@router.get(
    "/reviews/reported",
    response_model=ReviewListResponse,
    summary="List reported reviews",
    description="Get all reported reviews for moderation. Superuser only.",
)
@limiter.limit(settings.rate_limit_default)
def list_reported_reviews(
    request: Request,
    db: DbSession,
    pagination: Pagination,
    current_user: SuperUser,
) -> ReviewListResponse:
    """
    List all reported reviews (for moderation).

    Only accessible by superusers.

    Args:
        pagination: Pagination parameters
        current_user: Authenticated superuser

    Returns:
        Paginated list of reported reviews
    """
    # Count total reported reviews
    count_stmt = select(func.count()).where(Review.reported == True)  # noqa: E712
    total = db.execute(count_stmt).scalar() or 0

    # Calculate pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch reported reviews
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.reported == True)  # noqa: E712
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
# Individual Review Endpoints
# =============================================================================


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get a review by ID",
    description="Retrieve a specific review with user and book information.",
)
@limiter.limit(settings.rate_limit_default)
def get_review(
    request: Request,
    review_id: int,
    db: DbSession,
) -> ReviewResponse:
    """
    Get a single review by ID.

    Args:
        review_id: ID of the review

    Returns:
        Review with user and book info
    """
    review = get_review_or_404(db, review_id)
    return ReviewResponse.model_validate(review)


@router.put(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
    description="Update your own review. Only the review author can update.",
)
@limiter.limit(settings.rate_limit_write)
def update_review(
    request: Request,
    review_id: int,
    review_data: ReviewUpdate,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
) -> ReviewResponse:
    """
    Update an existing review.

    Only the review author can update their review.

    Args:
        review_id: ID of the review to update
        review_data: Fields to update
        current_user: Authenticated user

    Returns:
        Updated review

    Raises:
        HTTPException: 404 if review not found
        HTTPException: 403 if user is not the review author
    """
    review = get_review_or_404(db, review_id)

    # Check ownership
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reviews",
        )

    # Update fields
    update_data = review_data.model_dump(exclude_unset=True)
    rating_changed = "rating" in update_data and update_data["rating"] != review.rating
    for field, value in update_data.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)

    # Recalculate book ratings if rating was changed
    if rating_changed:
        recalculate_book_rating(db, review.book_id)

    # Publish event for WebSocket clients (background task)
    book_id = review.book_id
    review_id_val = review.id

    async def publish_event():
        await publish_review_event_async(
            EventType.REVIEW_UPDATED,
            book_id,
            review_id_val,
            {
                "rating": review.rating,
                "title": review.title,
            },
        )

    background_tasks.add_task(publish_event)

    return ReviewResponse.model_validate(review)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review",
    description="Delete a review. Only the review author or superusers can delete.",
)
@limiter.limit(settings.rate_limit_write)
def delete_review(
    request: Request,
    review_id: int,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Delete a review.

    - Review authors can delete their own reviews
    - Superusers can delete any review (moderation)

    Args:
        review_id: ID of the review to delete
        current_user: Authenticated user

    Raises:
        HTTPException: 404 if review not found
        HTTPException: 403 if user cannot delete this review
    """
    review = get_review_or_404(db, review_id)

    # Check ownership or superuser status
    if review.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )

    # Save info before deletion for the event
    book_id = review.book_id
    review_id_val = review.id
    review_title = review.title

    db.delete(review)
    db.commit()

    # Recalculate book ratings after deletion
    recalculate_book_rating(db, book_id)

    # Publish event for WebSocket clients (background task)
    async def publish_event():
        await publish_review_event_async(
            EventType.REVIEW_DELETED,
            book_id,
            review_id_val,
            {"title": review_title},
        )

    background_tasks.add_task(publish_event)


# =============================================================================
# User Review Endpoints
# =============================================================================


@router.get(
    "/users/{user_id}/reviews",
    response_model=ReviewListResponse,
    summary="List reviews by a user",
    description="Get a paginated list of reviews written by a specific user.",
)
@limiter.limit(settings.rate_limit_default)
def list_user_reviews(
    request: Request,
    user_id: int,
    db: DbSession,
    pagination: Pagination,
) -> ReviewListResponse:
    """
    List all reviews by a specific user.

    Args:
        user_id: ID of the user
        pagination: Pagination parameters

    Returns:
        Paginated list of reviews
    """
    # Verify user exists
    get_user_or_404(db, user_id)

    # Count total reviews
    count_stmt = select(func.count()).where(Review.user_id == user_id)
    total = db.execute(count_stmt).scalar() or 0

    # Calculate pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch reviews with relationships
    stmt = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.user_id == user_id)
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
# Report/Unreport Review Endpoints
# =============================================================================


@router.post(
    "/reviews/{review_id}/report",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Report a review",
    description="Flag a review for moderation. Requires authentication.",
)
@limiter.limit(settings.rate_limit_write)
def report_review(
    request: Request,
    review_id: int,
    db: DbSession,
    current_user: ActiveUser,
) -> None:
    """
    Report a review for moderation.

    Args:
        review_id: ID of the review to report
        current_user: Authenticated user

    Raises:
        HTTPException: 404 if review not found
    """
    review = get_review_or_404(db, review_id)
    review.reported = True
    db.commit()


@router.post(
    "/reviews/{review_id}/unreport",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear review report",
    description="Clear the reported flag on a review. Superuser only.",
)
@limiter.limit(settings.rate_limit_write)
def unreport_review(
    request: Request,
    review_id: int,
    db: DbSession,
    current_user: SuperUser,
) -> None:
    """
    Clear the reported flag on a review.

    Only accessible by superusers.

    Args:
        review_id: ID of the review to unreport
        current_user: Authenticated superuser

    Raises:
        HTTPException: 404 if review not found
    """
    review = get_review_or_404(db, review_id)
    review.reported = False
    db.commit()
