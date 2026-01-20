#!/usr/bin/env python3
"""
Elasticsearch Reindex Script

This script reindexes all books from PostgreSQL into Elasticsearch.

Usage:
    # From project root with venv activated:
    python scripts/reindex_elasticsearch.py

    # With Docker:
    docker-compose exec api python scripts/reindex_elasticsearch.py

    # Options:
    python scripts/reindex_elasticsearch.py --drop   # Drop and recreate index first
    python scripts/reindex_elasticsearch.py --batch-size 100  # Custom batch size
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.book import Book
from app.services.elasticsearch import (
    bulk_index_books,
    create_book_index,
    delete_book_index,
    get_document_count,
    init_elasticsearch,
    close_elasticsearch,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def reindex_all_books(drop_index: bool = False, batch_size: int = 100) -> None:
    """
    Reindex all books from PostgreSQL to Elasticsearch.

    Args:
        drop_index: If True, drop and recreate the index first
        batch_size: Number of books to index in each batch
    """
    logger.info("Starting Elasticsearch reindex...")

    # Initialize Elasticsearch
    connected = await init_elasticsearch()
    if not connected:
        logger.error("Failed to connect to Elasticsearch")
        return

    try:
        # Optionally drop and recreate index
        if drop_index:
            logger.info("Dropping existing index...")
            await delete_book_index()
            logger.info("Creating fresh index...")
            await create_book_index()

        # Get all books from PostgreSQL
        logger.info("Fetching books from PostgreSQL...")
        db = SessionLocal()

        try:
            # Load books with their relationships
            stmt = (
                select(Book)
                .options(
                    joinedload(Book.authors),
                    joinedload(Book.genres),
                )
                .order_by(Book.id)
            )
            result = db.execute(stmt)
            books = result.unique().scalars().all()

            total_books = len(books)
            logger.info(f"Found {total_books} books to index")

            if total_books == 0:
                logger.warning("No books found in database")
                return

            # Index in batches
            total_success = 0
            total_errors = 0

            for i in range(0, total_books, batch_size):
                batch = books[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_books + batch_size - 1) // batch_size

                logger.info(f"Indexing batch {batch_num}/{total_batches} ({len(batch)} books)...")

                success, errors = await bulk_index_books(batch)
                total_success += success
                total_errors += errors

            # Report results
            logger.info("=" * 50)
            logger.info("Reindex complete!")
            logger.info(f"Total books processed: {total_books}")
            logger.info(f"Successfully indexed: {total_success}")
            logger.info(f"Errors: {total_errors}")

            # Verify count
            doc_count = await get_document_count()
            logger.info(f"Documents in index: {doc_count}")

        finally:
            db.close()

    finally:
        await close_elasticsearch()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reindex all books in Elasticsearch"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop and recreate the index before reindexing"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of books to index in each batch (default: 100)"
    )

    args = parser.parse_args()

    # Run the async function
    asyncio.run(reindex_all_books(
        drop_index=args.drop,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
