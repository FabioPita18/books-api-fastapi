"""
User Pydantic Schemas

These schemas define the shape of data for User-related API operations.

Schemas:
- UserCreate: Registration data (email, password, username)
- UserResponse: Public user data (never exposes password)
- UserUpdate: Profile update fields
- UserInDB: Internal schema with hashed password (for database operations)

Pydantic v2 Features Used:
- model_config: Configure model behavior
- Field(): Define constraints and metadata
- field_validator: Validate and transform field values
- EmailStr: Built-in email validation
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """
    Base schema with shared user fields.

    Contains fields common to multiple user schemas.
    """

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["john@example.com"],
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username (3-50 characters, alphanumeric and underscores)",
        examples=["johndoe", "jane_doe123"],
    )

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        """
        Validate username format.

        Rules:
        - 3-50 characters
        - Only alphanumeric and underscores
        - Must start with a letter
        """
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only "
                "letters, numbers, and underscores"
            )
        return v.lower()  # Normalize to lowercase


class UserCreate(UserBase):
    """
    Schema for user registration.

    Requires email, username, and password with strength validation.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include uppercase and number)",
        examples=["SecurePass123"],
    )

    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="User's full display name",
        examples=["John Doe"],
    )

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - At least 8 characters (enforced by min_length)
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    All fields are optional for partial updates.
    """

    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="User's full display name",
    )

    bio: str | None = Field(
        default=None,
        max_length=500,
        description="User biography",
    )

    avatar_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL to avatar image",
    )


class UserResponse(BaseModel):
    """
    Schema for user responses (what the API returns).

    SECURITY: Never includes password or sensitive internal fields.
    """

    id: int = Field(
        ...,
        description="Unique user identifier",
        examples=[1, 42],
    )

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )

    username: str = Field(
        ...,
        description="Unique username",
    )

    full_name: str | None = Field(
        default=None,
        description="User's full display name",
    )

    avatar_url: str | None = Field(
        default=None,
        description="URL to avatar image",
    )

    bio: str | None = Field(
        default=None,
        description="User biography",
    )

    is_active: bool = Field(
        ...,
        description="Whether the account is active",
    )

    is_verified: bool = Field(
        ...,
        description="Whether email has been verified",
    )

    auth_provider: str = Field(
        ...,
        description="Authentication provider (local, google, github)",
    )

    created_at: datetime = Field(
        ...,
        description="When the user registered",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "john@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "avatar_url": None,
                "bio": "Book lover and software developer",
                "is_active": True,
                "is_verified": True,
                "auth_provider": "local",
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class UserPublicResponse(BaseModel):
    """
    Schema for public user profile (visible to other users).

    Excludes email and sensitive account status fields.
    """

    id: int = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Unique username")
    full_name: str | None = Field(default=None, description="User's display name")
    avatar_url: str | None = Field(default=None, description="URL to avatar image")
    bio: str | None = Field(default=None, description="User biography")
    created_at: datetime = Field(..., description="When the user joined")

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """
    Internal schema that includes hashed password.

    SECURITY: This schema is for internal use only.
    Never return this schema in API responses.
    """

    hashed_password: str | None = Field(
        default=None,
        description="Bcrypt hashed password",
    )

    is_superuser: bool = Field(
        default=False,
        description="Whether user has admin privileges",
    )


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password for verification",
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
    )

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        """Validate new password strength."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v
