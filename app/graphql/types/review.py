"""
GraphQL Review Type

Defines the Review type for GraphQL queries.
"""

from datetime import datetime

import strawberry

from app.graphql.types.user import UserPublicType


@strawberry.type
class ReviewType:
    """
    GraphQL type representing a book review.

    Maps to the Review SQLAlchemy model.
    """

    id: int
    rating: int
    title: str | None = None
    content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Nested user (public info only)
    user: UserPublicType | None = None

    # Book ID (to avoid circular imports, full book fetched separately)
    book_id: int | None = None
