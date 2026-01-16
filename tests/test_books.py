"""
Tests for Books API Endpoints

This module tests all CRUD operations for the /api/v1/books endpoints.

TEST NAMING CONVENTION:
- test_<action>_<scenario>
- Examples: test_create_book_success, test_get_book_not_found

TESTING BEST PRACTICES:
1. Arrange: Set up test data and conditions
2. Act: Perform the action being tested
3. Assert: Verify the expected outcome

Each test should:
- Test one thing (single assertion concept)
- Be independent (no reliance on other tests)
- Be descriptive (name explains what's tested)
"""


import pytest
from fastapi import status


class TestListBooks:
    """Tests for GET /api/v1/books/ endpoint."""

    def test_list_books_empty(self, client):
        """Test listing books when database is empty."""
        response = client.get("/api/v1/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 0

    def test_list_books_with_data(self, client, sample_book):
        """Test listing books returns expected data."""
        response = client.get("/api/v1/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "1984"

    def test_list_books_pagination(self, client, multiple_books):
        """Test pagination works correctly."""
        # First page
        response = client.get("/api/v1/books/?page=1&per_page=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["pages"] == 3

        # Second page
        response = client.get("/api/v1/books/?page=2&per_page=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2

    def test_list_books_invalid_pagination(self, client):
        """Test that invalid pagination params are rejected."""
        # Page must be >= 1
        response = client.get("/api/v1/books/?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # per_page must be <= 100
        response = client.get("/api/v1/books/?per_page=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetBook:
    """Tests for GET /api/v1/books/{book_id} endpoint."""

    def test_get_book_success(self, client, sample_book):
        """Test getting a book by ID."""
        response = client.get(f"/api/v1/books/{sample_book.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_book.id
        assert data["title"] == "1984"
        assert data["isbn"] == "9780451524935"
        assert len(data["authors"]) == 1
        assert data["authors"][0]["name"] == "George Orwell"

    def test_get_book_not_found(self, client):
        """Test getting a non-existent book returns 404."""
        response = client.get("/api/v1/books/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestCreateBook:
    """Tests for POST /api/v1/books/ endpoint."""

    def test_create_book_minimal(self, client):
        """Test creating a book with only required fields."""
        book_data = {"title": "New Book"}

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "New Book"
        assert data["id"] is not None
        assert data["authors"] == []
        assert data["genres"] == []

    def test_create_book_full(self, client, sample_author, sample_genre):
        """Test creating a book with all fields."""
        book_data = {
            "title": "Complete Book",
            "isbn": "978-0-13-468599-1",
            "description": "A complete book with all fields",
            "publication_date": "2024-01-15",
            "page_count": 500,
            "price": "29.99",
            "author_ids": [sample_author.id],
            "genre_ids": [sample_genre.id],
        }

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Complete Book"
        assert data["isbn"] == "9780134685991"  # Cleaned ISBN
        assert data["page_count"] == 500
        assert len(data["authors"]) == 1
        assert len(data["genres"]) == 1

    def test_create_book_invalid_isbn(self, client):
        """Test that invalid ISBN is rejected."""
        book_data = {
            "title": "Invalid ISBN Book",
            "isbn": "invalid-isbn",
        }

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_empty_title(self, client):
        """Test that empty title is rejected."""
        book_data = {"title": "   "}  # Whitespace only

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_invalid_author_id(self, client):
        """Test that non-existent author ID is rejected."""
        book_data = {
            "title": "Book with Invalid Author",
            "author_ids": [99999],
        }

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Authors not found" in response.json()["detail"]

    def test_create_book_negative_price(self, client):
        """Test that negative price is rejected."""
        book_data = {
            "title": "Negative Price Book",
            "price": "-10.00",
        }

        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateBook:
    """Tests for PUT /api/v1/books/{book_id} endpoint."""

    def test_update_book_title(self, client, sample_book):
        """Test updating only the title."""
        update_data = {"title": "Nineteen Eighty-Four"}

        response = client.put(
            f"/api/v1/books/{sample_book.id}",
            json=update_data,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Nineteen Eighty-Four"
        # Other fields should remain unchanged
        assert data["isbn"] == "9780451524935"

    def test_update_book_not_found(self, client):
        """Test updating a non-existent book returns 404."""
        update_data = {"title": "Updated Title"}

        response = client.put("/api/v1/books/99999", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_book_authors(self, client, sample_book, db_session):
        """Test updating book authors."""
        # Create a new author
        from app.models import Author

        new_author = Author(name="New Author")
        db_session.add(new_author)
        db_session.commit()
        db_session.refresh(new_author)

        update_data = {"author_ids": [new_author.id]}

        response = client.put(
            f"/api/v1/books/{sample_book.id}",
            json=update_data,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["authors"]) == 1
        assert data["authors"][0]["name"] == "New Author"


class TestDeleteBook:
    """Tests for DELETE /api/v1/books/{book_id} endpoint."""

    def test_delete_book_success(self, client, sample_book):
        """Test deleting a book successfully."""
        response = client.delete(f"/api/v1/books/{sample_book.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify book is deleted
        get_response = client.get(f"/api/v1/books/{sample_book.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_book_not_found(self, client):
        """Test deleting a non-existent book returns 404."""
        response = client.delete("/api/v1/books/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestBookValidation:
    """Tests for book data validation."""

    @pytest.mark.parametrize(
        "isbn,valid",
        [
            ("978-0-13-468599-1", True),   # ISBN-13 with hyphens
            ("9780134685991", True),        # ISBN-13 without hyphens
            ("0-06-112008-1", True),        # ISBN-10 with hyphens
            ("006112008X", True),           # ISBN-10 with X
            ("123", False),                 # Too short
            ("12345678901234", False),      # Too long
            ("978-0-13-XXXX-1", False),     # Invalid characters
        ],
    )
    def test_isbn_validation(self, client, isbn, valid):
        """Test various ISBN formats."""
        book_data = {"title": "Test Book", "isbn": isbn}

        response = client.post("/api/v1/books/", json=book_data)

        if valid:
            assert response.status_code == status.HTTP_201_CREATED
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "page_count,valid",
        [
            (100, True),
            (1, True),
            (50000, True),
            (0, False),     # Must be > 0
            (-1, False),    # Must be positive
            (50001, False), # Too large
        ],
    )
    def test_page_count_validation(self, client, page_count, valid):
        """Test page count validation."""
        book_data = {"title": "Test Book", "page_count": page_count}

        response = client.post("/api/v1/books/", json=book_data)

        if valid:
            assert response.status_code == status.HTTP_201_CREATED
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
