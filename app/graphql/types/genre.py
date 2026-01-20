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
