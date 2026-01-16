"""
Books Router

Complete CRUD endpoints for books.

This is the most comprehensive router, demonstrating:
- All CRUD operations
- Pagination
- Error handling
- Relationship management
- Request/response validation
- OpenAPI documentation
- Rate limiting
"""

import math

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import BookFilters, DbSession, Pagination, RequireAPIKey
from app.models import Author, Book, Genre
from app.schemas import (
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
)
from app.services.cache import (
    cache_get,
    cache_set,
    invalidate_book_cache,
    make_cache_key,
)
from app.services.rate_limiter import limiter

settings = get_settings()

# =============================================================================
# Router Configuration
# =============================================================================
# APIRouter groups related endpoints together
#
# Parameters:
# - prefix: URL prefix for all routes (e.g., /books)
# - tags: OpenAPI tags for documentation grouping
# - responses: Common responses for all endpoints

router = APIRouter(
    prefix="/books",
    tags=["Books"],
    responses={
        404: {"description": "Book not found"},
    },
)


# =============================================================================
# Helper Functions
# =============================================================================
def get_book_or_404(db: DbSession, book_id: int) -> Book:
    """
    Get a book by ID or raise 404.

    This is a common pattern: check if resource exists,
    return it or raise appropriate HTTP error.

    Uses selectinload to eagerly load relationships,
    preventing N+1 query problems.

    Args:
        db: Database session
        book_id: ID of the book to find

    Returns:
        Book instance

    Raises:
        HTTPException: 404 if book not found
    """
    # SQLAlchemy 2.0 uses select() instead of query()
    stmt = (
        select(Book)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .where(Book.id == book_id)
    )
    book = db.execute(stmt).scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )

    return book


def apply_book_filters(stmt, filters: BookFilters, db: DbSession):
    """
    Apply search and filter parameters to a book query.

    This function builds a dynamic query based on the provided filters:
    - q: General search across title and author name
    - title: Filter by book title (partial match)
    - author: Filter by author name (partial match)
    - genre_id: Filter by genre
    - min_year/max_year: Filter by publication year range
    - min_price/max_price: Filter by price range

    Args:
        stmt: SQLAlchemy select statement to modify
        filters: BookSearchParams instance with filter values
        db: Database session for subqueries

    Returns:
        Modified SQLAlchemy select statement with filters applied
    """
    # General search (searches both title and author name)
    if filters.q:
        search_term = f"%{filters.q.lower()}%"
        # Subquery to find books by author name
        author_book_ids = (
            select(Book.id)
            .join(Book.authors)
            .where(func.lower(Author.name).like(search_term))
        )
        stmt = stmt.where(
            or_(
                func.lower(Book.title).like(search_term),
                Book.id.in_(author_book_ids),
            )
        )

    # Filter by title (partial match, case-insensitive)
    if filters.title:
        stmt = stmt.where(func.lower(Book.title).like(f"%{filters.title.lower()}%"))

    # Filter by author name (partial match, case-insensitive)
    if filters.author:
        author_book_ids = (
            select(Book.id)
            .join(Book.authors)
            .where(func.lower(Author.name).like(f"%{filters.author.lower()}%"))
        )
        stmt = stmt.where(Book.id.in_(author_book_ids))

    # Filter by genre ID
    if filters.genre_id:
        genre_book_ids = (
            select(Book.id)
            .join(Book.genres)
            .where(Genre.id == filters.genre_id)
        )
        stmt = stmt.where(Book.id.in_(genre_book_ids))

    # Filter by publication year range
    if filters.min_year:
        stmt = stmt.where(
            extract("year", Book.publication_date) >= filters.min_year
        )
    if filters.max_year:
        stmt = stmt.where(
            extract("year", Book.publication_date) <= filters.max_year
        )

    # Filter by price range
    if filters.min_price is not None:
        stmt = stmt.where(Book.price >= filters.min_price)
    if filters.max_price is not None:
        stmt = stmt.where(Book.price <= filters.max_price)

    return stmt


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get(
    "/search",
    response_model=BookListResponse,
    summary="Search books",
    description="Search books by title, author, genre, year range, or price range.",
)
@limiter.limit(settings.rate_limit_search)
def search_books(
    request: Request,
    db: DbSession,
    pagination: Pagination,
    filters: BookFilters,
) -> BookListResponse:
    """
    Search and filter books with pagination.

    This endpoint provides comprehensive search capabilities:
    - q: General search across title and author name
    - title: Filter by book title
    - author: Filter by author name
    - genre_id: Filter by genre
    - min_year/max_year: Publication year range
    - min_price/max_price: Price range

    All filters can be combined. Results are paginated.

    Examples:
        GET /api/books/search?q=orwell
        GET /api/books/search?genre_id=1&min_year=1900&max_year=1960
        GET /api/books/search?author=hemingway&min_price=10
    """
    # Build base query
    base_stmt = select(Book)

    # Apply filters
    filtered_stmt = apply_book_filters(base_stmt, filters, db)

    # Count total matching books
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Calculate total pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch books for current page with relationships
    stmt = (
        filtered_stmt
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .offset(pagination.skip)
        .limit(pagination.per_page)
        .order_by(Book.created_at.desc())
    )
    books = db.execute(stmt).scalars().all()

    return BookListResponse(
        items=[BookResponse.model_validate(book) for book in books],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=pages,
    )


