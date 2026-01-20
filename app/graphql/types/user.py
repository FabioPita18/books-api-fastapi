"""
GraphQL User Type

Defines the User type for GraphQL queries.
Only exposes public/safe fields.
"""

from datetime import datetime

import strawberry


@strawberry.type
class UserType:
    """
    GraphQL type representing a user (public fields only).

    Maps to the User SQLAlchemy model but only exposes
    fields that are safe to show publicly.
    """

    id: int
    email: str
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


@strawberry.type
class UserPublicType:
    """
    GraphQL type for public user profile (limited fields).

    Used when displaying review authors or other users' profiles.
    """

    id: int
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
