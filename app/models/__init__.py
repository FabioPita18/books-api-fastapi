"""
SQLAlchemy Models Package

This package contains all database models for the Books API.
Models are SQLAlchemy ORM classes that map to database tables.

Model Relationships:
- Author <-> Book: Many-to-Many (an author can write many books,
                   a book can have multiple authors)
- Genre <-> Book: Many-to-Many (a book can belong to multiple genres,
                  a genre contains many books)

Import all models here to:
1. Make them available as: from app.models import Book, Author, Genre
2. Ensure Alembic discovers them for migrations
3. Provide a single import point for the application
"""

# Import all models so Alembic can discover them
# The order matters for SQLAlchemy to resolve relationships
from app.models.author import Author
from app.models.genre import Genre
from app.models.book import Book, book_authors, book_genres
from app.models.api_key import APIKey

# Export all models
__all__ = [
    "Author",
    "Genre",
    "Book",
    "book_authors",
    "book_genres",
    "APIKey",
]
