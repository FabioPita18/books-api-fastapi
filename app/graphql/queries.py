"""
GraphQL Query Resolvers

Defines all read operations (queries) for the GraphQL API.
Each resolver fetches data from the database using the context.
"""

import math

import strawberry
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.types.author import AuthorType
from app.graphql.types.book import BookConnection, BookType
from app.graphql.types.genre import GenreType
from app.graphql.types.user import UserType
from app.models import Author, Book, Genre


def book_to_graphql(book: Book) -> BookType:
    """Convert SQLAlchemy Book model to GraphQL BookType."""
    return BookType(
        id=book.id,
        title=book.title,
        isbn=book.isbn,
        description=book.description,
        publication_date=book.publication_date,
        page_count=book.page_count,
        price=book.price,
        average_rating=float(book.average_rating) if book.average_rating else None,
        review_count=book.review_count or 0,
        created_at=book.created_at,
        updated_at=book.updated_at,
        authors=[
            AuthorType(
                id=a.id,
                name=a.name,
                bio=a.bio,
                birth_date=a.birth_date,
                website=a.website,
            )
            for a in (book.authors or [])
        ],
        genres=[
            GenreType(id=g.id, name=g.name, description=g.description)
            for g in (book.genres or [])
        ],
    )


def author_to_graphql(author: Author) -> AuthorType:
    """Convert SQLAlchemy Author model to GraphQL AuthorType."""
    return AuthorType(
        id=author.id,
        name=author.name,
        bio=author.bio,
        birth_date=author.birth_date,
        website=author.website,
    )


def genre_to_graphql(genre: Genre) -> GenreType:
    """Convert SQLAlchemy Genre model to GraphQL GenreType."""
    return GenreType(
        id=genre.id,
        name=genre.name,
        description=genre.description,
    )


@strawberry.type
class Query:
    """
    GraphQL Query type containing all read operations.

    All resolvers receive an `info` parameter that contains the
    GraphQL context with database session and current user.
    """

    @strawberry.field(description="Get a paginated list of books")
    def books(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 10,
        title: str | None = None,
        genre_id: int | None = None,
        author_id: int | None = None,
    ) -> BookConnection:
        """
        Get books with optional filtering and pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page (max 100)
            title: Filter by title (partial match)
            genre_id: Filter by genre ID
            author_id: Filter by author ID

        Returns:
            Paginated list of books
        """
        db = info.context.db

        # Clamp per_page to reasonable limits
        per_page = min(max(1, per_page), 100)

        # Build query
        stmt = select(Book).options(
            selectinload(Book.authors), selectinload(Book.genres)
        )

        # Apply filters
        if title:
            stmt = stmt.where(func.lower(Book.title).contains(title.lower()))

        if genre_id:
            stmt = stmt.join(Book.genres).where(Genre.id == genre_id)

        if author_id:
            stmt = stmt.join(Book.authors).where(Author.id == author_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        # Calculate pagination
        pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page

        # Fetch books
        stmt = stmt.offset(offset).limit(per_page).order_by(Book.created_at.desc())
        books = db.execute(stmt).scalars().all()

        return BookConnection(
            items=[book_to_graphql(b) for b in books],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    @strawberry.field(description="Get a single book by ID")
    def book(self, info: Info[GraphQLContext, None], id: int) -> BookType | None:
        """
        Get a single book by its ID.

        Args:
            id: Book ID

        Returns:
            Book if found, None otherwise
        """
        db = info.context.db

        stmt = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.genres))
            .where(Book.id == id)
        )
        book = db.execute(stmt).scalar_one_or_none()

        if book is None:
            return None

        return book_to_graphql(book)

    @strawberry.field(description="Get a paginated list of authors")
    def authors(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 10,
        name: str | None = None,
    ) -> list[AuthorType]:
        """
        Get authors with optional filtering.

        Args:
            page: Page number
            per_page: Items per page
            name: Filter by name (partial match)

        Returns:
            List of authors
        """
        db = info.context.db
        per_page = min(max(1, per_page), 100)

        stmt = select(Author)

        if name:
            stmt = stmt.where(func.lower(Author.name).contains(name.lower()))

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page).order_by(Author.name)

        authors = db.execute(stmt).scalars().all()
        return [author_to_graphql(a) for a in authors]

    @strawberry.field(description="Get a single author by ID")
    def author(self, info: Info[GraphQLContext, None], id: int) -> AuthorType | None:
        """Get a single author by ID."""
        db = info.context.db

        stmt = select(Author).where(Author.id == id)
        author = db.execute(stmt).scalar_one_or_none()

        if author is None:
            return None

        return author_to_graphql(author)

    @strawberry.field(description="Get all genres")
    def genres(self, info: Info[GraphQLContext, None]) -> list[GenreType]:
        """Get all available genres."""
        db = info.context.db

        stmt = select(Genre).order_by(Genre.name)
        genres = db.execute(stmt).scalars().all()

        return [genre_to_graphql(g) for g in genres]

    @strawberry.field(description="Get a single genre by ID")
    def genre(self, info: Info[GraphQLContext, None], id: int) -> GenreType | None:
        """Get a single genre by ID."""
        db = info.context.db

        stmt = select(Genre).where(Genre.id == id)
        genre = db.execute(stmt).scalar_one_or_none()

        if genre is None:
            return None

        return genre_to_graphql(genre)

    @strawberry.field(description="Get the currently authenticated user")
    def me(self, info: Info[GraphQLContext, None]) -> UserType | None:
        """
        Get the current authenticated user.

        Returns None if not authenticated.
        """
        user = info.context.user

        if user is None:
            return None

        return UserType(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
        )
