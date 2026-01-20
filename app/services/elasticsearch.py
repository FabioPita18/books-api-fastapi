"""
Elasticsearch Service

Provides async Elasticsearch client and indexing operations for books.

Features:
- Async client with connection pooling
- Book indexing with English analyzer
- Full-text search with fuzzy matching
- Graceful fallback when Elasticsearch is unavailable
"""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# Elasticsearch Client
# =============================================================================

# Global client instance (initialized in app lifespan)
_es_client: AsyncElasticsearch | None = None


def get_index_name(index_type: str = "books") -> str:
    """Get the full index name with prefix."""
    return f"{settings.elasticsearch_index_prefix}{index_type}"


async def get_es_client() -> AsyncElasticsearch | None:
    """
    Get the Elasticsearch client instance.

    Returns None if Elasticsearch is disabled or not connected.
    """
    global _es_client
    return _es_client


async def init_elasticsearch() -> bool:
    """
    Initialize Elasticsearch client and create indices.

    Called during application startup.

    Returns:
        True if connection successful, False otherwise
    """
    global _es_client

    if not settings.elasticsearch_enabled:
        logger.info("Elasticsearch is disabled, skipping initialization")
        return False

    try:
        _es_client = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=settings.elasticsearch_timeout,
            retry_on_timeout=True,
            max_retries=3,
        )

        # Test connection
        info = await _es_client.info()
        logger.info(
            f"Connected to Elasticsearch {info['version']['number']} "
            f"at {settings.elasticsearch_url}"
        )

        # Create indices if they don't exist
        await create_book_index()

        return True

    except Exception as e:
        logger.warning(f"Failed to connect to Elasticsearch: {e}")
        logger.warning("Search will fall back to PostgreSQL")
        _es_client = None
        return False


async def close_elasticsearch() -> None:
    """
    Close Elasticsearch client connection.

    Called during application shutdown.
    """
    global _es_client

    if _es_client:
        await _es_client.close()
        _es_client = None
        logger.info("Elasticsearch connection closed")


async def is_elasticsearch_healthy() -> bool:
    """
    Check if Elasticsearch is healthy and available.

    Returns:
        True if healthy, False otherwise
    """
    if not _es_client:
        return False

    try:
        health = await _es_client.cluster.health()
        return health["status"] in ("green", "yellow")
    except Exception:
        return False


# =============================================================================
# Index Management
# =============================================================================

BOOK_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # Single node for development
        "analysis": {
            "analyzer": {
                "book_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "english_stemmer", "english_possessive_stemmer"]
                }
            },
            "filter": {
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "title": {
                "type": "text",
                "analyzer": "book_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {
                        "type": "completion"
                    }
                }
            },
            "description": {
                "type": "text",
                "analyzer": "book_analyzer"
            },
            "isbn": {"type": "keyword"},
            "authors": {
                "type": "text",
                "analyzer": "book_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "author_ids": {"type": "integer"},
            "genres": {"type": "keyword"},
            "genre_ids": {"type": "integer"},
            "publication_year": {"type": "integer"},
            "price": {"type": "float"},
            "average_rating": {"type": "float"},
            "review_count": {"type": "integer"},
            "page_count": {"type": "integer"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    }
}


async def create_book_index() -> bool:
    """
    Create the books index with proper mapping.

    Returns:
        True if created or already exists, False on error
    """
    if not _es_client:
        return False

    index_name = get_index_name("books")

    try:
        exists = await _es_client.indices.exists(index=index_name)

        if not exists:
            await _es_client.indices.create(
                index=index_name,
                body=BOOK_INDEX_MAPPING
            )
            logger.info(f"Created Elasticsearch index: {index_name}")
        else:
            logger.debug(f"Elasticsearch index already exists: {index_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {e}")
        return False


async def delete_book_index() -> bool:
    """
    Delete the books index.

    Use with caution - this removes all indexed data!

    Returns:
        True if deleted, False on error
    """
    if not _es_client:
        return False

    index_name = get_index_name("books")

    try:
        exists = await _es_client.indices.exists(index=index_name)

        if exists:
            await _es_client.indices.delete(index=index_name)
            logger.info(f"Deleted Elasticsearch index: {index_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to delete index {index_name}: {e}")
        return False


# =============================================================================
# Document Operations
# =============================================================================

def book_to_document(book: Any) -> dict:
    """
    Convert a Book SQLAlchemy model to an Elasticsearch document.

    Args:
        book: Book model instance with relationships loaded

    Returns:
        Dictionary suitable for Elasticsearch indexing
    """
    return {
        "id": book.id,
        "title": book.title,
        "description": book.description or "",
        "isbn": book.isbn,
        "authors": [author.name for author in book.authors] if book.authors else [],
        "author_ids": [author.id for author in book.authors] if book.authors else [],
        "genres": [genre.name for genre in book.genres] if book.genres else [],
        "genre_ids": [genre.id for genre in book.genres] if book.genres else [],
        "publication_year": book.published_date.year if book.published_date else None,
        "price": float(book.price) if book.price else None,
        "average_rating": float(book.average_rating) if book.average_rating else 0.0,
        "review_count": book.review_count or 0,
        "page_count": book.page_count,
        "created_at": book.created_at.isoformat() if book.created_at else None,
        "updated_at": book.updated_at.isoformat() if book.updated_at else None,
    }


async def index_book(book: Any) -> bool:
    """
    Index a single book in Elasticsearch.

    Args:
        book: Book model instance

    Returns:
        True if indexed successfully, False otherwise
    """
    if not _es_client:
        return False

    index_name = get_index_name("books")

    try:
        document = book_to_document(book)

        await _es_client.index(
            index=index_name,
            id=str(book.id),
            document=document,
            refresh=True  # Make immediately searchable
        )

        logger.debug(f"Indexed book {book.id}: {book.title}")
        return True

    except Exception as e:
        logger.error(f"Failed to index book {book.id}: {e}")
        return False


