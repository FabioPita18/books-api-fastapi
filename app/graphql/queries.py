"""
GraphQL Query Resolvers

Defines all read operations (queries) for the GraphQL API.
Each resolver fetches data from the database using the context.
"""

import asyncio
import math

import strawberry
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.types.author import AuthorConnection, AuthorType
from app.graphql.types.book import (
    BookConnection,
    BookType,
    SearchFacet,
    SearchFiltersInput,
    SearchResultItem,
    SearchResults,
)
from app.graphql.types.genre import GenreConnection, GenreType
from app.graphql.types.review import ReviewConnection, ReviewType
from app.graphql.types.user import UserPublicType, UserType
from app.models import Author, Book, Genre
from app.models.review import Review
from app.services.recommendations import (
    get_recommendations_for_user,
    get_similar_books,
)
from app.services.search import search_books_advanced


def book_to_graphql(book: Book, include_reviews: bool = False) -> BookType:
    """Convert SQLAlchemy Book model to GraphQL BookType."""
    reviews = []
    if include_reviews and book.reviews:
        reviews = [review_to_graphql(r) for r in book.reviews]

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
        reviews=reviews,
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


def review_to_graphql(review: Review) -> ReviewType:
    """Convert SQLAlchemy Review model to GraphQL ReviewType."""
    user = None
    if review.user:
        user = UserPublicType(
            id=review.user.id,
            full_name=review.user.full_name,
            bio=review.user.bio,
            avatar_url=review.user.avatar_url,
        )

    return ReviewType(
        id=review.id,
        rating=review.rating,
        title=review.title,
        content=review.content,
        created_at=review.created_at,
        updated_at=review.updated_at,
        user=user,
        book_id=review.book_id,
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
    def book(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        include_reviews: bool = False,
    ) -> BookType | None:
        """
        Get a single book by its ID.

        Args:
            id: Book ID
            include_reviews: Whether to include reviews in the response

        Returns:
            Book if found, None otherwise
        """
        db = info.context.db

        stmt = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.genres))
            .where(Book.id == id)
        )

        if include_reviews:
            stmt = stmt.options(selectinload(Book.reviews).selectinload(Review.user))

        book = db.execute(stmt).scalar_one_or_none()

        if book is None:
            return None

        return book_to_graphql(book, include_reviews=include_reviews)

    @strawberry.field(description="Get a paginated list of authors")
    def authors(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 10,
        name: str | None = None,
    ) -> AuthorConnection:
        """
        Get authors with optional filtering and pagination.

        Args:
            page: Page number
            per_page: Items per page
            name: Filter by name (partial match)

        Returns:
            Paginated list of authors
        """
        db = info.context.db
        per_page = min(max(1, per_page), 100)

        stmt = select(Author)

        if name:
            stmt = stmt.where(func.lower(Author.name).contains(name.lower()))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        # Calculate pagination
        pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page

        stmt = stmt.offset(offset).limit(per_page).order_by(Author.name)
        authors = db.execute(stmt).scalars().all()

        return AuthorConnection(
            items=[author_to_graphql(a) for a in authors],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    @strawberry.field(description="Get a single author by ID")
    def author(self, info: Info[GraphQLContext, None], id: int) -> AuthorType | None:
        """Get a single author by ID."""
        db = info.context.db

        stmt = select(Author).where(Author.id == id)
        author = db.execute(stmt).scalar_one_or_none()

        if author is None:
            return None

        return author_to_graphql(author)

    @strawberry.field(description="Get a paginated list of genres")
    def genres(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 50,
    ) -> GenreConnection:
        """Get all available genres with pagination."""
        db = info.context.db
        per_page = min(max(1, per_page), 100)

        stmt = select(Genre)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        # Calculate pagination
        pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page

        stmt = stmt.offset(offset).limit(per_page).order_by(Genre.name)
        genres = db.execute(stmt).scalars().all()

        return GenreConnection(
            items=[genre_to_graphql(g) for g in genres],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    @strawberry.field(description="Get a single genre by ID")
    def genre(self, info: Info[GraphQLContext, None], id: int) -> GenreType | None:
        """Get a single genre by ID."""
        db = info.context.db

        stmt = select(Genre).where(Genre.id == id)
        genre = db.execute(stmt).scalar_one_or_none()

        if genre is None:
            return None

        return genre_to_graphql(genre)

    @strawberry.field(description="Get reviews for a book")
    def reviews(
        self,
        info: Info[GraphQLContext, None],
        book_id: int,
        page: int = 1,
        per_page: int = 10,
    ) -> ReviewConnection:
        """
        Get reviews for a specific book.

        Args:
            book_id: ID of the book to get reviews for
            page: Page number
            per_page: Items per page

        Returns:
            Paginated list of reviews
        """
        db = info.context.db
        per_page = min(max(1, per_page), 100)

        stmt = (
            select(Review)
            .options(selectinload(Review.user))
            .where(Review.book_id == book_id)
        )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        # Calculate pagination
        pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page

        stmt = stmt.offset(offset).limit(per_page).order_by(Review.created_at.desc())
        reviews = db.execute(stmt).scalars().all()

        return ReviewConnection(
            items=[review_to_graphql(r) for r in reviews],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

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

    @strawberry.field(description="Search books using Elasticsearch with filters")
    def search(
        self,
        info: Info[GraphQLContext, None],
        query: str | None = None,
        filters: SearchFiltersInput | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResults:
        """
        Search books using Elasticsearch with optional filters.

        Args:
            query: Full-text search query
            filters: Optional search filters (genres, year range, rating, price)
            page: Page number (1-indexed)
            per_page: Results per page (max 100)

        Returns:
            Search results with facets for further filtering
        """
        db = info.context.db
        per_page = min(max(1, per_page), 100)

        # Extract filter values
        genres = filters.genres if filters else None
        min_year = filters.min_year if filters else None
        max_year = filters.max_year if filters else None
        min_rating = filters.min_rating if filters else None
        min_price = filters.min_price if filters else None
        max_price = filters.max_price if filters else None

        # Run async search in sync context
        result = asyncio.get_event_loop().run_until_complete(
            search_books_advanced(
                db=db,
                query=query,
                genres=genres,
                min_year=min_year,
                max_year=max_year,
                min_rating=min_rating,
                min_price=min_price,
                max_price=max_price,
                page=page,
                size=per_page,
            )
        )

        # Convert results to GraphQL types
        items = []
        for item in result.get("items", []):
            book_data = item.get("book", item)
            # Create minimal BookType from search results
            book_type = BookType(
                id=book_data.get("id"),
                title=book_data.get("title", ""),
                isbn=book_data.get("isbn"),
                description=book_data.get("description"),
                publication_date=book_data.get("publication_date"),
                page_count=book_data.get("page_count"),
                price=book_data.get("price"),
                average_rating=book_data.get("average_rating"),
                review_count=book_data.get("review_count", 0),
                created_at=book_data.get("created_at"),
                updated_at=book_data.get("updated_at"),
                authors=[
                    AuthorType(
                        id=a.get("id"),
                        name=a.get("name", ""),
                        bio=a.get("bio"),
                        birth_date=a.get("birth_date"),
                        website=a.get("website"),
                    )
                    for a in book_data.get("authors", [])
                ],
                genres=[
                    GenreType(
                        id=g.get("id"),
                        name=g.get("name", ""),
                        description=g.get("description"),
                    )
                    for g in book_data.get("genres", [])
                ],
            )
            items.append(
                SearchResultItem(book=book_type, score=item.get("score"))
            )

        # Convert facets
        facets = []
        for facet_name, facet_data in result.get("facets", {}).items():
            for bucket in facet_data:
                facets.append(
                    SearchFacet(
                        name=f"{facet_name}:{bucket.get('name', bucket.get('key', ''))}",
                        count=bucket.get("count", bucket.get("doc_count", 0)),
                    )
                )

        return SearchResults(
            items=items,
            total=result.get("total", 0),
            page=result.get("page", page),
            pages=result.get("pages", 0),
            facets=facets,
        )

    @strawberry.field(description="Get similar books based on a book ID")
    def similar_books(
        self,
        info: Info[GraphQLContext, None],
        book_id: int,
        limit: int = 10,
    ) -> list[SearchResultItem]:
        """
        Get books similar to a given book.

        Uses content-based filtering (genres, authors) to find similar books.

        Args:
            book_id: ID of the book to find similar books for
            limit: Maximum number of results (default 10)

        Returns:
            List of similar books with similarity scores
        """
        db = info.context.db
        limit = min(max(1, limit), 50)

        # Get user's read books to exclude (if authenticated)
        exclude_ids = []
        user = info.context.user
        if user:
            # Get book IDs the user has reviewed (i.e., read)
            stmt = select(Review.book_id).where(Review.user_id == user.id)
            exclude_ids = [r for r in db.execute(stmt).scalars().all()]

        results = get_similar_books(
            db=db,
            book_id=book_id,
            limit=limit,
            exclude_book_ids=exclude_ids if exclude_ids else None,
        )

        # Convert to GraphQL types
        items = []
        for result in results:
            book_data = result.get("book", {})
            # Fetch full book data
            stmt = (
                select(Book)
                .options(selectinload(Book.authors), selectinload(Book.genres))
                .where(Book.id == book_data.get("id"))
            )
            book = db.execute(stmt).scalar_one_or_none()

            if book:
                items.append(
                    SearchResultItem(
                        book=book_to_graphql(book),
                        score=result.get("score"),
                    )
                )

        return items

    @strawberry.field(description="Get personalized book recommendations")
    def recommendations(
        self,
        info: Info[GraphQLContext, None],
        limit: int = 10,
    ) -> list[SearchResultItem]:
        """
        Get personalized book recommendations for the authenticated user.

        Uses collaborative filtering based on the user's review history.
        Requires authentication.

        Args:
            limit: Maximum number of recommendations (default 10)

        Returns:
            List of recommended books with relevance scores
        """
        user = info.context.user

        if user is None:
            # Return empty list for unauthenticated users
            return []

        db = info.context.db
        limit = min(max(1, limit), 50)

        results = get_recommendations_for_user(
            db=db,
            user_id=user.id,
            limit=limit,
        )

        # Convert to GraphQL types
        items = []
        for result in results:
            book_data = result.get("book", {})
            # Fetch full book data
            stmt = (
                select(Book)
                .options(selectinload(Book.authors), selectinload(Book.genres))
                .where(Book.id == book_data.get("id"))
            )
            book = db.execute(stmt).scalar_one_or_none()

            if book:
                items.append(
                    SearchResultItem(
                        book=book_to_graphql(book),
                        score=result.get("score"),
                    )
                )

        return items
