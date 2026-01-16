"""
Author Pydantic Schemas

These schemas define the shape of data for Author-related API operations.

Pydantic v2 Features Used:
- model_config: New way to configure models (replaces Config class)
- Field(): Define constraints and metadata
- field_validator: Validate and transform field values
- model_validator: Validate the entire model
- ConfigDict: Type-safe configuration
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthorBase(BaseModel):
    """
    Base schema with shared author fields.

    This is the foundation for other Author schemas.
    Contains fields common to create, update, and response schemas.

    WHY a Base schema?
    - DRY principle: Define validation rules once
    - Consistency: Same rules apply everywhere
    - Inheritance: Other schemas extend this
    """

    name: str = Field(
        ...,  # ... means required (no default)
        min_length=1,
        max_length=255,
        description="Author's full name",
        examples=["George Orwell", "Jane Austen"],
    )

    bio: str | None = Field(
        default=None,
        max_length=5000,
        description="Author biography",
        examples=["English novelist and essayist, journalist and critic..."],
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """
        Validate that name is not just whitespace.

        @field_validator is a Pydantic v2 decorator that runs validation
        on specific fields. The @classmethod decorator is required.

        Args:
            v: The value being validated

        Returns:
            The validated/transformed value

        Raises:
            ValueError: If validation fails
        """
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()  # Also normalize by stripping whitespace


class AuthorCreate(AuthorBase):
    """
    Schema for creating a new author.

    Inherits all fields and validation from AuthorBase.
    In this case, no additional fields are needed for creation.

    Usage in route:
        @router.post("/authors/")
        def create_author(author: AuthorCreate):
            # author.name is validated and available
            ...
    """
    pass


class AuthorUpdate(BaseModel):
    """
    Schema for updating an existing author.

    All fields are optional because:
    - PATCH semantics: Update only provided fields
    - Users shouldn't need to resend all data

    Note: This doesn't inherit from AuthorBase because
    we want all fields to be optional.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Author's full name",
    )

    bio: str | None = Field(
        default=None,
        max_length=5000,
        description="Author biography",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str | None) -> str | None:
        """Validate name if provided."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else v


class AuthorResponse(AuthorBase):
    """
    Schema for author responses (what the API returns).

    Includes database fields like id and timestamps.
    These are read-only and set by the database.

    model_config with from_attributes=True allows:
    - Creating this schema from SQLAlchemy model instances
    - Automatic attribute access (author.name instead of author["name"])

    Usage:
        @router.get("/authors/{author_id}")
        def get_author(author_id: int) -> AuthorResponse:
            author = db.query(Author).get(author_id)
            return AuthorResponse.model_validate(author)
    """

    id: int = Field(
        ...,
        description="Unique identifier",
        examples=[1, 42],
    )

    created_at: datetime = Field(
        ...,
        description="When the author was created",
    )

    updated_at: datetime = Field(
        ...,
        description="When the author was last updated",
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        # Allow creating schema from SQLAlchemy model attributes
        from_attributes=True,
        # JSON schema examples for OpenAPI
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "George Orwell",
                "bio": "English novelist and essayist, best known for '1984' and 'Animal Farm'.",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )
