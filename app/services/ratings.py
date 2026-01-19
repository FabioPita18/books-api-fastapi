"""
Ratings Service

Service for managing book rating aggregations.

This service maintains denormalized rating fields on the Book model:
- average_rating: The mean of all review ratings
- review_count: Total number of reviews

These fields are updated whenever reviews are created, updated, or deleted.
This denormalization improves query performance for book listings by avoiding
expensive COUNT/AVG subqueries on every request.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Book
from app.models.review import Review


def recalculate_book_rating(db: Session, book_id: int) -> None:
    """
    Recalculate and update a book's rating aggregations.

    Called after any review create/update/delete operation to keep
    the denormalized fields in sync.

    Args:
        db: Database session
        book_id: ID of the book to update

    Note:
        This function commits the changes to the database.
    """
    # Calculate aggregations from reviews
    stmt = select(
        func.avg(Review.rating),
        func.count(Review.id),
    ).where(Review.book_id == book_id)

    result = db.execute(stmt).one()
    avg_rating = result[0]
    review_count = result[1]

    # Update book
    book = db.get(Book, book_id)
    if book:
        # Round to 2 decimal places if we have ratings
        book.average_rating = (
            Decimal(str(round(float(avg_rating), 2)))
            if avg_rating is not None
            else None
        )
        book.review_count = review_count
        db.commit()


def recalculate_all_book_ratings(db: Session) -> int:
    """
    Recalculate rating aggregations for all books.

    Useful for data migrations or fixing inconsistencies.

    Args:
        db: Database session

    Returns:
        Number of books updated
    """
    # Get all book IDs
    stmt = select(Book.id)
    book_ids = db.execute(stmt).scalars().all()

    for book_id in book_ids:
        recalculate_book_rating(db, book_id)

    return len(book_ids)
