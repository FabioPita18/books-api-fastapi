"""
Genres Router

CRUD endpoints for genres.
Follows the same patterns as the books router.
"""

import math
from typing import List

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.dependencies import DbSession, Pagination
from app.models import Genre, Book
from app.schemas import (
    GenreCreate,
    GenreUpdate,
    GenreResponse,
    BookResponse,
    BookListResponse,
)
from app.services.cache import invalidate_genre_cache
from app.services.rate_limiter import limiter

settings = get_settings()

router = APIRouter(
    prefix="/genres",
    tags=["Genres"],
    responses={
        404: {"description": "Genre not found"},
    },
)


def get_genre_or_404(db: DbSession, genre_id: int) -> Genre:
    """Get a genre by ID or raise 404."""
    stmt = (
        select(Genre)
        .options(selectinload(Genre.books))
        .where(Genre.id == genre_id)
    )
    genre = db.execute(stmt).scalar_one_or_none()

    if genre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Genre with id {genre_id} not found",
        )
    return genre


@router.get(
    "/",
    response_model=List[GenreResponse],
    summary="List all genres",
    description="Get a list of all genres in the system.",
)
@limiter.limit(settings.rate_limit_default)
def list_genres(request: Request, db: DbSession) -> List[GenreResponse]:
    """List all genres."""
    stmt = select(Genre).order_by(Genre.name)
    genres = db.execute(stmt).scalars().all()
    return [GenreResponse.model_validate(g) for g in genres]


@router.get(
    "/{genre_id}",
    response_model=GenreResponse,
    summary="Get a genre by ID",
    description="Retrieve detailed information about a specific genre.",
)
@limiter.limit(settings.rate_limit_default)
def get_genre(
    request: Request,
    genre_id: int,
    db: DbSession,
) -> GenreResponse:
    """Get a single genre by ID."""
    genre = get_genre_or_404(db, genre_id)
    return GenreResponse.model_validate(genre)


@router.get(
    "/{genre_id}/books",
    response_model=BookListResponse,
    summary="Get books in genre",
    description="Get all books in a specific genre.",
)
@limiter.limit(settings.rate_limit_default)
def get_genre_books(
    request: Request,
    genre_id: int,
    db: DbSession,
    pagination: Pagination,
) -> BookListResponse:
    """
    Get all books in a specific genre with pagination.

    Returns a paginated list of books that belong to the specified genre.
    """
    # First verify the genre exists
    get_genre_or_404(db, genre_id)

    # Count total books in this genre
    count_stmt = (
        select(func.count(Book.id))
        .join(Book.genres)
        .where(Genre.id == genre_id)
    )
    total = db.execute(count_stmt).scalar() or 0

    # Calculate total pages
    pages = math.ceil(total / pagination.per_page) if total > 0 else 0

    # Fetch books for current page
    stmt = (
        select(Book)
        .join(Book.genres)
        .where(Genre.id == genre_id)
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


@router.post(
    "/",
    response_model=GenreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new genre",
    description="Create a new genre in the system.",
)
@limiter.limit(settings.rate_limit_write)
def create_genre(
    request: Request,
    genre_data: GenreCreate,
    db: DbSession,
) -> GenreResponse:
    """
    Create a new genre.

    Genre names must be unique. If a genre with the same name exists,
    a 409 Conflict error is returned.
    """
    genre = Genre(
        name=genre_data.name,
        description=genre_data.description,
    )

    try:
        db.add(genre)
        db.commit()
        db.refresh(genre)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Genre with name '{genre_data.name}' already exists",
        )

    # Invalidate related caches
    invalidate_genre_cache()

    return GenreResponse.model_validate(genre)


@router.put(
    "/{genre_id}",
    response_model=GenreResponse,
    summary="Update a genre",
    description="Update an existing genre's information.",
)
@limiter.limit(settings.rate_limit_write)
def update_genre(
    request: Request,
    genre_id: int,
    genre_data: GenreUpdate,
    db: DbSession,
) -> GenreResponse:
    """Update an existing genre."""
    genre = get_genre_or_404(db, genre_id)

    update_data = genre_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(genre, field, value)

    try:
        db.commit()
        db.refresh(genre)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Genre with name '{genre_data.name}' already exists",
        )

    # Invalidate related caches
    invalidate_genre_cache(genre_id)

    return GenreResponse.model_validate(genre)


@router.delete(
    "/{genre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a genre",
    description="Permanently delete a genre from the database.",
)
@limiter.limit(settings.rate_limit_write)
def delete_genre(
    request: Request,
    genre_id: int,
    db: DbSession,
) -> None:
    """Delete a genre."""
    genre = get_genre_or_404(db, genre_id)
    db.delete(genre)
    db.commit()

    # Invalidate related caches
    invalidate_genre_cache(genre_id)
