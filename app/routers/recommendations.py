"""
Recommendations Router

Provides book recommendation endpoints:
- Similar books (content-based)
- Personalized recommendations (collaborative filtering)
- Trending books
- New releases

Endpoints:
- GET /books/{book_id}/similar - Books similar to a given book
- GET /recommendations - Personalized recommendations (auth required)
- GET /books/trending - Popular books by rating and review activity
- GET /books/new-releases - Recently added books
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbSession, OptionalUser
from app.models import Book
from app.models.review import Review
from app.services.rate_limiter import limiter
from app.services.recommendations import (
    get_new_releases,
    get_recommendations_for_user,
    get_similar_books,
    get_trending_books,
)

settings = get_settings()


# =============================================================================
# Response Models
# =============================================================================


class RecommendedBookItem(BaseModel):
    """Book item in recommendation results."""

    id: int
    title: str
    description: str | None = None
    isbn: str | None = None
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    publication_year: int | None = None
    price: float | None = None
    average_rating: float | None = None
    review_count: int = 0


class SimilarBookItem(BaseModel):
    """Similar book with similarity score."""

    book: RecommendedBookItem
    similarity_score: float = Field(description="Similarity score (0-1)")
    reasons: list[str] = Field(default_factory=list, description="Why this book is similar")


class SimilarBooksResponse(BaseModel):
    """Response for similar books endpoint."""

    items: list[SimilarBookItem]
    source_book_id: int
    algorithm: str = "content-based"


class PersonalizedRecommendation(BaseModel):
    """Personalized recommendation with score."""

    book: RecommendedBookItem
    recommendation_score: float = Field(description="Recommendation strength")
    reasons: list[str] = Field(default_factory=list, description="Why this is recommended")


class PersonalizedRecommendationsResponse(BaseModel):
    """Response for personalized recommendations endpoint."""

    items: list[PersonalizedRecommendation]
    algorithm: str = "collaborative-filtering"
    user_id: int


class TrendingBookItem(BaseModel):
    """Trending book with score."""

    book: RecommendedBookItem
    trending_score: float = Field(description="Trending score based on ratings and activity")
    reasons: list[str] = Field(default_factory=list)


class TrendingBooksResponse(BaseModel):
    """Response for trending books endpoint."""

    items: list[TrendingBookItem]
    algorithm: str = "popularity"


class NewReleaseItem(BaseModel):
    """New release book item."""

    book: RecommendedBookItem
    added_at: str = Field(description="When the book was added to the catalog")
    reasons: list[str] = Field(default_factory=list)


class NewReleasesResponse(BaseModel):
    """Response for new releases endpoint."""

    items: list[NewReleaseItem]


# =============================================================================
# Router Configuration
# =============================================================================

router = APIRouter(
    tags=["Recommendations"],
)


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/books/trending",
    response_model=TrendingBooksResponse,
    summary="Get trending books",
    description="""
Get popular/trending books based on ratings and review activity.

Books are scored by: average_rating × log(review_count + 1)

This balances quality (high ratings) with popularity (many reviews).
""",
)
@limiter.limit(settings.rate_limit_default)
def get_trending(
    request: Request,
    db: DbSession,
    current_user: OptionalUser,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of books to return",
            ge=1,
            le=50,
        )
    ] = 10,
) -> TrendingBooksResponse:
    """Get trending/popular books."""
    exclude_user_id = current_user.id if current_user else None

    results = get_trending_books(
        db=db,
        limit=limit,
        exclude_user_id=exclude_user_id,
    )

    items = []
    for r in results:
        items.append(TrendingBookItem(
            book=RecommendedBookItem(**r["book"]),
            trending_score=r.get("trending_score", 0),
            reasons=r.get("reasons", []),
        ))

    return TrendingBooksResponse(items=items)


@router.get(
    "/books/new-releases",
    response_model=NewReleasesResponse,
    summary="Get new releases",
    description="Get recently added books to the catalog.",
)
@limiter.limit(settings.rate_limit_default)
def get_new(
    request: Request,
    db: DbSession,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of books to return",
            ge=1,
            le=50,
        )
    ] = 10,
) -> NewReleasesResponse:
    """Get newly added books."""
    results = get_new_releases(db=db, limit=limit)

    items = []
    for r in results:
        items.append(NewReleaseItem(
            book=RecommendedBookItem(**r["book"]),
            added_at=r.get("added_at", ""),
            reasons=r.get("reasons", []),
        ))

    return NewReleasesResponse(items=items)


@router.get(
    "/books/{book_id}/similar",
    response_model=SimilarBooksResponse,
    summary="Get similar books",
    description="""
Get books similar to a given book using content-based filtering.

**Algorithm:**
- Finds books sharing the same genres (weighted by overlap)
- Finds books by the same authors (higher weight)
- Boosts results by average rating
- Returns results sorted by similarity score

**Use cases:**
- "Readers who liked this also liked..."
- Book detail page recommendations
""",
)
@limiter.limit(settings.rate_limit_default)
def get_similar(
    request: Request,
    book_id: int,
    db: DbSession,
    current_user: OptionalUser,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of similar books to return",
            ge=1,
            le=50,
        )
    ] = 10,
) -> SimilarBooksResponse:
    """Get books similar to a given book."""
    # Verify book exists
    book = db.execute(select(Book).where(Book.id == book_id)).scalar_one_or_none()
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )

    # Get books the user has already read (to optionally exclude)
    exclude_book_ids = None
    if current_user:
        user_books = db.execute(
            select(Review.book_id).where(Review.user_id == current_user.id)
        ).scalars().all()
        exclude_book_ids = list(user_books)

    results = get_similar_books(
        db=db,
        book_id=book_id,
        limit=limit,
        exclude_book_ids=exclude_book_ids,
    )

    items = []
    for r in results:
        items.append(SimilarBookItem(
            book=RecommendedBookItem(**r["book"]),
            similarity_score=r.get("similarity_score", 0),
            reasons=r.get("reasons", []),
        ))

    return SimilarBooksResponse(
        items=items,
        source_book_id=book_id,
    )


@router.get(
    "/recommendations",
    response_model=PersonalizedRecommendationsResponse,
    summary="Get personalized recommendations",
    description="""
Get personalized book recommendations for the authenticated user.

**Algorithm (Collaborative Filtering):**
1. Finds books you've rated highly (4+ stars)
2. Identifies users with similar taste (rated same books highly)
3. Recommends books those similar users enjoyed that you haven't read

**Fallback strategies:**
- New users: Falls back to trending books
- No similar users: Uses content-based recommendations from liked books

**Note:** Requires authentication. The more books you review, the better recommendations become.
""",
)
@limiter.limit(settings.rate_limit_default)
def get_personalized_recommendations(
    request: Request,
    db: DbSession,
    current_user: OptionalUser,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of recommendations to return",
            ge=1,
            le=50,
        )
    ] = 10,
) -> PersonalizedRecommendationsResponse:
    """Get personalized recommendations for the current user."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for personalized recommendations",
        )

    results = get_recommendations_for_user(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )

    items = []
    for r in results:
        items.append(PersonalizedRecommendation(
            book=RecommendedBookItem(**r["book"]),
            recommendation_score=r.get("recommendation_score", r.get("similarity_score", r.get("trending_score", 0))),
            reasons=r.get("reasons", []),
        ))

    return PersonalizedRecommendationsResponse(
        items=items,
        user_id=current_user.id,
    )
