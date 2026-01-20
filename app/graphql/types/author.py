"""
GraphQL Author Type

Defines the Author type for GraphQL queries.
"""

from datetime import date

import strawberry


@strawberry.type
class AuthorType:
    """
    GraphQL type representing a book author.

    Maps to the Author SQLAlchemy model.
    """

    id: int
    name: str
    bio: str | None = None
    birth_date: date | None = None
    website: str | None = None
