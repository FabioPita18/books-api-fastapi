"""
Test Suite for Books API

This package contains all tests for the Books API.

Test Organization:
- conftest.py: Shared fixtures (test database, client, sample data)
- test_books.py: Tests for /api/v1/books endpoints
- test_authors.py: Tests for /api/v1/authors endpoints
- test_genres.py: Tests for /api/v1/genres endpoints

Running Tests:
    # Run all tests
    pytest

    # Run with coverage
    pytest --cov=app --cov-report=html

    # Run specific file
    pytest tests/test_books.py

    # Run specific test
    pytest tests/test_books.py::test_create_book

    # Run with verbose output
    pytest -v
"""
