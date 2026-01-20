"""
GraphQL Types Package

This package contains all GraphQL type definitions that map to our
SQLAlchemy models. Types are defined using Strawberry's decorator syntax.

Types defined here:
- BookType: Book with authors, genres, and reviews
- AuthorType: Author with their books
- GenreType: Genre with book count
- UserType: Public user information
- ReviewType: Book review with user and book
- Various Input types for mutations
- Connection types for pagination
"""

from app.graphql.types.author import AuthorType
from app.graphql.types.book import BookConnection, BookType
from app.graphql.types.genre import GenreType
from app.graphql.types.review import ReviewType
from app.graphql.types.user import UserType

__all__ = [
    "BookType",
    "BookConnection",
    "AuthorType",
    "GenreType",
    "UserType",
    "ReviewType",
]
