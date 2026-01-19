"""
Book Model

The central model of the Books API, representing books in the database.

This file also contains the association tables for many-to-many relationships:
- book_authors: Links books to authors
- book_genres: Links books to genres

WHY Association Tables?
=======================
In relational databases, many-to-many relationships require a "junction"
or "association" table. This table contains:
- Foreign key to the first table (books)
- Foreign key to the second table (authors or genres)
- Optionally: additional data about the relationship

SQLAlchemy can create these as Table objects (not full models) when
you don't need to store extra data on the relationship.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.author import Author
    from app.models.genre import Genre
    from app.models.review import Review


# =============================================================================
# Association Tables
# =============================================================================
# These are "pure" association tables - they only store the relationship,
# no additional data. They're defined as Table objects, not classes.
#
# If you needed extra data (e.g., author's role in the book), you'd create
# a full model class instead.

book_authors = Table(
    "book_authors",
    Base.metadata,
    Column(
        "book_id",
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "author_id",
        Integer,
        ForeignKey("authors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Adding a comment for database documentation
    comment="Association table linking books to their authors",
)

book_genres = Table(
    "book_genres",
    Base.metadata,
    Column(
        "book_id",
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    comment="Association table linking books to their genres",
)


class Book(Base):
    """
    Book model representing books in the library.

    Table: books

    Fields:
    - title: Book title (required)
    - isbn: International Standard Book Number (unique)
    - description: Book summary/description
    - publication_date: When the book was published
    - page_count: Number of pages
    - price: Book price with 2 decimal precision

    Relationships:
    - authors: Many-to-Many (a book can have multiple authors)
    - genres: Many-to-Many (a book can belong to multiple genres)

    Indexes:
    - Primary key on id (automatic)
    - isbn: Unique index for lookups
    - title: Index for searching
    - publication_date: Index for sorting/filtering

    Example:
        book = Book(
            title="1984",
            isbn="978-0451524935",
            description="A dystopian novel...",
            publication_date=date(1949, 6, 8),
            page_count=328,
            price=Decimal("12.99"),
        )
    """

    __tablename__ = "books"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------------------------
    # Basic Fields
    # -------------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(500),
        index=True,
        nullable=False,
        comment="Book title"
    )

    # ISBN is the international standard identifier for books
    # It should be unique - no two books have the same ISBN
    # Optional because older books might not have one
    isbn: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=True,
        comment="International Standard Book Number"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Book description or summary"
    )

    # Date (not DateTime) because we only care about the day, not time
    publication_date: Mapped[date | None] = mapped_column(
        Date,
        index=True,
        nullable=True,
        comment="Date of publication"
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of pages in the book"
    )

    # Numeric(10, 2) = up to 10 digits, 2 after decimal point
    # This is standard for currency: 99999999.99 maximum
    # Using Decimal (not float) for precise money calculations
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Book price in USD"
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
    # Many-to-many relationship with Author
    # back_populates creates a bidirectional relationship:
    #   book.authors  -> list of authors
    #   author.books  -> list of books
    authors: Mapped[list["Author"]] = relationship(
        "Author",
        secondary=book_authors,
        back_populates="books",
    )

    # Many-to-many relationship with Genre
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=book_genres,
        back_populates="books",
    )

    # One-to-many relationship with Reviews
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Book(id={self.id}, title='{self.title}', isbn='{self.isbn}')"
