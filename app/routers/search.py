"""
Advanced Search Router

Provides enhanced search capabilities using Elasticsearch with
PostgreSQL fallback.

Features:
- Full-text search with fuzzy matching
- Faceted search (filter by genre, year, rating)
- Relevance scoring
- Pagination
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.dependencies import DbSession
from app.services.rate_limiter import limiter
from app.services.search import search_books_advanced

settings = get_settings()

# =============================================================================
# Router Configuration
# =============================================================================

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


# =============================================================================
# Response Models
# =============================================================================


class SearchBookItem(BaseModel):
    """Book item in search results."""

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
    relevance_score: float | None = Field(default=None, description="Relevance score (ES only)")

    class Config:
        from_attributes = True


class GenreFacet(BaseModel):
    """Genre facet item."""

    name: str
    count: int


class YearFacet(BaseModel):
    """Year facet item."""

    year: int
    count: int


class RatingFacet(BaseModel):
    """Rating range facet item."""

    range: str
    count: int


class SearchFacets(BaseModel):
    """Search facets (aggregations)."""

    genres: list[GenreFacet] = Field(default_factory=list)
    years: list[YearFacet] = Field(default_factory=list)
    ratings: list[RatingFacet] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Advanced search response with facets."""

    items: list[SearchBookItem]
    total: int
    page: int
    size: int
    pages: int
    facets: SearchFacets
    fallback: bool = Field(
        default=False,
        description="True if PostgreSQL fallback was used instead of Elasticsearch"
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=SearchResponse,
    summary="Advanced book search",
    description="""
Search books with full-text search, fuzzy matching, and filters.

**Search Features:**
- Full-text search across title, description, and authors
- Fuzzy matching for typo tolerance (e.g., "pragmtic" finds "pragmatic")
- Relevance scoring (most relevant results first)

**Filters:**
- `genres`: Filter by genre names (can specify multiple)
- `min_year` / `max_year`: Publication year range
- `min_rating`: Minimum average rating (1-5)
- `min_price` / `max_price`: Price range

**Facets:**
Response includes aggregations for filtering:
- Genre distribution
- Publication years
- Rating ranges

**Fallback:**
If Elasticsearch is unavailable, falls back to PostgreSQL search
(without fuzzy matching or relevance scoring).
""",
)
@limiter.limit(settings.rate_limit_search)
async def search_books(
    request: Request,
    db: DbSession,
    q: Annotated[
        str | None,
        Query(
            description="Search query (searches title, description, authors)",
            min_length=1,
            max_length=200,
            examples=["pragmatic programmer", "science fiction", "Orwell"]
        )
    ] = None,
    genres: Annotated[
        list[str] | None,
        Query(
            description="Filter by genre names",
            examples=["Fiction", "Science Fiction"]
        )
    ] = None,
    min_year: Annotated[
        int | None,
        Query(
            description="Minimum publication year",
            ge=1000,
            le=2100,
            examples=[1950, 2000]
        )
    ] = None,
    max_year: Annotated[
        int | None,
        Query(
            description="Maximum publication year",
            ge=1000,
            le=2100,
            examples=[2000, 2024]
        )
    ] = None,
    min_rating: Annotated[
        float | None,
        Query(
            description="Minimum average rating",
            ge=1.0,
            le=5.0,
            examples=[3.5, 4.0]
        )
    ] = None,
    min_price: Annotated[
        float | None,
        Query(
            description="Minimum price",
            ge=0,
            examples=[10.0, 20.0]
        )
    ] = None,
    max_price: Annotated[
        float | None,
        Query(
            description="Maximum price",
            ge=0,
            examples=[50.0, 100.0]
        )
    ] = None,
    page: Annotated[
        int,
        Query(
            description="Page number (1-indexed)",
            ge=1,
            examples=[1, 2]
        )
    ] = 1,
    size: Annotated[
        int,
        Query(
            description="Results per page",
            ge=1,
            le=100,
            examples=[10, 20]
        )
    ] = 20,
    fuzzy: Annotated[
        bool,
        Query(
            description="Enable fuzzy matching for typo tolerance"
        )
    ] = True,
) -> SearchResponse:
    """
    Advanced search endpoint with Elasticsearch.

    Provides full-text search with fuzzy matching, filters, and faceted results.
    Falls back to PostgreSQL if Elasticsearch is unavailable.
    """
    result = await search_books_advanced(
        db=db,
        query=q,
        genres=genres,
        min_year=min_year,
        max_year=max_year,
        min_rating=min_rating,
        min_price=min_price,
        max_price=max_price,
        page=page,
        size=size,
        fuzzy=fuzzy,
    )

    # Convert to response model
    return SearchResponse(
        items=[SearchBookItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
        facets=SearchFacets(
            genres=[GenreFacet(**g) for g in result.get("facets", {}).get("genres", [])],
            years=[YearFacet(**y) for y in result.get("facets", {}).get("years", [])],
            ratings=[RatingFacet(**r) for r in result.get("facets", {}).get("ratings", [])],
        ),
        fallback=result.get("fallback", False),
    )
