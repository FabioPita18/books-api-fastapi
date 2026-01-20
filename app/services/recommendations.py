"""
Recommendations Service

Provides book recommendations using multiple strategies:
1. Content-based: Books similar by genre/author
2. Collaborative filtering: Users who liked X also liked Y
3. Trending: Popular books by recent activity

Features:
- Hybrid recommendations combining multiple signals
- Redis caching for performance
- Graceful handling of cold-start problems
"""

import logging
import math
from collections import defaultdict
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.book import Book, book_authors, book_genres
from app.models.review import Review
from app.services.cache import cache_delete_pattern, cache_get, cache_set, make_cache_key

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Content-Based Recommendations
# =============================================================================


def get_similar_books(
    db: Session,
    book_id: int,
    limit: int = 10,
    exclude_book_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Find books similar to a given book based on genres and authors.

    Algorithm:
    1. Get the book's genres and authors
    2. Find books sharing genres (weighted by overlap count)
    3. Find books by same authors (higher weight)
    4. Score and rank by similarity
    5. Exclude already-read books if provided

    Args:
        db: Database session
        book_id: ID of the book to find similar books for
        limit: Maximum number of recommendations
        exclude_book_ids: Book IDs to exclude (e.g., already read)

    Returns:
        List of similar books with similarity scores and reasons
    """
    # Check cache first
    cache_key = make_cache_key("similar_books", book_id, limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        # Filter out excluded books from cached results
        if exclude_book_ids:
            cached = [b for b in cached if b["book"]["id"] not in exclude_book_ids]
        return cached[:limit]

    # Get the source book with its relationships
    source_book = db.execute(
        select(Book)
        .options(selectinload(Book.genres), selectinload(Book.authors))
        .where(Book.id == book_id)
    ).scalar_one_or_none()

    if source_book is None:
        return []

    source_genre_ids = {g.id for g in source_book.genres}
    source_author_ids = {a.id for a in source_book.authors}

    if not source_genre_ids and not source_author_ids:
        # No genres or authors to match on
        return []

    # Build similarity scores
    # Key: book_id, Value: {"score": float, "reasons": list}
    similarity_scores: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"score": 0.0, "reasons": []}
    )

    # Score books by genre overlap
    if source_genre_ids:
        genre_matches = db.execute(
            select(book_genres.c.book_id, func.count().label("match_count"))
            .where(book_genres.c.genre_id.in_(source_genre_ids))
            .where(book_genres.c.book_id != book_id)
            .group_by(book_genres.c.book_id)
        ).all()

        for match_book_id, match_count in genre_matches:
            # Jaccard-like similarity: matches / total genres
            genre_similarity = match_count / len(source_genre_ids)
            similarity_scores[match_book_id]["score"] += genre_similarity * 0.6
            if match_count > 0:
                similarity_scores[match_book_id]["reasons"].append(
                    f"Shares {match_count} genre(s)"
                )

    # Score books by author overlap (higher weight)
    if source_author_ids:
        author_matches = db.execute(
            select(book_authors.c.book_id, func.count().label("match_count"))
            .where(book_authors.c.author_id.in_(source_author_ids))
            .where(book_authors.c.book_id != book_id)
            .group_by(book_authors.c.book_id)
        ).all()

        for match_book_id, match_count in author_matches:
            author_similarity = match_count / len(source_author_ids)
            similarity_scores[match_book_id]["score"] += author_similarity * 0.8
            if match_count > 0:
                similarity_scores[match_book_id]["reasons"].append(
                    f"Same author(s)"
                )

    # Boost by rating (higher rated books are better recommendations)
    book_ids_to_score = list(similarity_scores.keys())
    if book_ids_to_score:
        rated_books = db.execute(
            select(Book.id, Book.average_rating)
            .where(Book.id.in_(book_ids_to_score))
            .where(Book.average_rating.isnot(None))
        ).all()

        for rated_book_id, avg_rating in rated_books:
            if avg_rating:
                # Normalize rating to 0-1 and add small boost
                rating_boost = (float(avg_rating) / 5.0) * 0.2
                similarity_scores[rated_book_id]["score"] += rating_boost

    # Sort by score and get top results
    sorted_books = sorted(
        similarity_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    # Fetch book details for top candidates
    top_book_ids = [bid for bid, _ in sorted_books[:limit * 2]]
    if not top_book_ids:
        return []

    books_data = db.execute(
        select(Book)
        .options(selectinload(Book.genres), selectinload(Book.authors))
        .where(Book.id.in_(top_book_ids))
    ).scalars().all()

    books_by_id = {book.id: book for book in books_data}

    # Build response
    results = []
    for bid, score_data in sorted_books:
        if bid not in books_by_id:
            continue

        book = books_by_id[bid]
        results.append({
            "book": {
                "id": book.id,
                "title": book.title,
                "description": book.description,
                "isbn": book.isbn,
                "authors": [a.name for a in book.authors],
                "genres": [g.name for g in book.genres],
                "publication_year": book.published_date.year if book.published_date else None,
                "price": float(book.price) if book.price else None,
                "average_rating": float(book.average_rating) if book.average_rating else None,
                "review_count": book.review_count or 0,
            },
            "similarity_score": round(score_data["score"], 3),
            "reasons": score_data["reasons"],
        })

        if len(results) >= limit * 2:
            break

    # Cache results (without exclusions applied)
    cache_set(cache_key, results, ttl=settings.recommendation_cache_ttl)

    # Apply exclusions
    if exclude_book_ids:
        results = [r for r in results if r["book"]["id"] not in exclude_book_ids]

    return results[:limit]


# =============================================================================
# Collaborative Filtering
# =============================================================================


def get_recommendations_for_user(
    db: Session,
    user_id: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get personalized recommendations for a user using collaborative filtering.

    Algorithm:
    1. Get books the user has rated highly (4+)
    2. Find similar users (who also rated those books highly)
    3. Get books those similar users liked that this user hasn't read
    4. Score by how many similar users liked each book

    Args:
        db: Database session
        user_id: ID of the user to get recommendations for
        limit: Maximum number of recommendations

    Returns:
        List of recommended books with scores and reasons
    """
    # Check cache
    cache_key = make_cache_key("user_recommendations", user_id, limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # Get books the user has rated highly (4+)
    user_high_ratings = db.execute(
        select(Review.book_id, Review.rating)
        .where(Review.user_id == user_id)
        .where(Review.rating >= 4)
    ).all()

    if not user_high_ratings:
        # Cold start: user has no high ratings, return trending books
        logger.debug(f"User {user_id} has no high ratings, falling back to trending")
        return get_trending_books(db, limit=limit, exclude_user_id=user_id)

    user_liked_book_ids = {r.book_id for r in user_high_ratings}

    # Get ALL books the user has reviewed (to exclude from recommendations)
    all_user_reviews = db.execute(
        select(Review.book_id)
        .where(Review.user_id == user_id)
    ).scalars().all()
    user_read_book_ids = set(all_user_reviews)

    # Find similar users: users who also rated the same books highly
    similar_users = db.execute(
        select(Review.user_id, func.count().label("overlap_count"))
        .where(Review.book_id.in_(user_liked_book_ids))
        .where(Review.rating >= 4)
        .where(Review.user_id != user_id)
        .group_by(Review.user_id)
        .having(func.count() >= 1)  # At least 1 book in common
        .order_by(desc("overlap_count"))
        .limit(50)  # Top 50 similar users
    ).all()

    if not similar_users:
        # No similar users found, fall back to content-based
        logger.debug(f"No similar users for {user_id}, falling back to content-based")
        recommendations = []
        for book_id in list(user_liked_book_ids)[:3]:
            similar = get_similar_books(
                db, book_id, limit=5, exclude_book_ids=list(user_read_book_ids)
            )
            recommendations.extend(similar)

        # Deduplicate and sort
        seen = set()
        unique_recs = []
        for rec in sorted(recommendations, key=lambda x: x["similarity_score"], reverse=True):
            if rec["book"]["id"] not in seen:
                seen.add(rec["book"]["id"])
                unique_recs.append(rec)
                if len(unique_recs) >= limit:
                    break

        cache_set(cache_key, unique_recs, ttl=settings.recommendation_cache_ttl)
        return unique_recs

    similar_user_ids = [u.user_id for u in similar_users]
    similar_user_weights = {u.user_id: u.overlap_count for u in similar_users}

    # Get books that similar users rated highly (that current user hasn't read)
    candidate_books = db.execute(
        select(Review.book_id, Review.user_id, Review.rating)
        .where(Review.user_id.in_(similar_user_ids))
        .where(Review.rating >= 4)
        .where(~Review.book_id.in_(user_read_book_ids))
    ).all()

    # Score candidates by weighted votes from similar users
    book_scores: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"score": 0.0, "voter_count": 0, "avg_rating": 0.0}
    )

    for book_id, reviewer_id, rating in candidate_books:
        weight = similar_user_weights.get(reviewer_id, 1)
        book_scores[book_id]["score"] += weight * (rating / 5.0)
        book_scores[book_id]["voter_count"] += 1
        book_scores[book_id]["avg_rating"] += rating

    # Normalize scores
    for book_id in book_scores:
        count = book_scores[book_id]["voter_count"]
        if count > 0:
            book_scores[book_id]["avg_rating"] /= count
            # Boost score based on number of similar users who liked it
            book_scores[book_id]["score"] *= math.log(count + 1)

    # Sort and get top candidates
    sorted_candidates = sorted(
        book_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )[:limit * 2]

    top_book_ids = [bid for bid, _ in sorted_candidates]
    if not top_book_ids:
        cache_set(cache_key, [], ttl=settings.recommendation_cache_ttl)
        return []

    # Fetch book details
    books_data = db.execute(
        select(Book)
        .options(selectinload(Book.genres), selectinload(Book.authors))
        .where(Book.id.in_(top_book_ids))
    ).scalars().all()

    books_by_id = {book.id: book for book in books_data}

    # Build response
    results = []
    for bid, score_data in sorted_candidates:
        if bid not in books_by_id:
            continue

        book = books_by_id[bid]
        voter_count = score_data["voter_count"]
        results.append({
            "book": {
                "id": book.id,
                "title": book.title,
                "description": book.description,
                "isbn": book.isbn,
                "authors": [a.name for a in book.authors],
                "genres": [g.name for g in book.genres],
                "publication_year": book.published_date.year if book.published_date else None,
                "price": float(book.price) if book.price else None,
                "average_rating": float(book.average_rating) if book.average_rating else None,
                "review_count": book.review_count or 0,
            },
            "recommendation_score": round(score_data["score"], 3),
            "reasons": [f"Liked by {voter_count} reader(s) with similar taste"],
        })

        if len(results) >= limit:
            break

    cache_set(cache_key, results, ttl=settings.recommendation_cache_ttl)
    return results