async def bulk_index_books(books: list[Any]) -> tuple[int, int]:
    """
    Bulk index multiple books.

    Args:
        books: List of Book model instances

    Returns:
        Tuple of (success_count, error_count)
    """
    if not _es_client or not books:
        return 0, len(books) if books else 0

    index_name = get_index_name("books")

    def generate_actions():
        for book in books:
            yield {
                "_index": index_name,
                "_id": str(book.id),
                "_source": book_to_document(book),
            }

    try:
        success, errors = await async_bulk(
            _es_client,
            generate_actions(),
            raise_on_error=False,
            refresh=True
        )

        error_count = len(errors) if isinstance(errors, list) else 0
        logger.info(f"Bulk indexed {success} books, {error_count} errors")

        return success, error_count

    except Exception as e:
        logger.error(f"Bulk indexing failed: {e}")
        return 0, len(books)


async def delete_book_from_index(book_id: int) -> bool:
    """
    Remove a book from the Elasticsearch index.

    Args:
        book_id: ID of the book to remove

    Returns:
        True if deleted (or not found), False on error
    """
    if not _es_client:
        return False

    index_name = get_index_name("books")

    try:
        await _es_client.delete(
            index=index_name,
            id=str(book_id),
            refresh=True
        )
        logger.debug(f"Deleted book {book_id} from index")
        return True

    except NotFoundError:
        # Already not in index, that's fine
        return True

    except Exception as e:
        logger.error(f"Failed to delete book {book_id} from index: {e}")
        return False


async def update_book_in_index(book: Any) -> bool:
    """
    Update a book in the Elasticsearch index.

    This is equivalent to re-indexing the book.

    Args:
        book: Book model instance with updated data

    Returns:
        True if updated successfully, False otherwise
    """
    return await index_book(book)


# =============================================================================
# Search Operations
# =============================================================================

async def search_books(
    query: str | None = None,
    genres: list[str] | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    min_rating: float | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    size: int = 20,
    fuzzy: bool = True,
) -> dict:
    """
    Search books with full-text search and filters.

    Args:
        query: Full-text search query
        genres: List of genre names to filter by
        min_year: Minimum publication year
        max_year: Maximum publication year
        min_rating: Minimum average rating
        min_price: Minimum price
        max_price: Maximum price
        page: Page number (1-indexed)
        size: Results per page
        fuzzy: Enable fuzzy matching for typo tolerance

    Returns:
        Dictionary with items, total, and facets
    """
    if not _es_client:
        return {"items": [], "total": 0, "facets": {}, "fallback": True}

    index_name = get_index_name("books")

    # Build query
    must_clauses = []
    filter_clauses = []

    # Full-text search
    if query:
        if fuzzy:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "authors^2", "description"],
                    "fuzziness": "AUTO",
                    "prefix_length": 2,
                }
            })
        else:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "authors^2", "description"],
                }
            })

    # Filters
    if genres:
        filter_clauses.append({"terms": {"genres": genres}})

    if min_year is not None:
        filter_clauses.append({"range": {"publication_year": {"gte": min_year}}})

    if max_year is not None:
        filter_clauses.append({"range": {"publication_year": {"lte": max_year}}})

    if min_rating is not None:
        filter_clauses.append({"range": {"average_rating": {"gte": min_rating}}})

    if min_price is not None:
        filter_clauses.append({"range": {"price": {"gte": min_price}}})

    if max_price is not None:
        filter_clauses.append({"range": {"price": {"lte": max_price}}})

    # Build the final query
    if must_clauses or filter_clauses:
        es_query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        }
    else:
        es_query = {"match_all": {}}

    # Aggregations for facets
    aggs = {
        "genres": {
            "terms": {
                "field": "genres",
                "size": 20,
            }
        },
        "years": {
            "terms": {
                "field": "publication_year",
                "size": 20,
                "order": {"_key": "desc"}
            }
        },
        "rating_ranges": {
            "range": {
                "field": "average_rating",
                "ranges": [
                    {"key": "4+", "from": 4.0},
                    {"key": "3-4", "from": 3.0, "to": 4.0},
                    {"key": "2-3", "from": 2.0, "to": 3.0},
                    {"key": "1-2", "from": 1.0, "to": 2.0},
                ]
            }
        }
    }

    try:
        response = await _es_client.search(
            index=index_name,
            query=es_query,
            aggs=aggs,
            from_=(page - 1) * size,
            size=size,
            source=True,
        )

        # Extract results
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]

        items = []
        for hit in hits:
            item = hit["_source"]
            item["_score"] = hit["_score"]
            items.append(item)

        # Extract facets
        facets = {
            "genres": [
                {"name": bucket["key"], "count": bucket["doc_count"]}
                for bucket in response["aggregations"]["genres"]["buckets"]
            ],
            "years": [
                {"year": bucket["key"], "count": bucket["doc_count"]}
                for bucket in response["aggregations"]["years"]["buckets"]
            ],
            "ratings": [
                {"range": bucket["key"], "count": bucket["doc_count"]}
                for bucket in response["aggregations"]["rating_ranges"]["buckets"]
            ],
        }

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
            "facets": facets,
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"Elasticsearch search failed: {e}")
        return {"items": [], "total": 0, "facets": {}, "fallback": True}


async def get_document_count() -> int:
    """
    Get the total number of documents in the books index.

    Returns:
        Document count, or 0 if unavailable
    """
    if not _es_client:
        return 0

    index_name = get_index_name("books")

    try:
        response = await _es_client.count(index=index_name)
        return response["count"]
    except Exception:
        return 0
