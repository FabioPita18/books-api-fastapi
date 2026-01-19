"""
pytest Fixtures for Books API Tests

This file contains shared fixtures used across all test files.

WHAT ARE FIXTURES?
==================
Fixtures are reusable test setup/teardown functions.
They provide:
- Test data (sample books, authors)
- Test resources (database connections, HTTP clients)
- Setup/cleanup logic (create/drop tables)

HOW FIXTURES WORK:
1. pytest discovers fixtures by the @pytest.fixture decorator
2. Tests request fixtures by including them as parameters
3. pytest calls the fixture, provides the return value to the test
4. After the test, cleanup code after yield runs

FIXTURE SCOPES:
- function (default): New instance per test function
- class: New instance per test class
- module: New instance per test module
- session: Single instance for entire test session

For database tests, we use:
- session scope for engine (expensive to create)
- function scope for sessions (isolation between tests)
"""

# =============================================================================
# TEST ENVIRONMENT SETUP
# =============================================================================
# IMPORTANT: Set environment variables BEFORE importing the app
# This disables rate limiting and sets a test secret key
import os

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-at-least-32-characters-long"

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Author, Book, Genre
from app.models.user import User
from app.models.review import Review
from app.services.security import hash_password

# =============================================================================
# DATABASE FIXTURES
# =============================================================================
# We use SQLite in-memory for tests because:
# - Fast: No disk I/O, runs in memory
# - Isolated: Each test run starts fresh
# - Simple: No external database needed
#
# IMPORTANT: Some PostgreSQL features won't work in SQLite.
# For integration tests, use a real PostgreSQL test database.

@pytest.fixture(scope="session")
def engine():
    """
    Create a SQLite in-memory database engine.

    Scope: session
    - Created once for all tests
    - Shared across all test modules
    - Cleaned up after all tests complete

    StaticPool keeps the connection alive for the entire session.
    Without it, SQLite in-memory database would disappear between connections.
    """
    # SQLite in-memory database with shared cache
    # check_same_thread=False allows multiple threads (needed for tests)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup: Drop all tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.

    Scope: function
    - New session for each test function
    - Changes are rolled back after each test
    - Tests don't affect each other

    The session is wrapped in a transaction that's rolled back,
    ensuring test isolation without needing to recreate tables.
    """
    # Create session factory bound to test engine
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    # Begin a transaction
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    # Cleanup: Rollback and close
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with the test database.

    The test client:
    - Makes HTTP requests to our FastAPI app
    - Uses the test database (not production)
    - Allows testing endpoints without running a server

    We override the get_db dependency to use our test session.
    This is dependency injection in action!
    """

    def override_get_db():
        """Provide test database session instead of real one."""
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Remove override after test
    app.dependency_overrides.clear()


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================
# These fixtures provide test data.
# They depend on db_session, so they're created fresh for each test.


@pytest.fixture
def sample_author(db_session: Session) -> Author:
    """Create a sample author for testing."""
    author = Author(
        name="George Orwell",
        bio="English novelist and essayist, journalist and critic.",
    )
    db_session.add(author)
    db_session.commit()
    db_session.refresh(author)
    return author


@pytest.fixture
def sample_genre(db_session: Session) -> Genre:
    """Create a sample genre for testing."""
    genre = Genre(
        name="Science Fiction",
        description="Fiction based on futuristic science and technology.",
    )
    db_session.add(genre)
    db_session.commit()
    db_session.refresh(genre)
    return genre


@pytest.fixture
def sample_book(
    db_session: Session,
    sample_author: Author,
    sample_genre: Genre,
) -> Book:
    """
    Create a sample book with author and genre associations.

    This fixture depends on sample_author and sample_genre fixtures.
    pytest automatically resolves these dependencies.
    """
    book = Book(
        title="1984",
        isbn="9780451524935",
        description="A dystopian novel set in a totalitarian society.",
        publication_date=date(1949, 6, 8),
        page_count=328,
        price=Decimal("12.99"),
        authors=[sample_author],
        genres=[sample_genre],
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


@pytest.fixture
def multiple_books(
    db_session: Session,
    sample_author: Author,
    sample_genre: Genre,
) -> list[Book]:
    """Create multiple books for pagination testing."""
    books = []
    for i in range(15):  # More than default page size
        book = Book(
            title=f"Test Book {i + 1}",
            isbn=f"978045152493{i}" if i < 10 else None,
            description=f"Description for book {i + 1}",
            page_count=100 + i * 10,
            price=Decimal(f"{10 + i}.99"),
        )
        if i % 2 == 0:
            book.authors = [sample_author]
        if i % 3 == 0:
            book.genres = [sample_genre]
        books.append(book)
        db_session.add(book)

    db_session.commit()
    for book in books:
        db_session.refresh(book)

    return books


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password=hash_password("SecurePass123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_user(db_session: Session) -> User:
    """Create a second user for testing ownership scenarios."""
    user = User(
        email="seconduser@example.com",
        username="seconduser",
        hashed_password=hash_password("SecurePass456"),
        full_name="Second User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superuser(db_session: Session) -> User:
    """Create a superuser for testing admin scenarios."""
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("AdminPass123"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_review(
    db_session: Session,
    sample_book: Book,
    sample_user: User,
) -> Review:
    """Create a sample review for testing."""
    review = Review(
        book_id=sample_book.id,
        user_id=sample_user.id,
        rating=4,
        title="Great book!",
        content="I really enjoyed reading this book.",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review
