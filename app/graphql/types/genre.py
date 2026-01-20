"""
GraphQL Genre Type

Defines the Genre type for GraphQL queries.
"""

import strawberry


@strawberry.type
class GenreType:
    """
    GraphQL type representing a book genre.

    Maps to the Genre SQLAlchemy model.
    """

    id: int
    name: str
    description: str | None = None


@strawberry.type
class GenreConnection:
    """
    Paginated list of genres.

    Follows the Connection pattern for GraphQL pagination.
    """

    items: list[GenreType]
    total: int
    page: int
    per_page: int
    pages: int


@strawberry.input
class GenreInput:
    """
    Input type for creating/updating genres.
    """

    name: str
    description: str | None = None
