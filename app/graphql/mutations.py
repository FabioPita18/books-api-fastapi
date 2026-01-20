"""
GraphQL Mutation Resolvers

Defines all write operations (mutations) for the GraphQL API.
Mutations require authentication for most operations.
"""

from datetime import UTC, datetime

import strawberry
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.queries import (
    author_to_graphql,
    book_to_graphql,
    genre_to_graphql,
    review_to_graphql,
)
from app.graphql.types.author import AuthorInput, AuthorType
from app.graphql.types.book import BookInput, BookType, BookUpdateInput
from app.graphql.types.genre import GenreInput, GenreType
from app.graphql.types.review import ReviewInput, ReviewType, ReviewUpdateInput
from app.graphql.types.user import AuthPayload, LoginInput, RegisterInput, UserType
from app.models import Author, Book, Genre
from app.models.review import Review
from app.models.user import AuthProvider, User
from app.services.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


# =============================================================================
# Error classes for GraphQL
# =============================================================================


class AuthenticationError(Exception):
    """Raised when authentication is required but not provided."""

    pass


class AuthorizationError(Exception):
    """Raised when user lacks permission for an operation."""

    pass


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


def require_auth(info: Info[GraphQLContext, None]) -> User:
    """Helper to require authentication and return the user."""
    user = info.context.user
    if user is None:
        raise AuthenticationError("Authentication required")
    return user


# =============================================================================
# Mutation Type
# =============================================================================


