"""
Authors Router

CRUD endpoints for authors.
Follows the same patterns as the books router.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import DbSession
from app.models import Author
from app.schemas import (
    AuthorCreate,
    AuthorUpdate,
    AuthorResponse,
)

router = APIRouter(
    prefix="/authors",
    tags=["Authors"],
    responses={
        404: {"description": "Author not found"},
    },
)


def get_author_or_404(db: DbSession, author_id: int) -> Author:
    """Get an author by ID or raise 404."""
    stmt = (
        select(Author)
        .options(selectinload(Author.books))
        .where(Author.id == author_id)
    )
    author = db.execute(stmt).scalar_one_or_none()

    if author is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Author with id {author_id} not found",
        )
    return author


@router.get(
    "/",
    response_model=List[AuthorResponse],
    summary="List all authors",
    description="Get a list of all authors in the system.",
)
def list_authors(db: DbSession) -> List[AuthorResponse]:
    """List all authors."""
    stmt = select(Author).order_by(Author.name)
    authors = db.execute(stmt).scalars().all()
    return [AuthorResponse.model_validate(a) for a in authors]


@router.get(
    "/{author_id}",
    response_model=AuthorResponse,
    summary="Get an author by ID",
    description="Retrieve detailed information about a specific author.",
)
def get_author(
    author_id: int,
    db: DbSession,
) -> AuthorResponse:
    """Get a single author by ID."""
    author = get_author_or_404(db, author_id)
    return AuthorResponse.model_validate(author)


@router.post(
    "/",
    response_model=AuthorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new author",
    description="Create a new author in the system.",
)
def create_author(
    author_data: AuthorCreate,
    db: DbSession,
) -> AuthorResponse:
    """Create a new author."""
    author = Author(
        name=author_data.name,
        bio=author_data.bio,
    )

    db.add(author)
    db.commit()
    db.refresh(author)

    return AuthorResponse.model_validate(author)


@router.put(
    "/{author_id}",
    response_model=AuthorResponse,
    summary="Update an author",
    description="Update an existing author's information.",
)
def update_author(
    author_id: int,
    author_data: AuthorUpdate,
    db: DbSession,
) -> AuthorResponse:
    """Update an existing author."""
    author = get_author_or_404(db, author_id)

    update_data = author_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(author, field, value)

    db.commit()
    db.refresh(author)

    return AuthorResponse.model_validate(author)


@router.delete(
    "/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an author",
    description="Permanently delete an author from the database.",
)
def delete_author(
    author_id: int,
    db: DbSession,
) -> None:
    """Delete an author."""
    author = get_author_or_404(db, author_id)
    db.delete(author)
    db.commit()
