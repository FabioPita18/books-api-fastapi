"""
Author Model

Represents an author in the books database.

SQLAlchemy 2.0 Features Used:
- mapped_column(): New way to define columns with full type support
- Mapped[]: Type hint wrapper for SQLAlchemy columns
- relationship(): Define relationships between models
- back_populates: Two-way relationship binding
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# TYPE_CHECKING is True only during type checking (mypy, IDE)
# This prevents circular imports at runtime while enabling type hints
if TYPE_CHECKING:
    from app.models.book import Book


class Author(Base):
    """
    Author model representing writers in the system.

    Table: authors

    Relationships:
    - books: Many-to-Many relationship through book_authors table

    Indexes:
    - Primary key on id (automatic)
    - name: For searching authors by name

    Example:
        author = Author(
            name="George Orwell",
            bio="English novelist and essayist...",
        )
        db.add(author)
        db.commit()
    """

    __tablename__ = "authors"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    # mapped_column() is SQLAlchemy 2.0's way to define columns
    # Mapped[int] tells the type checker this is an integer
    # primary_key=True creates an auto-incrementing primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------------------------
    # Basic Fields
    # -------------------------------------------------------------------------
    # String(255) limits the column to 255 characters
    # index=True creates a database index for faster searches
    # nullable=False means this field is required (NOT NULL in SQL)
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        comment="Author's full name"
    )

    # Text is for unlimited length strings (like biography)
    # Optional[str] + nullable=True means this field can be None/NULL
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Author biography"
    )

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    # These are automatically set by the database
    # server_default=func.now() uses the database's NOW() function
    # This is better than Python's datetime.now() because:
    # 1. Consistent timezone handling
    # 2. Works even when inserting directly via SQL
    # 3. Database is the source of truth for time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the author record was created"
    )

    # onupdate=func.now() automatically updates this field on UPDATE
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When the author record was last updated"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    # This defines the Python-side relationship to Book
    #
    # Parameters:
    # - "Book": The related model (string to avoid circular imports)
    # - secondary: The association table for many-to-many
    # - back_populates: The attribute name on Book that points back here
    #
    # With this relationship, you can do:
    #   author.books  # Get all books by this author
    #   author.books.append(book)  # Add a book to this author
    books: Mapped[list["Book"]] = relationship(
        "Book",
        secondary="book_authors",
        back_populates="authors",
    )

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        """
        Developer-friendly string representation.

        Used when printing the object or in debugger:
            >>> author = Author(name="George Orwell")
            >>> print(author)
            Author(id=1, name='George Orwell')
        """
        return f"Author(id={self.id}, name='{self.name}')"