@strawberry.type
class Mutation:
    """
    GraphQL Mutation type containing all write operations.

    Most mutations require authentication via JWT token.
    """

    # =========================================================================
    # Authentication Mutations
    # =========================================================================

    @strawberry.mutation(description="Login with email and password")
    def login(
        self,
        info: Info[GraphQLContext, None],
        input: LoginInput,
    ) -> AuthPayload:
        """
        Authenticate with email and password.

        Returns access and refresh tokens on success.
        """
        db = info.context.db

        # Find user by email
        stmt = select(User).where(User.email == input.email)
        user = db.execute(stmt).scalar_one_or_none()

        # Verify credentials
        if not user or not user.hashed_password:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(input.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthorizationError("Account is inactive")

        # Create tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Update last login
        user.last_login_at = datetime.now(UTC)
        db.commit()

        return AuthPayload(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserType(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )

    @strawberry.mutation(description="Register a new user account")
    def register(
        self,
        info: Info[GraphQLContext, None],
        input: RegisterInput,
    ) -> AuthPayload:
        """
        Create a new user account.

        Returns access and refresh tokens on success.
        """
        db = info.context.db

        # Check if email already exists
        stmt = select(User).where(User.email == input.email)
        if db.execute(stmt).scalar_one_or_none():
            raise ValidationError("Email already registered")

        # Create user
        user = User(
            email=input.email,
            username=input.email.split("@")[0].lower(),  # Generate username from email
            hashed_password=hash_password(input.password),
            full_name=input.full_name,
            auth_provider=AuthProvider.LOCAL.value,
            is_active=True,
            is_verified=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Create tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return AuthPayload(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserType(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )

    # =========================================================================
    # Book Mutations
    # =========================================================================

    @strawberry.mutation(description="Create a new book")
    def create_book(
        self,
        info: Info[GraphQLContext, None],
        input: BookInput,
    ) -> BookType:
        """
        Create a new book.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        # Create book
        book = Book(
            title=input.title,
            isbn=input.isbn,
            description=input.description,
            publication_date=input.publication_date,
            page_count=input.page_count,
            price=input.price,
        )

        # Add authors
        if input.author_ids:
            stmt = select(Author).where(Author.id.in_(input.author_ids))
            authors = db.execute(stmt).scalars().all()
            if len(authors) != len(input.author_ids):
                raise NotFoundError("One or more authors not found")
            book.authors = list(authors)

        # Add genres
        if input.genre_ids:
            stmt = select(Genre).where(Genre.id.in_(input.genre_ids))
            genres = db.execute(stmt).scalars().all()
            if len(genres) != len(input.genre_ids):
                raise NotFoundError("One or more genres not found")
            book.genres = list(genres)

        db.add(book)
        db.commit()
        db.refresh(book)

        # Reload with relationships
        stmt = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.genres))
            .where(Book.id == book.id)
        )
        book = db.execute(stmt).scalar_one()

        return book_to_graphql(book)

    @strawberry.mutation(description="Update an existing book")
    def update_book(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        input: BookUpdateInput,
    ) -> BookType:
        """
        Update an existing book.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        # Find book
        stmt = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.genres))
            .where(Book.id == id)
        )
        book = db.execute(stmt).scalar_one_or_none()

        if book is None:
            raise NotFoundError(f"Book with ID {id} not found")

        # Update fields
        if input.title is not None:
            book.title = input.title
        if input.isbn is not None:
            book.isbn = input.isbn
        if input.description is not None:
            book.description = input.description
        if input.publication_date is not None:
            book.publication_date = input.publication_date
        if input.page_count is not None:
            book.page_count = input.page_count
        if input.price is not None:
            book.price = input.price

        # Update authors
        if input.author_ids is not None:
            stmt = select(Author).where(Author.id.in_(input.author_ids))
            authors = db.execute(stmt).scalars().all()
            if len(authors) != len(input.author_ids):
                raise NotFoundError("One or more authors not found")
            book.authors = list(authors)

        # Update genres
        if input.genre_ids is not None:
            stmt = select(Genre).where(Genre.id.in_(input.genre_ids))
            genres = db.execute(stmt).scalars().all()
            if len(genres) != len(input.genre_ids):
                raise NotFoundError("One or more genres not found")
            book.genres = list(genres)

        db.commit()
        db.refresh(book)

        return book_to_graphql(book)

    @strawberry.mutation(description="Delete a book")
    def delete_book(
        self,
        info: Info[GraphQLContext, None],
        id: int,
    ) -> bool:
        """
        Delete a book.

        Requires authentication.
        Returns True if deleted successfully.
        """
        require_auth(info)
        db = info.context.db

        stmt = select(Book).where(Book.id == id)
        book = db.execute(stmt).scalar_one_or_none()

        if book is None:
            raise NotFoundError(f"Book with ID {id} not found")

        db.delete(book)
        db.commit()

        return True

    # =========================================================================
    # Author Mutations
    # =========================================================================

    @strawberry.mutation(description="Create a new author")
    def create_author(
        self,
        info: Info[GraphQLContext, None],
        input: AuthorInput,
    ) -> AuthorType:
        """
        Create a new author.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        author = Author(
            name=input.name,
            bio=input.bio,
            birth_date=input.birth_date,
            website=input.website,
        )

        db.add(author)
        db.commit()
        db.refresh(author)

        return author_to_graphql(author)

    @strawberry.mutation(description="Update an existing author")
    def update_author(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        input: AuthorInput,
    ) -> AuthorType:
        """
        Update an existing author.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        stmt = select(Author).where(Author.id == id)
        author = db.execute(stmt).scalar_one_or_none()

        if author is None:
            raise NotFoundError(f"Author with ID {id} not found")

        # Update fields (only if provided)
        if input.name:
            author.name = input.name
        if input.bio is not None:
            author.bio = input.bio
        if input.birth_date is not None:
            author.birth_date = input.birth_date
        if input.website is not None:
            author.website = input.website

        db.commit()
        db.refresh(author)

        return author_to_graphql(author)

    @strawberry.mutation(description="Delete an author")
    def delete_author(
        self,
        info: Info[GraphQLContext, None],
        id: int,
    ) -> bool:
        """
        Delete an author.

        Requires authentication.
        Returns True if deleted successfully.
        """
        require_auth(info)
        db = info.context.db

        stmt = select(Author).where(Author.id == id)
        author = db.execute(stmt).scalar_one_or_none()

        if author is None:
            raise NotFoundError(f"Author with ID {id} not found")

        db.delete(author)
        db.commit()

        return True

    # =========================================================================
    # Genre Mutations
    # =========================================================================

    @strawberry.mutation(description="Create a new genre")
    def create_genre(
        self,
        info: Info[GraphQLContext, None],
        input: GenreInput,
    ) -> GenreType:
        """
        Create a new genre.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        # Check for duplicate name
        stmt = select(Genre).where(Genre.name == input.name)
        if db.execute(stmt).scalar_one_or_none():
            raise ValidationError(f"Genre '{input.name}' already exists")

        genre = Genre(
            name=input.name,
            description=input.description,
        )

        db.add(genre)
        db.commit()
        db.refresh(genre)

        return genre_to_graphql(genre)

    @strawberry.mutation(description="Update an existing genre")
    def update_genre(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        input: GenreInput,
    ) -> GenreType:
        """
        Update an existing genre.

        Requires authentication.
        """
        require_auth(info)
        db = info.context.db

        stmt = select(Genre).where(Genre.id == id)
        genre = db.execute(stmt).scalar_one_or_none()

        if genre is None:
            raise NotFoundError(f"Genre with ID {id} not found")

        # Check for duplicate name (if changing)
        if input.name and input.name != genre.name:
            stmt = select(Genre).where(Genre.name == input.name)
            if db.execute(stmt).scalar_one_or_none():
                raise ValidationError(f"Genre '{input.name}' already exists")
            genre.name = input.name

        if input.description is not None:
            genre.description = input.description

        db.commit()
        db.refresh(genre)

        return genre_to_graphql(genre)

    @strawberry.mutation(description="Delete a genre")
    def delete_genre(
        self,
        info: Info[GraphQLContext, None],
        id: int,
    ) -> bool:
        """
        Delete a genre.

        Requires authentication.
        Returns True if deleted successfully.
        """
        require_auth(info)
        db = info.context.db

        stmt = select(Genre).where(Genre.id == id)
        genre = db.execute(stmt).scalar_one_or_none()

        if genre is None:
            raise NotFoundError(f"Genre with ID {id} not found")

        db.delete(genre)
        db.commit()

        return True

    # =========================================================================
    # Review Mutations
    # =========================================================================

    @strawberry.mutation(description="Create a review for a book")
    def create_review(
        self,
        info: Info[GraphQLContext, None],
        book_id: int,
        input: ReviewInput,
    ) -> ReviewType:
        """
        Create a review for a book.

        Requires authentication. Users can only create one review per book.
        """
        user = require_auth(info)
        db = info.context.db

        # Check book exists
        stmt = select(Book).where(Book.id == book_id)
        book = db.execute(stmt).scalar_one_or_none()
        if book is None:
            raise NotFoundError(f"Book with ID {book_id} not found")

        # Check for existing review
        stmt = select(Review).where(
            Review.book_id == book_id,
            Review.user_id == user.id,
        )
        if db.execute(stmt).scalar_one_or_none():
            raise ValidationError("You have already reviewed this book")

        # Validate rating
        if input.rating < 1 or input.rating > 5:
            raise ValidationError("Rating must be between 1 and 5")

        review = Review(
            book_id=book_id,
            user_id=user.id,
            rating=input.rating,
            title=input.title,
            content=input.content,
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        # Reload with user relationship
        stmt = (
            select(Review)
            .options(selectinload(Review.user))
            .where(Review.id == review.id)
        )
        review = db.execute(stmt).scalar_one()

        return review_to_graphql(review)

    @strawberry.mutation(description="Update a review")
    def update_review(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        input: ReviewUpdateInput,
    ) -> ReviewType:
        """
        Update a review.

        Requires authentication. Users can only update their own reviews.
        """
        user = require_auth(info)
        db = info.context.db

        stmt = (
            select(Review)
            .options(selectinload(Review.user))
            .where(Review.id == id)
        )
        review = db.execute(stmt).scalar_one_or_none()

        if review is None:
            raise NotFoundError(f"Review with ID {id} not found")

        # Check ownership
        if review.user_id != user.id:
            raise AuthorizationError("You can only update your own reviews")

        # Update fields
        if input.rating is not None:
            if input.rating < 1 or input.rating > 5:
                raise ValidationError("Rating must be between 1 and 5")
            review.rating = input.rating
        if input.title is not None:
            review.title = input.title
        if input.content is not None:
            review.content = input.content

        db.commit()
        db.refresh(review)

        return review_to_graphql(review)

    @strawberry.mutation(description="Delete a review")
    def delete_review(
        self,
        info: Info[GraphQLContext, None],
        id: int,
    ) -> bool:
        """
        Delete a review.

        Requires authentication. Users can only delete their own reviews.
        Superusers can delete any review.
        """
        user = require_auth(info)
        db = info.context.db

        stmt = select(Review).where(Review.id == id)
        review = db.execute(stmt).scalar_one_or_none()

        if review is None:
            raise NotFoundError(f"Review with ID {id} not found")

        # Check ownership or superuser
        if review.user_id != user.id and not user.is_superuser:
            raise AuthorizationError("You can only delete your own reviews")

        db.delete(review)
        db.commit()

        return True
