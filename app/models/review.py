"""
Review Model

Represents a user's review of a book, including rating and text content.

Business Rules:
- One review per user per book (unique constraint)
- Rating must be 1-5
- Users can only edit/delete their own reviews
- Superusers can delete any review (moderation)
"""

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    """
    Review model for book reviews.

    Attributes:
        id: Primary key
        book_id: Foreign key to books table
        user_id: Foreign key to users table
        rating: 1-5 star rating
        title: Optional review title
        content: Review text content
        helpful_count: Number of "helpful" votes
        reported: Flag for moderation
        created_at: When the review was created
        updated_at: When the review was last updated
    """

    __tablename__ = "reviews"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    book_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Review content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Rating from 1-5 stars",
    )
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Optional review title",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Review text content",
    )

    # Moderation fields
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of helpful votes",
    )
    reported: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Flag for moderation review",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    # Constraints
    __table_args__ = (
        # One review per user per book
        UniqueConstraint("book_id", "user_id", name="uq_review_book_user"),
        # Rating must be 1-5
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating})>"
