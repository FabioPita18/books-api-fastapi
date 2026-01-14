"""
Genres Router

CRUD endpoints for genres.
Follows the same patterns as the books router.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession
from app.models import Genre
from app.schemas import (
    GenreCreate,
    GenreUpdate,
    GenreResponse,
)

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
def list_genres(db: DbSession) -> List[GenreResponse]:
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
def get_genre(
    genre_id: int,
    db: DbSession,
) -> GenreResponse:
    """Get a single genre by ID."""
    genre = get_genre_or_404(db, genre_id)
    return GenreResponse.model_validate(genre)


@router.post(
    "/",
    response_model=GenreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new genre",
    description="Create a new genre in the system.",
)
def create_genre(
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

    return GenreResponse.model_validate(genre)


@router.put(
    "/{genre_id}",
    response_model=GenreResponse,
    summary="Update a genre",
    description="Update an existing genre's information.",
)
def update_genre(
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

    return GenreResponse.model_validate(genre)


@router.delete(
    "/{genre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a genre",
    description="Permanently delete a genre from the database.",
)
def delete_genre(
    genre_id: int,
    db: DbSession,
) -> None:
    """Delete a genre."""
    genre = get_genre_or_404(db, genre_id)
    db.delete(genre)
    db.commit()