@router.get(
    "/",
    response_model=BookListResponse,
    summary="List all books",
    description="Get a paginated list of all books with optional filtering.",
)
@limiter.limit(settings.rate_limit_default)
def list_books(
    request: Request,
    db: DbSession,
    pagination: Pagination,
    filters: BookFilters,
) -> BookListResponse:
    """
    List all books with pagination and optional filtering.

    Supports all the same filters as /search endpoint:
    - title: Filter by book title
    - author: Filter by author name
    - genre_id: Filter by genre
    - min_year/max_year: Publication year range
    - min_price/max_price: Price range

    Returns:
        Paginated list of books with metadata
    """
    # Build base query
    base_stmt = select(Book)

    # Apply filters if any are provided
    if filters.has_filters:
        base_stmt = apply_book_filters(base_stmt, filters, db)

    # Count total books for pagination metadata
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Calculate total pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch books for current page with relationships
    stmt = (
        base_stmt
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .offset(pagination.skip)
        .limit(pagination.per_page)
        .order_by(Book.created_at.desc())  # Newest first
    )
    books = db.execute(stmt).scalars().all()

    return BookListResponse(
        items=[BookResponse.model_validate(book) for book in books],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=pages,
    )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get a book by ID",
    description="Retrieve detailed information about a specific book.",
)
@limiter.limit(settings.rate_limit_default)
def get_book(
    request: Request,
    book_id: int,
    db: DbSession,
) -> BookResponse:
    """
    Get a single book by its ID.

    Uses Redis caching to improve performance for frequently accessed books.

    Args:
        book_id: The ID of the book to retrieve
        db: Database session (injected)

    Returns:
        Book details with authors and genres

    Raises:
        HTTPException: 404 if book not found
    """
    # Try to get from cache first
    cache_key = make_cache_key("book", book_id)
    cached = cache_get(cache_key)
    if cached:
        return BookResponse.model_validate(cached)

    # Not in cache, fetch from database
    book = get_book_or_404(db, book_id)
    response = BookResponse.model_validate(book)

    # Cache the result
    settings = get_settings()
    cache_set(cache_key, response.model_dump(mode="json"), ttl=settings.cache_ttl_books)

    return response


