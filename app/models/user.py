"""
User Model

Represents a user in the books database with support for both
email/password authentication and social OAuth providers.

SQLAlchemy 2.0 Features Used:
- mapped_column(): New way to define columns with full type support
- Mapped[]: Type hint wrapper for SQLAlchemy columns
- relationship(): Define relationships between models
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.review import Review


class AuthProvider(str, Enum):
    """
    Authentication providers supported by the system.

    - LOCAL: Email/password registration
    - GOOGLE: Google OAuth
    - GITHUB: GitHub OAuth
    """
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """
    User model representing registered users in the system.

    Table: users

    Supports both email/password authentication and social OAuth.
    OAuth users may not have a password (hashed_password is nullable).

    Relationships:
    - reviews: One-to-Many relationship with Review model

    Indexes:
    - Primary key on id (automatic)
    - email: Unique index for login lookups
    - username: Unique index for profile URLs
    - provider_user_id: For OAuth account linking

    Example:
        # Email/password user
        user = User(
            email="john@example.com",
            username="johndoe",
            hashed_password=hash_password("secret123"),
            auth_provider=AuthProvider.LOCAL,
        )

        # OAuth user
        user = User(
            email="jane@gmail.com",
            username="janedoe",
            auth_provider=AuthProvider.GOOGLE,
            provider_user_id="google-123456",
        )
    """

    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------------------------
    # Authentication Fields
    # -------------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="User's email address (used for login)"
    )

    # Nullable because OAuth users don't have passwords
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt hashed password (null for OAuth users)"
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique username for profile URLs"
    )

    # -------------------------------------------------------------------------
    # Profile Fields
    # -------------------------------------------------------------------------
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User's full display name"
    )

    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="URL to user's avatar image"
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User biography"
    )

    # -------------------------------------------------------------------------
    # Account Status
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the account is active"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email has been verified"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has admin privileges"
    )

    # -------------------------------------------------------------------------
    # OAuth Fields
    # -------------------------------------------------------------------------
    auth_provider: Mapped[str] = mapped_column(
        String(20),
        default=AuthProvider.LOCAL.value,
        nullable=False,
        comment="Authentication provider (local, google, github)"
    )

    provider_user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User ID from OAuth provider"
    )

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the user registered"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When the user profile was last updated"
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user last logged in"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return f"User(id={self.id}, email='{self.email}', username='{self.username}')"
