"""
Genre Model

Represents a book genre/category in the database.

Genres allow books to be categorized for browsing and filtering.
A book can belong to multiple genres (e.g., "Science Fiction" and "Dystopian").
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.book import Book


class Genre(Base):
    """
    Genre model representing book categories.

    Table: genres

    Relationships:
    - books: Many-to-Many relationship through book_genres table

    Indexes:
    - Primary key on id (automatic)
    - name: Unique index for preventing duplicate genres

    Example:
        genre = Genre(
            name="Science Fiction",
            description="Fiction dealing with futuristic concepts...",
        )
    """

    __tablename__ = "genres"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------------------------
    # Basic Fields
    # -------------------------------------------------------------------------
    # unique=True prevents duplicate genre names
    # This creates a UNIQUE constraint in the database
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Genre name (e.g., 'Science Fiction', 'Mystery')"
    )

    # Optional description of the genre
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what this genre encompasses"
    )

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    # Many-to-many relationship with Book through book_genres table
    books: Mapped[List["Book"]] = relationship(
        "Book",
        secondary="book_genres",
        back_populates="genres",
    )

    def __repr__(self) -> str:
        return f"Genre(id={self.id}, name='{self.name}')"
