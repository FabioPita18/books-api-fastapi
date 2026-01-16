"""
Database Configuration Module

This module sets up SQLAlchemy 2.0 with PostgreSQL for the Books API.

SQLAlchemy 2.0 vs 1.x
=====================
SQLAlchemy 2.0 introduced significant changes:
1. Native async support (we're using sync for simplicity)
2. New declarative syntax with mapped_column()
3. Type hints integration
4. More explicit session management

We're using SYNCHRONOUS SQLAlchemy because:
- Simpler to understand and debug
- PostgreSQL with psycopg2 is battle-tested
- Async provides minimal benefit for simple CRUD APIs
- Easier to learn FastAPI patterns first

For high-concurrency apps, you'd switch to async with asyncpg.

Session Management Pattern
==========================
We use the "session per request" pattern:
1. Request arrives → create a new session
2. Use session for all database operations in that request
3. Commit on success, rollback on failure
4. Close session when request ends

This is implemented using FastAPI's dependency injection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

# Get settings instance
settings = get_settings()


# =============================================================================
# Database Engine
# =============================================================================
# The engine is the starting point for any SQLAlchemy application.
# It's a "home base" for the actual database and its DBAPI (psycopg2).
#
# Key parameters:
# - pool_size: Number of connections to keep open permanently
# - max_overflow: How many extra connections can be created during high load
# - pool_pre_ping: Test connection health before using (prevents stale connections)
# - echo: Log all SQL statements (useful for debugging, disable in production)

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Verify connections are alive before using
    echo=settings.debug,  # Log SQL in debug mode
)


# =============================================================================
# Session Factory
# =============================================================================
# sessionmaker creates a factory for database sessions.
# Each call to SessionLocal() creates a new session.
#
# Parameters:
# - autocommit=False: We control when to commit (explicit is better than implicit)
# - autoflush=False: Don't auto-flush before queries (more predictable behavior)
# - bind=engine: Connect sessions to our database engine

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =============================================================================
# Base Model Class
# =============================================================================
# All SQLAlchemy models will inherit from this base class.
# This is the SQLAlchemy 2.0 way to create a declarative base.
#
# Why DeclarativeBase?
# - Provides the Mapper registry for model discovery
# - Enables relationship() and other ORM features
# - Alembic uses this to find all models for migrations

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    All your models should inherit from this class:

        class Book(Base):
            __tablename__ = "books"
            ...

    The Base class:
    1. Provides the SQLAlchemy mapper registry
    2. Enables table/model relationship tracking
    3. Is used by Alembic to discover models for migrations
    """
    pass


# =============================================================================
# Dependency Injection
# =============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    This is a generator function (uses yield) that:
    1. Creates a new database session
    2. Yields it to the route handler
    3. Closes it when the request ends (in the finally block)

    WHY Generator with yield?
    ========================
    FastAPI's Depends() works with generators to manage resources:
    - Code before yield: Setup (create session)
    - yield: Provide the session to the route
    - Code after yield: Cleanup (close session)

    The finally block ensures cleanup happens even if an exception occurs.

    Usage in Routes:
        from fastapi import Depends
        from app.database import get_db

        @router.get("/books/")
        def get_books(db: Session = Depends(get_db)):
            return db.query(Book).all()

    The Session type hint tells FastAPI and your IDE what type db is,
    enabling autocomplete and type checking.

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Utility Functions
# =============================================================================
def create_tables() -> None:
    """
    Create all database tables.

    This is useful for:
    - Development: Quick table creation without migrations
    - Testing: Create tables in test database

    WARNING: In production, use Alembic migrations instead!
    This function doesn't track schema changes or allow rollbacks.

    Usage:
        from app.database import create_tables
        create_tables()
    """
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """
    Drop all database tables.

    DANGER: This deletes all data! Only use in:
    - Development: Reset database to clean state
    - Testing: Clean up after tests

    NEVER use in production!
    """
    Base.metadata.drop_all(bind=engine)
