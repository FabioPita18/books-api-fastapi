"""
Tests for Search and Filtering Endpoints

Tests the search functionality added in Phase 2A:
- General search across title and author
- Individual filters (title, author, genre, year range, price range)
- Combined filters
- Pagination with filters
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import status

from app.models import Author, Book, Genre


class TestBookSearch:
    """Tests for GET /api/v1/books/search endpoint."""

    @pytest.fixture
    def search_data(self, db_session):
        """Create diverse test data for search testing."""
        # Create authors
        orwell = Author(name="George Orwell", bio="English novelist")
        hemingway = Author(name="Ernest Hemingway", bio="American novelist")
        tolkien = Author(name="J.R.R. Tolkien", bio="English writer")

        db_session.add_all([orwell, hemingway, tolkien])
        db_session.commit()

        # Create genres
        fiction = Genre(name="Fiction", description="Literary fiction")
        scifi = Genre(name="Science Fiction", description="Sci-fi books")
        fantasy = Genre(name="Fantasy", description="Fantasy novels")

        db_session.add_all([fiction, scifi, fantasy])
        db_session.commit()

        # Create books with various attributes
        books = [
            Book(
                title="1984",
                isbn="9780451524935",
                publication_date=date(1949, 6, 8),
                page_count=328,
                price=Decimal("12.99"),
                authors=[orwell],
                genres=[fiction, scifi],
            ),
            Book(
                title="Animal Farm",
                isbn="9780451526342",
                publication_date=date(1945, 8, 17),
                page_count=112,
                price=Decimal("9.99"),
                authors=[orwell],
                genres=[fiction],
            ),
            Book(
                title="The Old Man and the Sea",
                isbn="9780684801223",
                publication_date=date(1952, 9, 1),
                page_count=127,
                price=Decimal("14.99"),
                authors=[hemingway],
                genres=[fiction],
            ),
            Book(
                title="The Hobbit",
                isbn="9780547928227",
                publication_date=date(1937, 9, 21),
                page_count=310,
                price=Decimal("15.99"),
                authors=[tolkien],
                genres=[fantasy],
            ),
            Book(
                title="The Lord of the Rings",
                isbn="9780544003415",
                publication_date=date(1954, 7, 29),
                page_count=1178,
                price=Decimal("29.99"),
                authors=[tolkien],
                genres=[fantasy],
            ),
        ]

        for book in books:
            db_session.add(book)
        db_session.commit()

        for book in books:
            db_session.refresh(book)

        return {
            "authors": {"orwell": orwell, "hemingway": hemingway, "tolkien": tolkien},
            "genres": {"fiction": fiction, "scifi": scifi, "fantasy": fantasy},
            "books": books,
        }

    def test_search_by_title(self, client, search_data):
        """Test searching books by title."""
        response = client.get("/api/v1/books/search?title=1984")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "1984"

    def test_search_by_title_partial_match(self, client, search_data):
        """Test partial title matching (case-insensitive)."""
        response = client.get("/api/v1/books/search?title=the")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should match "The Old Man...", "The Hobbit", "The Lord..."
        assert data["total"] == 3

    def test_search_by_author(self, client, search_data):
        """Test filtering books by author name."""
        response = client.get("/api/v1/books/search?author=orwell")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        titles = [book["title"] for book in data["items"]]
        assert "1984" in titles
        assert "Animal Farm" in titles

    def test_search_by_author_partial_match(self, client, search_data):
        """Test partial author name matching."""
        response = client.get("/api/v1/books/search?author=tolkien")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2

    def test_search_by_genre_id(self, client, search_data):
        """Test filtering books by genre ID."""
        fantasy_id = search_data["genres"]["fantasy"].id
        response = client.get(f"/api/v1/books/search?genre_id={fantasy_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        titles = [book["title"] for book in data["items"]]
        assert "The Hobbit" in titles
        assert "The Lord of the Rings" in titles

    def test_search_by_year_range(self, client, search_data):
        """Test filtering books by publication year range."""
        # Books published between 1950 and 1960
        response = client.get("/api/v1/books/search?min_year=1950&max_year=1960")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        titles = [book["title"] for book in data["items"]]
        assert "The Old Man and the Sea" in titles  # 1952
        assert "The Lord of the Rings" in titles  # 1954

    def test_search_by_min_year(self, client, search_data):
        """Test filtering books by minimum publication year."""
        response = client.get("/api/v1/books/search?min_year=1950")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 1952 and 1954 books
        assert data["total"] == 2

    def test_search_by_max_year(self, client, search_data):
        """Test filtering books by maximum publication year."""
        response = client.get("/api/v1/books/search?max_year=1945")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 1937 and 1945 books
        assert data["total"] == 2

    def test_search_by_price_range(self, client, search_data):
        """Test filtering books by price range."""
        response = client.get("/api/v1/books/search?min_price=10&max_price=15")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Books with price between 10.00 and 15.00
        for book in data["items"]:
            price = float(book["price"])
            assert 10.0 <= price <= 15.0

    def test_search_combined_filters(self, client, search_data):
        """Test combining multiple filters."""
        # Fiction books published before 1950
        fiction_id = search_data["genres"]["fiction"].id
        response = client.get(
            f"/api/v1/books/search?genre_id={fiction_id}&max_year=1950"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 1984 (1949) and Animal Farm (1945) are fiction before 1950
        assert data["total"] == 2

    def test_search_no_results(self, client, search_data):
        """Test search with no matching results."""
        response = client.get("/api/v1/books/search?title=nonexistent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_search_with_pagination(self, client, search_data):
        """Test search results with pagination."""
        response = client.get("/api/v1/books/search?per_page=2&page=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["per_page"] == 2
        assert data["page"] == 1
        assert data["total"] == 5
        assert data["pages"] == 3

    def test_general_search_query(self, client, search_data):
        """Test general search (q parameter) searches both title and author."""
        # Search for "orwell" should find books by author Orwell
        response = client.get("/api/v1/books/search?q=orwell")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2  # 1984 and Animal Farm

        # Search for "hobbit" should find the book by title
        response = client.get("/api/v1/books/search?q=hobbit")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "The Hobbit"


class TestBookListFilters:
    """Tests for filtering on GET /api/v1/books/ endpoint."""

    @pytest.fixture
    def filter_data(self, db_session):
        """Create test data for filter testing."""
        author = Author(name="Test Author")
        genre = Genre(name="Test Genre")
        db_session.add_all([author, genre])
        db_session.commit()

        books = [
            Book(
                title="Cheap Book",
                price=Decimal("5.99"),
                authors=[author],
                genres=[genre],
            ),
            Book(
                title="Medium Book",
                price=Decimal("15.99"),
                authors=[author],
            ),
            Book(
                title="Expensive Book",
                price=Decimal("49.99"),
                genres=[genre],
            ),
        ]

        for book in books:
            db_session.add(book)
        db_session.commit()

        return {"author": author, "genre": genre, "books": books}

    def test_list_with_title_filter(self, client, filter_data):
        """Test listing books with title filter."""
        response = client.get("/api/v1/books/?title=cheap")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Cheap Book"

    def test_list_with_price_filter(self, client, filter_data):
        """Test listing books with price filter."""
        response = client.get("/api/v1/books/?min_price=10&max_price=20")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Medium Book"

    def test_list_without_filters(self, client, filter_data):
        """Test listing all books without filters."""
        response = client.get("/api/v1/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3


class TestAuthorBooks:
    """Tests for GET /api/v1/authors/{author_id}/books endpoint."""

    @pytest.fixture
    def author_books_data(self, db_session):
        """Create author with multiple books."""
        author = Author(name="Prolific Author")
        db_session.add(author)
        db_session.commit()

        books = [
            Book(title=f"Book {i}", authors=[author])
            for i in range(5)
        ]
        for book in books:
            db_session.add(book)
        db_session.commit()

        for book in books:
            db_session.refresh(book)

        return {"author": author, "books": books}

    def test_get_author_books(self, client, author_books_data):
        """Test getting all books by an author."""
        author_id = author_books_data["author"].id
        response = client.get(f"/api/v1/authors/{author_id}/books")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5

    def test_get_author_books_pagination(self, client, author_books_data):
        """Test pagination for author's books."""
        author_id = author_books_data["author"].id
        response = client.get(f"/api/v1/authors/{author_id}/books?per_page=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    def test_get_author_books_not_found(self, client):
        """Test getting books for non-existent author."""
        response = client.get("/api/v1/authors/99999/books")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGenreBooks:
    """Tests for GET /api/v1/genres/{genre_id}/books endpoint."""

    @pytest.fixture
    def genre_books_data(self, db_session):
        """Create genre with multiple books."""
        genre = Genre(name="Popular Genre")
        db_session.add(genre)
        db_session.commit()

        books = [
            Book(title=f"Genre Book {i}", genres=[genre])
            for i in range(4)
        ]
        for book in books:
            db_session.add(book)
        db_session.commit()

        for book in books:
            db_session.refresh(book)

        return {"genre": genre, "books": books}

    def test_get_genre_books(self, client, genre_books_data):
        """Test getting all books in a genre."""
        genre_id = genre_books_data["genre"].id
        response = client.get(f"/api/v1/genres/{genre_id}/books")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 4

    def test_get_genre_books_pagination(self, client, genre_books_data):
        """Test pagination for genre's books."""
        genre_id = genre_books_data["genre"].id
        response = client.get(f"/api/v1/genres/{genre_id}/books?per_page=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pages"] == 2

    def test_get_genre_books_not_found(self, client):
        """Test getting books for non-existent genre."""
        response = client.get("/api/v1/genres/99999/books")

        assert response.status_code == status.HTTP_404_NOT_FOUND
