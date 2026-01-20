"""
GraphQL Book Type

Defines the Book type and related types for GraphQL queries.
"""

from datetime import date, datetime
from decimal import Decimal

import strawberry

from app.graphql.types.author import AuthorType
from app.graphql.types.genre import GenreType


@strawberry.type
class BookType:
    """
    GraphQL type representing a book.

    Maps to the Book SQLAlchemy model with relationships.
    """

    id: int
    title: str
    isbn: str | None = None
    description: str | None = None
    publication_date: date | None = None
    page_count: int | None = None
    price: Decimal | None = None
    average_rating: float | None = None
    review_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Relationships (populated by resolvers)
    authors: list[AuthorType] = strawberry.field(default_factory=list)
    genres: list[GenreType] = strawberry.field(default_factory=list)


@strawberry.type
class BookConnection:
    """
    Paginated list of books.

    Follows the Connection pattern for GraphQL pagination.
    """

    items: list[BookType]
    total: int
    page: int
    per_page: int
    pages: int
