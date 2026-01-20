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

from app.graphql.types.author import AuthorConnection, AuthorInput, AuthorType
from app.graphql.types.book import (
    BookConnection,
    BookInput,
    BookType,
    BookUpdateInput,
    SearchFacet,
    SearchFiltersInput,
    SearchResultItem,
    SearchResults,
)
from app.graphql.types.genre import GenreConnection, GenreInput, GenreType
from app.graphql.types.review import (
    ReviewConnection,
    ReviewInput,
    ReviewType,
    ReviewUpdateInput,
)
from app.graphql.types.user import (
    AuthPayload,
    LoginInput,
    RegisterInput,
    UserPublicType,
    UserType,
)

__all__ = [
    # Book types
    "BookType",
    "BookConnection",
    "BookInput",
    "BookUpdateInput",
    "SearchFiltersInput",
    "SearchResultItem",
    "SearchFacet",
    "SearchResults",
    # Author types
    "AuthorType",
    "AuthorConnection",
    "AuthorInput",
    # Genre types
    "GenreType",
    "GenreConnection",
    "GenreInput",
    # User types
    "UserType",
    "UserPublicType",
    "AuthPayload",
    "LoginInput",
    "RegisterInput",
    # Review types
    "ReviewType",
    "ReviewConnection",
    "ReviewInput",
    "ReviewUpdateInput",
]