# =============================================================================
# Trending & New Releases
# =============================================================================


def get_trending_books(
    db: Session,
    limit: int = 10,
    exclude_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Get trending/popular books based on recent reviews and ratings.

    Criteria:
    - High average rating (weighted)
    - Many recent reviews (activity indicator)
    - Balances quality with popularity

    Args:
        db: Database session
        limit: Maximum number of books
        exclude_user_id: User ID to exclude books they've already read

    Returns:
        List of trending books
    """
    cache_key = make_cache_key("trending_books", limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        if exclude_user_id:
            # Get user's read books
            user_books = set(db.execute(
                select(Review.book_id).where(Review.user_id == exclude_user_id)
            ).scalars().all())
            cached = [b for b in cached if b["book"]["id"] not in user_books]
        return cached[:limit]

    # Get books with good ratings and multiple reviews
    stmt = (
        select(Book)
        .options(selectinload(Book.genres), selectinload(Book.authors))
        .where(Book.average_rating.isnot(None))
        .where(Book.review_count >= 1)
        .order_by(
            # Score: rating * log(review_count + 1)
            (Book.average_rating * func.log(Book.review_count + 1)).desc()
        )
        .limit(limit * 2)
    )

    books = db.execute(stmt).scalars().all()

    results = []
    for book in books:
        results.append({
            "book": {
                "id": book.id,
                "title": book.title,
                "description": book.description,
                "isbn": book.isbn,
                "authors": [a.name for a in book.authors],
                "genres": [g.name for g in book.genres],
                "publication_year": book.published_date.year if book.published_date else None,
                "price": float(book.price) if book.price else None,
                "average_rating": float(book.average_rating) if book.average_rating else None,
                "review_count": book.review_count or 0,
            },
            "trending_score": round(
                float(book.average_rating or 0) * math.log(book.review_count + 1), 3
            ),
            "reasons": [f"Rated {book.average_rating}/5 by {book.review_count} reader(s)"],
        })

    # Cache without user exclusions
    cache_set(cache_key, results, ttl=900)  # 15 min TTL for trending

    if exclude_user_id:
        user_books = set(db.execute(
            select(Review.book_id).where(Review.user_id == exclude_user_id)
        ).scalars().all())
        results = [r for r in results if r["book"]["id"] not in user_books]

    return results[:limit]


def get_new_releases(
    db: Session,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get recently added books.

    Args:
        db: Database session
        limit: Maximum number of books

    Returns:
        List of newly added books
    """
    cache_key = make_cache_key("new_releases", limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    stmt = (
        select(Book)
        .options(selectinload(Book.genres), selectinload(Book.authors))
        .order_by(Book.created_at.desc())
        .limit(limit)
    )

    books = db.execute(stmt).scalars().all()

    results = []
    for book in books:
        results.append({
            "book": {
                "id": book.id,
                "title": book.title,
                "description": book.description,
                "isbn": book.isbn,
                "authors": [a.name for a in book.authors],
                "genres": [g.name for g in book.genres],
                "publication_year": book.published_date.year if book.published_date else None,
                "price": float(book.price) if book.price else None,
                "average_rating": float(book.average_rating) if book.average_rating else None,
                "review_count": book.review_count or 0,
            },
            "added_at": book.created_at.isoformat(),
            "reasons": ["Recently added to catalog"],
        })

    cache_set(cache_key, results, ttl=900)  # 15 min TTL
    return results


# =============================================================================
# Cache Invalidation
# =============================================================================


def invalidate_recommendation_cache(
    user_id: int | None = None,
    book_id: int | None = None,
) -> None:
    """
    Invalidate recommendation caches when data changes.

    Called when:
    - User adds/updates a review (invalidate their recommendations)
    - Book is updated (invalidate similar books cache)

    Args:
        user_id: User whose recommendations should be invalidated
        book_id: Book whose similar books should be invalidated
    """
    if user_id:
        cache_delete_pattern(f"user_recommendations:{user_id}:*")

    if book_id:
        cache_delete_pattern(f"similar_books:{book_id}:*")

    # Trending is short-lived, no need to invalidate
