"""
FastAPI Dependencies Module

Dependencies are reusable components injected into route handlers.
FastAPI's Depends() function manages their lifecycle.

WHY Dependency Injection?
=========================
1. Reusability: Write once, use in many routes
2. Testing: Easy to mock dependencies in tests
3. Separation of Concerns: Routes focus on business logic
4. Lifecycle Management: FastAPI handles creation/cleanup

Common Dependency Patterns:
- Database sessions (per-request)
- Authentication (verify user)
- Pagination parameters
- Rate limiting
- Caching
"""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

settings = get_settings()

# =============================================================================
# Type Aliases with Annotated
# =============================================================================
# Annotated allows attaching metadata to type hints.
# This makes route signatures cleaner and more reusable.
#
# Instead of writing:
#   def get_books(db: Session = Depends(get_db)):
#
# You can write:
#   def get_books(db: DbSession):

DbSession = Annotated[Session, Depends(get_db)]


# =============================================================================
# Pagination Parameters
# =============================================================================
class PaginationParams:
    """
    Common pagination parameters for list endpoints.

    This class-based dependency captures pagination logic:
    - page: Which page to return (1-indexed for user-friendliness)
    - per_page: How many items per page
    - skip: Calculated offset for database query

    Usage in route:
        @router.get("/books/")
        def get_books(
            db: DbSession,
            pagination: PaginationParams = Depends()
        ):
            books = db.query(Book).offset(pagination.skip).limit(pagination.per_page).all()
    """

    def __init__(
        self,
        page: int = Query(
            default=1,
            ge=1,
            description="Page number (1-indexed)",
            examples=[1, 2, 3],
        ),
        per_page: int = Query(
            default=10,
            ge=1,
            le=100,  # Limit to prevent abuse
            description="Number of items per page (max 100)",
            examples=[10, 25, 50],
        ),
    ) -> None:
        """
        Initialize pagination parameters.

        Query() is used because these come from URL query parameters:
            GET /books/?page=2&per_page=20

        Args:
            page: Page number (starts at 1 for user-friendliness)
            per_page: Number of items per page
        """
        self.page = page
        self.per_page = per_page

    @property
    def skip(self) -> int:
        """
        Calculate the number of records to skip.

        Database OFFSET uses 0-based indexing, but users expect 1-based pages.
        Page 1 → skip 0 items
        Page 2 → skip per_page items
        Page 3 → skip 2 * per_page items

        Returns:
            Number of records to skip in database query
        """
        return (self.page - 1) * self.per_page


# Type alias for cleaner route signatures
Pagination = Annotated[PaginationParams, Depends()]


# =============================================================================
# Common Query Parameters
# =============================================================================
def get_search_query(
    q: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Search query string",
        examples=["orwell", "science fiction"],
    ),
) -> str | None:
    """
    Common search query parameter.

    Returns None if no search query provided, otherwise the search string.

    Usage:
        @router.get("/books/")
        def search_books(search: str | None = Depends(get_search_query)):
            if search:
                # Filter books by search term
    """
    return q


SearchQuery = Annotated[str | None, Depends(get_search_query)]


# =============================================================================
# Book Search Filters
# =============================================================================
class BookSearchParams:
    """
    Search and filter parameters for book endpoints.

    Supports:
    - Text search (title, author name)
    - Genre filtering
    - Publication year range
    - Price range

    All parameters are optional and can be combined.

    Usage:
        GET /api/books/?title=orwell&genre_id=1&min_year=1940&max_year=1960
        GET /api/books/search/?q=dystopian&min_price=10&max_price=20
    """

    def __init__(
        self,
        q: str | None = Query(
            default=None,
            min_length=1,
            max_length=100,
            description="Search query (searches title and author name)",
            examples=["orwell", "dystopian"],
        ),
        title: str | None = Query(
            default=None,
            min_length=1,
            max_length=100,
            description="Filter by title (partial match, case-insensitive)",
            examples=["1984", "pride"],
        ),
        author: str | None = Query(
            default=None,
            min_length=1,
            max_length=100,
            description="Filter by author name (partial match, case-insensitive)",
            examples=["orwell", "austen"],
        ),
        genre_id: int | None = Query(
            default=None,
            ge=1,
            description="Filter by genre ID",
            examples=[1, 2],
        ),
        min_year: int | None = Query(
            default=None,
            ge=1000,
            le=9999,
            description="Minimum publication year",
            examples=[1900, 1950],
        ),
        max_year: int | None = Query(
            default=None,
            ge=1000,
            le=9999,
            description="Maximum publication year",
            examples=[2000, 2024],
        ),
        min_price: float | None = Query(
            default=None,
            ge=0,
            description="Minimum price",
            examples=[0, 10.00],
        ),
        max_price: float | None = Query(
            default=None,
            ge=0,
            description="Maximum price",
            examples=[20.00, 50.00],
        ),
    ) -> None:
        self.q = q
        self.title = title
        self.author = author
        self.genre_id = genre_id
        self.min_year = min_year
        self.max_year = max_year
        self.min_price = min_price
        self.max_price = max_price

    @property
    def has_filters(self) -> bool:
        """Check if any filters are applied."""
        return any([
            self.q,
            self.title,
            self.author,
            self.genre_id,
            self.min_year,
            self.max_year,
            self.min_price,
            self.max_price,
        ])


# Type alias for cleaner route signatures
BookFilters = Annotated[BookSearchParams, Depends()]


# =============================================================================
# API Key Authentication
# =============================================================================
def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """
    Extract and validate API key from request header.

    This dependency is used for endpoints that REQUIRE authentication.
    It will raise 401 if the key is missing or invalid.

    Args:
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        The validated API key string

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Import here to avoid circular imports
    from app.services.auth import validate_api_key

    # Check if authentication is disabled (for development)
    if not settings.api_key_enabled:
        return None

    # Check if key is provided
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate the key
    api_key = validate_api_key(db, x_api_key)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


def get_optional_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """
    Extract API key from request header (optional).

    This dependency is used for endpoints that optionally accept authentication.
    It returns None if no key is provided (no error raised).

    Args:
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        The API key string if provided and valid, None otherwise
    """
    from app.services.auth import validate_api_key

    if not x_api_key:
        return None

    api_key = validate_api_key(db, x_api_key)
    return x_api_key if api_key else None


# Type aliases for cleaner route signatures
RequireAPIKey = Annotated[str, Depends(get_api_key)]
OptionalAPIKey = Annotated[Optional[str], Depends(get_optional_api_key)]