@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new book",
    description="Create a new book with optional author and genre associations. Requires API key.",
)
@limiter.limit(settings.rate_limit_write)
def create_book(
    request: Request,
    book_data: BookCreate,
    db: DbSession,
    _: RequireAPIKey,
) -> BookResponse:
    """
    Create a new book.

    Demonstrates:
    - Request body validation with Pydantic
    - 201 Created status code
    - Relationship management (authors, genres)
    - Database transaction handling

    Args:
        book_data: Validated book data from request body
        db: Database session

    Returns:
        Created book with all relationships

    Raises:
        HTTPException: 400 if author/genre IDs are invalid
    """
    # Create book instance (exclude relationship IDs from model creation)
    book = Book(
        title=book_data.title,
        isbn=book_data.isbn,
        description=book_data.description,
        publication_date=book_data.publication_date,
        page_count=book_data.page_count,
        price=book_data.price,
    )

    # Handle author associations if provided
    if book_data.author_ids:
        authors = db.execute(
            select(Author).where(Author.id.in_(book_data.author_ids))
        ).scalars().all()

        # Validate all author IDs exist
        if len(authors) != len(book_data.author_ids):
            found_ids = {a.id for a in authors}
            missing = set(book_data.author_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authors not found: {missing}",
            )
        book.authors = list(authors)

    # Handle genre associations if provided
    if book_data.genre_ids:
        genres = db.execute(
            select(Genre).where(Genre.id.in_(book_data.genre_ids))
        ).scalars().all()

        if len(genres) != len(book_data.genre_ids):
            found_ids = {g.id for g in genres}
            missing = set(book_data.genre_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Genres not found: {missing}",
            )
        book.genres = list(genres)

    # Save to database
    db.add(book)
    db.commit()
    db.refresh(book)

    # Invalidate related caches
    invalidate_book_cache()

    return BookResponse.model_validate(book)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    summary="Update a book",
    description="Update an existing book's information and associations. Requires API key.",
)
@limiter.limit(settings.rate_limit_write)
def update_book(
    request: Request,
    book_id: int,
    book_data: BookUpdate,
    db: DbSession,
    _: RequireAPIKey,
) -> BookResponse:
    """
    Update an existing book.

    Uses PUT semantics but with optional fields (PATCH-like behavior).
    Only provided fields are updated.

    Args:
        book_id: ID of book to update
        book_data: Fields to update
        db: Database session

    Returns:
        Updated book

    Raises:
        HTTPException: 404 if book not found
        HTTPException: 400 if author/genre IDs are invalid
    """
    book = get_book_or_404(db, book_id)

    # Update only provided fields
    # model_dump(exclude_unset=True) returns only fields that were set
    update_data = book_data.model_dump(exclude_unset=True)

    # Handle author_ids separately (it's a relationship, not a column)
    if "author_ids" in update_data:
        author_ids = update_data.pop("author_ids")
        if author_ids is not None:
            authors = db.execute(
                select(Author).where(Author.id.in_(author_ids))
            ).scalars().all()

            if len(authors) != len(author_ids):
                found_ids = {a.id for a in authors}
                missing = set(author_ids) - found_ids
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Authors not found: {missing}",
                )
            book.authors = list(authors)

    # Handle genre_ids separately
    if "genre_ids" in update_data:
        genre_ids = update_data.pop("genre_ids")
        if genre_ids is not None:
            genres = db.execute(
                select(Genre).where(Genre.id.in_(genre_ids))
            ).scalars().all()

            if len(genres) != len(genre_ids):
                found_ids = {g.id for g in genres}
                missing = set(genre_ids) - found_ids
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Genres not found: {missing}",
                )
            book.genres = list(genres)

    # Update remaining fields
    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)

    # Invalidate related caches
    invalidate_book_cache(book_id)

    return BookResponse.model_validate(book)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
    description="Permanently delete a book from the database. Requires API key.",
)
@limiter.limit(settings.rate_limit_write)
def delete_book(
    request: Request,
    book_id: int,
    db: DbSession,
    _: RequireAPIKey,
) -> None:
    """
    Delete a book.

    Returns 204 No Content on success (standard for DELETE).
    The None return type and status_code=204 tell FastAPI
    not to send a response body.

    Args:
        book_id: ID of book to delete
        db: Database session

    Raises:
        HTTPException: 404 if book not found
    """
    book = get_book_or_404(db, book_id)
    db.delete(book)
    db.commit()

    # Invalidate related caches
    invalidate_book_cache(book_id)
