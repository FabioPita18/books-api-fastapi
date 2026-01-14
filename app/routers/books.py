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
"""

import math
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.dependencies import DbSession, Pagination
from app.models import Book, Author, Genre
from app.schemas import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookListResponse,
)

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


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=BookListResponse,
    summary="List all books",
    description="Get a paginated list of all books with their authors and genres.",
)
def list_books(
    db: DbSession,
    pagination: Pagination,
) -> BookListResponse:
    """
    List all books with pagination.

    This endpoint demonstrates:
    - Pagination using query parameters
    - Eager loading of relationships
    - Response model for structured output

    Returns:
        Paginated list of books with metadata
    """
    # Count total books for pagination metadata
    count_stmt = select(func.count()).select_from(Book)
    total = db.execute(count_stmt).scalar() or 0

    # Calculate total pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch books for current page with relationships
    stmt = (
        select(Book)
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
def get_book(
    book_id: int,
    db: DbSession,
) -> BookResponse:
    """
    Get a single book by its ID.

    Path parameters (like book_id) are automatically parsed from the URL.
    FastAPI validates that book_id is an integer.

    Args:
        book_id: The ID of the book to retrieve
        db: Database session (injected)

    Returns:
        Book details with authors and genres

    Raises:
        HTTPException: 404 if book not found
    """
    book = get_book_or_404(db, book_id)
    return BookResponse.model_validate(book)


@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new book",
    description="Create a new book with optional author and genre associations.",
)
def create_book(
    book_data: BookCreate,
    db: DbSession,
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

    return BookResponse.model_validate(book)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    summary="Update a book",
    description="Update an existing book's information and associations.",
)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: DbSession,
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

    return BookResponse.model_validate(book)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
    description="Permanently delete a book from the database.",
)
def delete_book(
    book_id: int,
    db: DbSession,
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
