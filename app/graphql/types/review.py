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
    Includes the public user info of the reviewer.
    """

    id: int
    rating: int
    title: str | None = None
    content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # The user who wrote the review (public info only)
    user: UserPublicType | None = None

    # Book ID for reference
    book_id: int | None = None


@strawberry.type
class ReviewConnection:
    """
    Paginated list of reviews.

    Follows the Connection pattern for GraphQL pagination.
    """

    items: list[ReviewType]
    total: int
    page: int
    per_page: int
    pages: int


@strawberry.input
class ReviewInput:
    """
    Input type for creating a review.
    """

    rating: int
    title: str | None = None
    content: str | None = None


@strawberry.input
class ReviewUpdateInput:
    """
    Input type for updating a review.
    All fields are optional.
    """

    rating: int | None = None
    title: str | None = None
    content: str | None = None
