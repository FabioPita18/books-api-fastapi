"""
Review Pydantic Schemas

Schemas for book reviews with ratings.

Schemas:
- ReviewBase: Shared fields for review operations
- ReviewCreate: Create a new review
- ReviewUpdate: Update an existing review
- ReviewResponse: Full review data for API responses
- ReviewListResponse: Paginated list of reviews

Business Rules:
- Rating must be 1-5 (validated at schema level)
- One review per user per book (enforced at database level)
- Users can only edit/delete their own reviews
"""
# ruff: noqa: I001
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import UserPublicResponse


# =============================================================================
# Embedded Schemas (Minimal data for nested responses)
# =============================================================================


class BookMinimal(BaseModel):
    """
    Minimal book info for embedding in review responses.

    We don't want to include full book data (authors, genres, etc.)
    when returning a list of reviews - just enough to identify the book.
    """

    id: int = Field(..., description="Book ID")
    title: str = Field(..., description="Book title")
    isbn: str | None = Field(default=None, description="ISBN")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Review Schemas
# =============================================================================


class ReviewBase(BaseModel):
    """
    Base schema with shared review fields.

    Contains validation for:
    - Rating (must be 1-5)
    - Title length
    - Content length
    """

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 to 5 stars",
        examples=[4, 5],
    )

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional review title/headline",
        examples=["A masterpiece!", "Disappointing read"],
    )

    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Review text content",
        examples=["This book changed my perspective on..."],
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty_if_provided(cls, v: str | None) -> str | None:
        """Validate title is not just whitespace if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty_if_provided(cls, v: str | None) -> str | None:
        """Validate content is not just whitespace if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ReviewCreate(ReviewBase):
    """
    Schema for creating a new review.

    Only requires rating - title and content are optional.

    Example request body:
    {
        "rating": 5,
        "title": "Amazing book!",
        "content": "One of the best books I've ever read..."
    }
    """

    pass  # Inherits all fields from ReviewBase


class ReviewUpdate(BaseModel):
    """
    Schema for updating an existing review.

    All fields are optional for PATCH-style updates.
    """

    rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Rating from 1 to 5 stars",
    )

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional review title/headline",
    )

    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Review text content",
    )


class ReviewResponse(ReviewBase):
    """
    Schema for review responses.

    Includes:
    - Review data (rating, title, content)
    - Database fields (id, timestamps)
    - Nested user info (who wrote the review)
    - Nested book info (which book was reviewed)
    - Moderation fields (helpful_count, reported)
    """

    id: int = Field(..., description="Unique review identifier")
    book_id: int = Field(..., description="ID of the reviewed book")
    user_id: int = Field(..., description="ID of the user who wrote the review")

    helpful_count: int = Field(
        default=0,
        description="Number of helpful votes"
    )

    created_at: datetime = Field(..., description="When the review was created")
    updated_at: datetime = Field(..., description="When the review was last updated")

    # Nested relationships
    user: UserPublicResponse = Field(..., description="User who wrote the review")
    book: BookMinimal = Field(..., description="Book being reviewed")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "book_id": 42,
                "user_id": 7,
                "rating": 5,
                "title": "A must-read classic!",
                "content": "This book completely changed my perspective on...",
                "helpful_count": 12,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "user": {
                    "id": 7,
                    "username": "booklover",
                    "full_name": "Jane Doe",
                    "avatar_url": None,
                    "bio": "Avid reader",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                "book": {
                    "id": 42,
                    "title": "1984",
                    "isbn": "9780451524935",
                },
            }
        },
    )


class ReviewResponseSimple(ReviewBase):
    """
    Simplified review response without nested relationships.

    Used when returning reviews as part of book or user responses
    to avoid deep nesting.
    """

    id: int = Field(..., description="Unique review identifier")
    book_id: int = Field(..., description="ID of the reviewed book")
    user_id: int = Field(..., description="ID of the user who wrote the review")
    helpful_count: int = Field(default=0, description="Number of helpful votes")
    created_at: datetime = Field(..., description="When the review was created")
    updated_at: datetime = Field(..., description="When the review was last updated")

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """
    Schema for paginated review list responses.

    Includes pagination metadata:
    - total: Total number of reviews
    - page: Current page number
    - per_page: Number of items per page
    - pages: Total number of pages
    """

    items: list[ReviewResponse] = Field(
        ...,
        description="List of reviews for this page",
    )

    total: int = Field(
        ...,
        ge=0,
        description="Total number of reviews",
    )

    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )

    per_page: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page",
    )

    pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 50,
                "page": 1,
                "per_page": 10,
                "pages": 5,
            }
        },
    )


# =============================================================================
# Aggregation Schemas
# =============================================================================


class BookRatingStats(BaseModel):
    """
    Aggregated rating statistics for a book.

    Used to show average rating and total review count.
    """

    book_id: int = Field(..., description="Book ID")
    average_rating: float = Field(
        ...,
        ge=0,
        le=5,
        description="Average rating (0-5, 0 means no reviews)"
    )
    total_reviews: int = Field(
        ...,
        ge=0,
        description="Total number of reviews"
    )
    rating_distribution: dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        description="Count of each rating (1-5)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": 42,
                "average_rating": 4.2,
                "total_reviews": 125,
                "rating_distribution": {
                    "1": 5,
                    "2": 10,
                    "3": 20,
                    "4": 40,
                    "5": 50
                }
            }
        },
    )
