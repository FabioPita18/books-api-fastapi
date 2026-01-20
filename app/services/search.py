"""
Search Service

Provides advanced search functionality using Elasticsearch with
PostgreSQL fallback when Elasticsearch is unavailable.

Features:
- Full-text search across title, description, authors
- Fuzzy matching for typo tolerance
- Faceted search (filter by genre, year, rating)
- Relevance scoring
- Graceful degradation to PostgreSQL
"""

import logging
import math
from typing import Any

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Author, Book, Genre
from app.services.elasticsearch import is_elasticsearch_healthy, search_books as es_search_books

logger = logging.getLogger(__name__)


async def search_books_advanced(
    db: Session,
    query: str | None = None,
    genres: list[str] | None = None,
    genre_ids: list[int] | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    min_rating: float | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    size: int = 20,
    fuzzy: bool = True,
) -> dict[str, Any]:
    """
    Search books using Elasticsearch with PostgreSQL fallback.

    Args:
        db: Database session (for fallback)
        query: Full-text search query
        genres: List of genre names to filter by
        genre_ids: List of genre IDs to filter by
        min_year: Minimum publication year
        max_year: Maximum publication year
        min_rating: Minimum average rating
        min_price: Minimum price
        max_price: Maximum price
        page: Page number (1-indexed)
        size: Results per page
        fuzzy: Enable fuzzy matching

    Returns:
        Dictionary with items, total, facets, and metadata
    """
    # Check if Elasticsearch is available
    es_healthy = await is_elasticsearch_healthy()

    if es_healthy:
        logger.debug("Using Elasticsearch for search")
        result = await es_search_books(
            query=query,
            genres=genres,
            min_year=min_year,
            max_year=max_year,
            min_rating=min_rating,
            min_price=min_price,
            max_price=max_price,
            page=page,
            size=size,
            fuzzy=fuzzy,
        )

        if not result.get("fallback", False):
            return result

    # Fallback to PostgreSQL search
    logger.debug("Falling back to PostgreSQL for search")
    return _search_books_postgres(
        db=db,
        query=query,
        genres=genres,
        genre_ids=genre_ids,
        min_year=min_year,
        max_year=max_year,
        min_rating=min_rating,
        min_price=min_price,
        max_price=max_price,
        page=page,
        size=size,
    )


def _search_books_postgres(
    db: Session,
    query: str | None = None,
    genres: list[str] | None = None,
    genre_ids: list[int] | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    min_rating: float | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """
    Search books using PostgreSQL (fallback when ES is unavailable).

    This provides basic search functionality without the advanced
    features of Elasticsearch (fuzzy matching, relevance scoring, etc.)
    """
    # Build base query
    stmt = select(Book)
    filter_conditions = []

    # Full-text search (basic LIKE matching)
    if query:
        search_term = f"%{query.lower()}%"
        # Search in title
        title_match = func.lower(Book.title).like(search_term)
        # Search in description
        desc_match = func.lower(Book.description).like(search_term)
        # Search in author names (subquery)
        author_book_ids = (
            select(Book.id)
            .join(Book.authors)
            .where(func.lower(Author.name).like(search_term))
        )
        filter_conditions.append(
            or_(title_match, desc_match, Book.id.in_(author_book_ids))
        )

    # Filter by genre names
    if genres:
        genre_book_ids = (
            select(Book.id)
            .join(Book.genres)
            .where(Genre.name.in_(genres))
        )
        filter_conditions.append(Book.id.in_(genre_book_ids))

    # Filter by genre IDs
    if genre_ids:
        genre_book_ids = (
            select(Book.id)
            .join(Book.genres)
            .where(Genre.id.in_(genre_ids))
        )
        filter_conditions.append(Book.id.in_(genre_book_ids))

    # Filter by publication year range
    if min_year is not None:
        filter_conditions.append(
            extract("year", Book.published_date) >= min_year
        )
    if max_year is not None:
        filter_conditions.append(
            extract("year", Book.published_date) <= max_year
        )

    # Filter by rating
    if min_rating is not None:
        filter_conditions.append(Book.average_rating >= min_rating)

    # Filter by price range
    if min_price is not None:
        filter_conditions.append(Book.price >= min_price)
    if max_price is not None:
        filter_conditions.append(Book.price <= max_price)

    # Apply all filters
    if filter_conditions:
        stmt = stmt.where(*filter_conditions)

    # Count total matching books
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Calculate pagination
    pages = math.ceil(total / size) if total > 0 else 0
    offset = (page - 1) * size

    # Fetch books with relationships
    stmt = (
        stmt
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .offset(offset)
        .limit(size)
        .order_by(Book.average_rating.desc().nullslast(), Book.created_at.desc())
    )
    books = db.execute(stmt).scalars().all()

    # Build response items
    items = []
    for book in books:
        items.append({
            "id": book.id,
            "title": book.title,
            "description": book.description,
            "isbn": book.isbn,
            "authors": [author.name for author in book.authors] if book.authors else [],
            "genres": [genre.name for genre in book.genres] if book.genres else [],
            "publication_year": book.published_date.year if book.published_date else None,
            "price": float(book.price) if book.price else None,
            "average_rating": float(book.average_rating) if book.average_rating else None,
            "review_count": book.review_count or 0,
            "relevance_score": None,  # No relevance score in PostgreSQL
        })

    # Build facets (aggregations)
    facets = _build_postgres_facets(db, filter_conditions)

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "facets": facets,
        "fallback": True,  # Indicates PostgreSQL was used
    }


def _build_postgres_facets(db: Session, base_filters: list) -> dict[str, list]:
    """
    Build faceted search aggregations using PostgreSQL.

    This is less efficient than Elasticsearch aggregations but provides
    similar functionality for the fallback case.
    """
    facets = {
        "genres": [],
        "years": [],
        "ratings": [],
    }

    try:
        # Genre facet
        genre_stmt = (
            select(Genre.name, func.count(Book.id))
            .join(Book.genres)
            .group_by(Genre.name)
            .order_by(func.count(Book.id).desc())
            .limit(20)
        )
        genre_results = db.execute(genre_stmt).all()
        facets["genres"] = [
            {"name": name, "count": count}
            for name, count in genre_results
        ]

        # Year facet
        year_stmt = (
            select(
                extract("year", Book.published_date).label("year"),
                func.count(Book.id)
            )
            .where(Book.published_date.isnot(None))
            .group_by("year")
            .order_by(extract("year", Book.published_date).desc())
            .limit(20)
        )
        year_results = db.execute(year_stmt).all()
        facets["years"] = [
            {"year": int(year), "count": count}
            for year, count in year_results
            if year is not None
        ]

        # Rating ranges facet
        rating_ranges = [
            ("4+", 4.0, None),
            ("3-4", 3.0, 4.0),
            ("2-3", 2.0, 3.0),
            ("1-2", 1.0, 2.0),
        ]
        for range_key, min_r, max_r in rating_ranges:
            conditions = [Book.average_rating >= min_r]
            if max_r is not None:
                conditions.append(Book.average_rating < max_r)

            count_stmt = select(func.count()).select_from(
                select(Book.id).where(*conditions).subquery()
            )
            count = db.execute(count_stmt).scalar() or 0
            facets["ratings"].append({"range": range_key, "count": count})

    except Exception as e:
        logger.warning(f"Failed to build facets: {e}")

    return facets
