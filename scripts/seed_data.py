#!/usr/bin/env python3
"""
Database Seed Script

Populates the database with sample data for development and testing.

USAGE:
    # Make sure you're in the project root with venv activated
    python scripts/seed_data.py

    # Or with Docker
    docker-compose exec api python scripts/seed_data.py

This script:
1. Connects to the database using app settings
2. Clears existing data (optional)
3. Creates sample authors, genres, and books
4. Establishes relationships between them
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.database import SessionLocal, create_tables
from app.models import Author, Book, Genre


def clear_data(db: Session) -> None:
    """Clear all existing data from the database."""
    print("Clearing existing data...")
    db.query(Book).delete()
    db.query(Author).delete()
    db.query(Genre).delete()
    db.commit()
    print("Data cleared.")


def create_authors(db: Session) -> dict[str, Author]:
    """Create sample authors."""
    print("Creating authors...")
    authors_data = [
        {
            "name": "George Orwell",
            "bio": "English novelist and essayist, journalist and critic. "
                   "Best known for '1984' and 'Animal Farm'.",
        },
        {
            "name": "Jane Austen",
            "bio": "English novelist known for her six major novels which critique "
                   "the British landed gentry at the end of the 18th century.",
        },
        {
            "name": "Ernest Hemingway",
            "bio": "American novelist, short-story writer, and journalist. "
                   "His economical style influenced 20th-century fiction.",
        },
        {
            "name": "Agatha Christie",
            "bio": "English writer known for her 66 detective novels and 14 short story collections.",
        },
        {
            "name": "Isaac Asimov",
            "bio": "American writer and professor of biochemistry. "
                   "Known for his works of science fiction and popular science.",
        },
        {
            "name": "J.R.R. Tolkien",
            "bio": "English writer, poet, philologist, and academic. "
                   "Best known for 'The Hobbit' and 'The Lord of the Rings'.",
        },
    ]

    authors = {}
    for data in authors_data:
        author = Author(**data)
        db.add(author)
        authors[data["name"]] = author

    db.commit()
    for author in authors.values():
        db.refresh(author)

    print(f"Created {len(authors)} authors.")
    return authors


def create_genres(db: Session) -> dict[str, Genre]:
    """Create sample genres."""
    print("Creating genres...")
    genres_data = [
        {
            "name": "Science Fiction",
            "description": "Fiction based on imagined future scientific or technological advances.",
        },
        {
            "name": "Fantasy",
            "description": "Fiction with supernatural or magical elements.",
        },
        {
            "name": "Mystery",
            "description": "Fiction dealing with the solution of a crime or puzzle.",
        },
        {
            "name": "Classic Literature",
            "description": "Timeless works of literary fiction.",
        },
        {
            "name": "Dystopian",
            "description": "Fiction depicting a dark, oppressive future society.",
        },
        {
            "name": "Romance",
            "description": "Fiction focused on romantic relationships.",
        },
    ]

    genres = {}
    for data in genres_data:
        genre = Genre(**data)
        db.add(genre)
        genres[data["name"]] = genre

    db.commit()
    for genre in genres.values():
        db.refresh(genre)

    print(f"Created {len(genres)} genres.")
    return genres


def create_books(
    db: Session,
    authors: dict[str, Author],
    genres: dict[str, Genre],
) -> list[Book]:
    """Create sample books with author and genre relationships."""
    print("Creating books...")

    books_data = [
        {
            "title": "1984",
            "isbn": "9780451524935",
            "description": "A dystopian novel set in a totalitarian society under constant surveillance.",
            "publication_date": date(1949, 6, 8),
            "page_count": 328,
            "price": Decimal("12.99"),
            "authors": ["George Orwell"],
            "genres": ["Science Fiction", "Dystopian", "Classic Literature"],
        },
        {
            "title": "Animal Farm",
            "isbn": "9780451526342",
            "description": "An allegorical novella reflecting events leading up to the Russian Revolution.",
            "publication_date": date(1945, 8, 17),
            "page_count": 112,
            "price": Decimal("9.99"),
            "authors": ["George Orwell"],
            "genres": ["Classic Literature"],
        },
        {
            "title": "Pride and Prejudice",
            "isbn": "9780141439518",
            "description": "A romantic novel following the emotional development of Elizabeth Bennet.",
            "publication_date": date(1813, 1, 28),
            "page_count": 432,
            "price": Decimal("8.99"),
            "authors": ["Jane Austen"],
            "genres": ["Romance", "Classic Literature"],
        },
        {
            "title": "The Old Man and the Sea",
            "isbn": "9780684801223",
            "description": "The story of an aging Cuban fisherman and his epic battle with a giant marlin.",
            "publication_date": date(1952, 9, 1),
            "page_count": 127,
            "price": Decimal("11.99"),
            "authors": ["Ernest Hemingway"],
            "genres": ["Classic Literature"],
        },
        {
            "title": "Murder on the Orient Express",
            "isbn": "9780062693662",
            "description": "Hercule Poirot investigates a murder on a train stuck in a snowdrift.",
            "publication_date": date(1934, 1, 1),
            "page_count": 256,
            "price": Decimal("14.99"),
            "authors": ["Agatha Christie"],
            "genres": ["Mystery", "Classic Literature"],
        },
        {
            "title": "Foundation",
            "isbn": "9780553293357",
            "description": "The first novel in the Foundation series about the fall of the Galactic Empire.",
            "publication_date": date(1951, 5, 1),
            "page_count": 244,
            "price": Decimal("15.99"),
            "authors": ["Isaac Asimov"],
            "genres": ["Science Fiction"],
        },
        {
            "title": "The Hobbit",
            "isbn": "9780547928227",
            "description": "Bilbo Baggins embarks on a quest to reclaim the Lonely Mountain.",
            "publication_date": date(1937, 9, 21),
            "page_count": 310,
            "price": Decimal("14.99"),
            "authors": ["J.R.R. Tolkien"],
            "genres": ["Fantasy", "Classic Literature"],
        },
        {
            "title": "I, Robot",
            "isbn": "9780553382563",
            "description": "A collection of nine science fiction short stories about robots.",
            "publication_date": date(1950, 12, 2),
            "page_count": 224,
            "price": Decimal("13.99"),
            "authors": ["Isaac Asimov"],
            "genres": ["Science Fiction"],
        },
    ]

    books = []
    for data in books_data:
        author_names = data.pop("authors")
        genre_names = data.pop("genres")

        book = Book(**data)
        book.authors = [authors[name] for name in author_names]
        book.genres = [genres[name] for name in genre_names]

        db.add(book)
        books.append(book)

    db.commit()
    for book in books:
        db.refresh(book)

    print(f"Created {len(books)} books.")
    return books


def seed_database(clear_existing: bool = True) -> None:
    """
    Main function to seed the database.

    Args:
        clear_existing: If True, clears existing data before seeding.
    """
    print("=" * 60)
    print("Starting database seed...")
    print("=" * 60)

    # Create tables if they don't exist
    create_tables()

    # Create session
    db = SessionLocal()

    try:
        if clear_existing:
            clear_data(db)

        authors = create_authors(db)
        genres = create_genres(db)
        books = create_books(db, authors, genres)

        print("=" * 60)
        print("Database seeding completed successfully!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Authors: {len(authors)}")
        print(f"  - Genres: {len(genres)}")
        print(f"  - Books: {len(books)}")
        print(f"\nYou can now access the API at http://localhost:8001")
        print(f"API documentation at http://localhost:8001/docs")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
