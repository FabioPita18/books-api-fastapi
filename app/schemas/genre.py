"""
Genre Pydantic Schemas

Schemas for genre-related API operations.
Follows the same pattern as Author schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenreBase(BaseModel):
    """Base schema with shared genre fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Genre name",
        examples=["Science Fiction", "Mystery", "Romance"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Description of the genre",
        examples=["Fiction dealing with futuristic science and technology"],
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate and normalize genre name."""
        if not v.strip():
            raise ValueError("Genre name cannot be empty or whitespace")
        return v.strip()


class GenreCreate(GenreBase):
    """Schema for creating a new genre."""
    pass


class GenreUpdate(BaseModel):
    """Schema for updating an existing genre. All fields optional."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Genre name",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Description of the genre",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate name if provided."""
        if v is not None and not v.strip():
            raise ValueError("Genre name cannot be empty or whitespace")
        return v.strip() if v else v


class GenreResponse(GenreBase):
    """Schema for genre responses."""

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When the genre was created")
    updated_at: datetime = Field(..., description="When the genre was last updated")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Science Fiction",
                "description": "Fiction based on futuristic science and technology",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )
