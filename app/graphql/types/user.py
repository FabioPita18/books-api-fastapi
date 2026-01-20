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
    GraphQL type representing a user (full profile for authenticated user).

    Maps to the User SQLAlchemy model but only exposes
    fields that are safe to show.
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
    Does not expose email or sensitive information.
    """

    id: int
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


@strawberry.type
class AuthPayload:
    """
    Response type for authentication mutations.

    Contains the JWT tokens and user information.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserType | None = None


@strawberry.input
class LoginInput:
    """
    Input type for login mutation.
    """

    email: str
    password: str


@strawberry.input
class RegisterInput:
    """
    Input type for user registration.
    """

    email: str
    password: str
    full_name: str | None = None
