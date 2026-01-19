"""
Book Pydantic Schemas

The most complex schemas, handling:
- Nested relationships (authors, genres)
- ISBN validation
- Price validation
- Pagination for list responses
"""

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.author import AuthorResponse
from app.schemas.genre import GenreResponse


class BookBase(BaseModel):
    """
    Base schema with shared book fields.

    Contains validation for:
    - ISBN format (ISBN-10 or ISBN-13)
    - Price (must be positive)
    - Page count (must be positive)
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Book title",
        examples=["1984", "Pride and Prejudice"],
    )

    isbn: str | None = Field(
        default=None,
        max_length=20,
        description="ISBN-10 or ISBN-13",
        examples=["978-0451524935", "0-06-112008-1"],
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Book description or summary",
        examples=["A dystopian novel set in a totalitarian society..."],
    )

    publication_date: date | None = Field(
        default=None,
        description="Date of publication",
        examples=["1949-06-08"],
    )

    page_count: int | None = Field(
        default=None,
        gt=0,  # gt = greater than
        le=50000,  # le = less than or equal (reasonable max)
        description="Number of pages",
        examples=[328, 256],
    )

    price: Decimal | None = Field(
        default=None,
        ge=0,  # ge = greater than or equal (free books allowed)
        le=Decimal("9999.99"),
        description="Book price in USD",
        examples=["12.99", "24.95"],
    )

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        """
        Validate ISBN format.

        Accepts:
        - ISBN-10: 10 digits, last can be X
        - ISBN-13: 13 digits

        ISBNs can include hyphens, which we strip for storage.
        """
        if v is None:
            return v

        # Remove hyphens and spaces for validation
        cleaned = re.sub(r"[-\s]", "", v)

        # ISBN-10: 9 digits + (digit or X)
        # ISBN-13: 13 digits
        if len(cleaned) == 10:
            if not re.match(r"^\d{9}[\dX]$", cleaned):
                raise ValueError(
                    "Invalid ISBN-10 format. Must be 10 characters: "
                    "9 digits followed by a digit or 'X'"
                )
        elif len(cleaned) == 13:
            if not cleaned.isdigit():
                raise ValueError(
                    "Invalid ISBN-13 format. Must be exactly 13 digits"
                )
        else:
            raise ValueError(
                "ISBN must be either 10 or 13 characters "
                "(excluding hyphens)"
            )

        return cleaned  # Store without hyphens for consistency

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Validate and normalize title."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()


class BookCreate(BookBase):
    """
    Schema for creating a new book.

    Includes optional lists of author and genre IDs to associate
    with the book upon creation.

    Example request body:
    {
        "title": "1984",
        "isbn": "978-0451524935",
        "author_ids": [1, 2],
        "genre_ids": [1, 3]
    }
    """

    author_ids: list[int] | None = Field(
        default=None,
        description="List of author IDs to associate with this book",
        examples=[[1, 2]],
    )

    genre_ids: list[int] | None = Field(
        default=None,
        description="List of genre IDs to associate with this book",
        examples=[[1, 3]],
    )


class BookUpdate(BaseModel):
    """
    Schema for updating an existing book.

    All fields are optional for PATCH-style updates.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Book title",
    )

    isbn: str | None = Field(
        default=None,
        max_length=20,
        description="ISBN-10 or ISBN-13",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Book description",
    )

    publication_date: date | None = Field(
        default=None,
        description="Date of publication",
    )

    page_count: int | None = Field(
        default=None,
        gt=0,
        le=50000,
        description="Number of pages",
    )

    price: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("9999.99"),
        description="Book price in USD",
    )

    author_ids: list[int] | None = Field(
        default=None,
        description="List of author IDs (replaces existing)",
    )

    genre_ids: list[int] | None = Field(
        default=None,
        description="List of genre IDs (replaces existing)",
    )

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        """Validate ISBN if provided."""
        if v is None:
            return v

        cleaned = re.sub(r"[-\s]", "", v)

        if len(cleaned) == 10:
            if not re.match(r"^\d{9}[\dX]$", cleaned):
                raise ValueError("Invalid ISBN-10 format")
        elif len(cleaned) == 13:
            if not cleaned.isdigit():
                raise ValueError("Invalid ISBN-13 format")
        else:
            raise ValueError("ISBN must be 10 or 13 characters")

        return cleaned

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str | None) -> str | None:
        """Validate title if provided."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v else v


class BookResponse(BookBase):
    """
    Schema for book responses.

    Includes:
    - Database fields (id, timestamps)
    - Nested author and genre data

    The nested data uses AuthorResponse and GenreResponse schemas,
    so clients get full information without additional API calls.
    """

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When the book was created")
    updated_at: datetime = Field(..., description="When the book was last updated")

    # Rating aggregation fields
    average_rating: Decimal | None = Field(
        default=None,
        description="Average review rating (1.00-5.00), null if no reviews",
    )
    review_count: int = Field(
        default=0,
        description="Number of reviews for this book",
    )

    # Nested relationships - returns full objects, not just IDs
    authors: list[AuthorResponse] = Field(
        default=[],
        description="List of authors",
    )

    genres: list[GenreResponse] = Field(
        default=[],
        description="List of genres",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "1984",
                "isbn": "9780451524935",
                "description": "A dystopian novel about totalitarianism",
                "publication_date": "1949-06-08",
                "page_count": 328,
                "price": "12.99",
                "average_rating": "4.25",
                "review_count": 42,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "authors": [
                    {
                        "id": 1,
                        "name": "George Orwell",
                        "bio": "English novelist and essayist",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "genres": [
                    {
                        "id": 1,
                        "name": "Science Fiction",
                        "description": "Futuristic fiction",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
            }
        },
    )


class BookListResponse(BaseModel):
    """
    Schema for paginated book list responses.

    WHY Pagination?
    ===============
    - Performance: Don't load entire database into memory
    - User Experience: Faster responses
    - API Best Practice: Predictable response sizes

    This schema includes metadata about the pagination:
    - total: Total number of books matching the query
    - page: Current page number
    - per_page: Number of items per page
    - pages: Total number of pages
    """

    items: list[BookResponse] = Field(
        ...,
        description="List of books for this page",
    )

    total: int = Field(
        ...,
        ge=0,
        description="Total number of books",
    )

    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )

    per_page: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page",
    )

    pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "per_page": 10,
                "pages": 10,
            }
        },
    )
