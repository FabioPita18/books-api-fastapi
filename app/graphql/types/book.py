"""
GraphQL Book Type

Defines the Book type and related types for GraphQL queries.
"""

from datetime import date, datetime
from decimal import Decimal

import strawberry

from app.graphql.types.author import AuthorType
from app.graphql.types.genre import GenreType
from app.graphql.types.review import ReviewType


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
    reviews: list[ReviewType] = strawberry.field(default_factory=list)


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


@strawberry.input
class BookInput:
    """
    Input type for creating a book.
    """

    title: str
    isbn: str | None = None
    description: str | None = None
    publication_date: date | None = None
    page_count: int | None = None
    price: Decimal | None = None
    author_ids: list[int] = strawberry.field(default_factory=list)
    genre_ids: list[int] = strawberry.field(default_factory=list)


@strawberry.input
class BookUpdateInput:
    """
    Input type for updating a book.
    All fields are optional.
    """

    title: str | None = None
    isbn: str | None = None
    description: str | None = None
    publication_date: date | None = None
    page_count: int | None = None
    price: Decimal | None = None
    author_ids: list[int] | None = None
    genre_ids: list[int] | None = None


@strawberry.input
class SearchFiltersInput:
    """
    Input type for search filters.
    """

    genres: list[str] | None = None
    min_year: int | None = None
    max_year: int | None = None
    min_rating: float | None = None
    min_price: float | None = None
    max_price: float | None = None


@strawberry.type
class SearchResultItem:
    """
    A single search result with relevance score.
    """

    book: BookType
    score: float | None = None


@strawberry.type
class SearchFacet:
    """
    A facet item for filtering.
    """

    name: str
    count: int


@strawberry.type
class SearchResults:
    """
    Search results with facets.
    """

    items: list[SearchResultItem]
    total: int
    page: int
    pages: int
    facets: list[SearchFacet] = strawberry.field(default_factory=list)
