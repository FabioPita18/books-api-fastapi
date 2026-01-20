"""
Tests for Advanced Search (Phase 4C)

Tests the search endpoint with PostgreSQL fallback:
- Full-text search across title, description, authors
- Filter by genres, year range, rating, price
- Pagination
- Faceted results

Note: These tests use PostgreSQL fallback since Elasticsearch
is not available in the test environment.
"""
# ruff: noqa: I001
from datetime import date
from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Author, Book, Genre


# =============================================================================
# Test Data Setup
# =============================================================================


def create_test_books(db_session: Session) -> dict:
    """Create a diverse set of books for search testing."""
    # Create authors
    orwell = Author(name="George Orwell", bio="English novelist")
    asimov = Author(name="Isaac Asimov", bio="Science fiction author")
    tolkien = Author(name="J.R.R. Tolkien", bio="Fantasy author")
    db_session.add_all([orwell, asimov, tolkien])

    # Create genres
    scifi = Genre(name="Science Fiction", description="Futuristic fiction")
    dystopian = Genre(name="Dystopian", description="Dark futures")
    fantasy = Genre(name="Fantasy", description="Magical worlds")
    classic = Genre(name="Classic", description="Timeless literature")
    db_session.add_all([scifi, dystopian, fantasy, classic])

    db_session.flush()

    # Create books with various attributes
    books = [
        Book(
            title="1984",
            isbn="9780451524935",
            description="A dystopian novel about totalitarian society and surveillance.",
            publication_date=date(1949, 6, 8),
            page_count=328,
            price=Decimal("12.99"),
            average_rating=Decimal("4.50"),
            review_count=100,
            authors=[orwell],
            genres=[dystopian, classic],
        ),
        Book(
            title="Animal Farm",
            isbn="9780451526342",
            description="A satirical allegory about Soviet totalitarianism.",
            publication_date=date(1945, 8, 17),
            page_count=112,
            price=Decimal("9.99"),
            average_rating=Decimal("4.30"),
            review_count=80,
            authors=[orwell],
            genres=[dystopian, classic],
        ),
        Book(
            title="Foundation",
            isbn="9780553293357",
            description="The first novel in the Foundation series about galactic empire.",
            publication_date=date(1951, 5, 1),
            page_count=244,
            price=Decimal("15.99"),
            average_rating=Decimal("4.70"),
            review_count=150,
            authors=[asimov],
            genres=[scifi],
        ),
        Book(
            title="I, Robot",
            isbn="9780553382563",
            description="A collection of robot stories exploring artificial intelligence.",
            publication_date=date(1950, 12, 2),
            page_count=224,
            price=Decimal("14.99"),
            average_rating=Decimal("4.20"),
            review_count=90,
            authors=[asimov],
            genres=[scifi],
        ),
        Book(
            title="The Hobbit",
            isbn="9780547928227",
            description="A fantasy adventure about Bilbo Baggins and a dragon.",
            publication_date=date(1937, 9, 21),
            page_count=310,
            price=Decimal("16.99"),
            average_rating=Decimal("4.80"),
            review_count=200,
            authors=[tolkien],
            genres=[fantasy, classic],
        ),
        Book(
            title="The Lord of the Rings",
            isbn="9780544003415",
            description="An epic fantasy trilogy about the One Ring.",
            publication_date=date(1954, 7, 29),
            page_count=1178,
            price=Decimal("29.99"),
            average_rating=Decimal("4.90"),
            review_count=250,
            authors=[tolkien],
            genres=[fantasy, classic],
        ),
    ]

    db_session.add_all(books)
    db_session.commit()

    for book in books:
        db_session.refresh(book)

    return {
        "books": books,
        "authors": {"orwell": orwell, "asimov": asimov, "tolkien": tolkien},
        "genres": {"scifi": scifi, "dystopian": dystopian, "fantasy": fantasy, "classic": classic},
    }


# =============================================================================
# Basic Search Tests
# =============================================================================


class TestBasicSearch:
    """Tests for basic search functionality."""

    def test_search_no_query(self, client: TestClient, db_session: Session):
        """Test search without query returns all books."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 6
        assert len(data["items"]) == 6
        assert "facets" in data

    def test_search_by_title(self, client: TestClient, db_session: Session):
        """Test search by book title."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"q": "1984"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        titles = [item["title"] for item in data["items"]]
        assert "1984" in titles

    def test_search_by_description(self, client: TestClient, db_session: Session):
        """Test search finds books by description content."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"q": "dystopian"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        # Should find 1984 and Animal Farm (both have dystopian in description/genre)

    def test_search_by_author_name(self, client: TestClient, db_session: Session):
        """Test search finds books by author name."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"q": "Orwell"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        # Should find books by George Orwell

    def test_search_case_insensitive(self, client: TestClient, db_session: Session):
        """Test search is case-insensitive."""
        create_test_books(db_session)

        response1 = client.get("/api/v1/search", params={"q": "hobbit"})
        response2 = client.get("/api/v1/search", params={"q": "HOBBIT"})
        response3 = client.get("/api/v1/search", params={"q": "Hobbit"})

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK

        # All should return the same results
        assert response1.json()["total"] == response2.json()["total"]
        assert response2.json()["total"] == response3.json()["total"]

    def test_search_no_results(self, client: TestClient, db_session: Session):
        """Test search with no matching results."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"q": "xyznonexistent"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# =============================================================================
# Filter Tests
# =============================================================================


class TestSearchFilters:
    """Tests for search filters."""

    def test_filter_by_genre(self, client: TestClient, db_session: Session):
        """Test filtering by genre name."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"genres": "Science Fiction"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2  # Foundation and I, Robot
        for item in data["items"]:
            assert "Science Fiction" in item["genres"]

    def test_filter_by_multiple_genres(self, client: TestClient, db_session: Session):
        """Test filtering by multiple genres."""
        create_test_books(db_session)

        response = client.get(
            "/api/v1/search",
            params={"genres": ["Fantasy", "Dystopian"]},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return books that have Fantasy OR Dystopian
        assert data["total"] >= 2

    def test_filter_by_min_year(self, client: TestClient, db_session: Session):
        """Test filtering by minimum publication year."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"min_year": 1950})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["publication_year"]:
                assert item["publication_year"] >= 1950

    def test_filter_by_max_year(self, client: TestClient, db_session: Session):
        """Test filtering by maximum publication year."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"max_year": 1950})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["publication_year"]:
                assert item["publication_year"] <= 1950

    def test_filter_by_year_range(self, client: TestClient, db_session: Session):
        """Test filtering by year range."""
        create_test_books(db_session)

        response = client.get(
            "/api/v1/search",
            params={"min_year": 1945, "max_year": 1955},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["publication_year"]:
                assert 1945 <= item["publication_year"] <= 1955

    def test_filter_by_min_rating(self, client: TestClient, db_session: Session):
        """Test filtering by minimum rating."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"min_rating": 4.5})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["average_rating"]:
                assert item["average_rating"] >= 4.5

    def test_filter_by_price_range(self, client: TestClient, db_session: Session):
        """Test filtering by price range."""
        create_test_books(db_session)

        response = client.get(
            "/api/v1/search",
            params={"min_price": 10.0, "max_price": 20.0},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["price"]:
                assert 10.0 <= item["price"] <= 20.0

    def test_combined_filters(self, client: TestClient, db_session: Session):
        """Test combining search query with filters."""
        create_test_books(db_session)

        response = client.get(
            "/api/v1/search",
            params={
                "q": "ring",
                "genres": "Fantasy",
                "min_rating": 4.0,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should find "The Lord of the Rings"
        assert data["total"] >= 1


# =============================================================================
# Pagination Tests
# =============================================================================


class TestSearchPagination:
    """Tests for search pagination."""

    def test_pagination_default(self, client: TestClient, db_session: Session):
        """Test default pagination values."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 20  # Default size

    def test_pagination_custom_size(self, client: TestClient, db_session: Session):
        """Test custom page size."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"size": 2})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["size"] == 2

    def test_pagination_second_page(self, client: TestClient, db_session: Session):
        """Test fetching second page."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"page": 2, "size": 2})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2

    def test_pagination_total_pages(self, client: TestClient, db_session: Session):
        """Test total pages calculation."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"size": 2})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pages"] == 3  # 6 books / 2 per page = 3 pages

    def test_pagination_beyond_results(self, client: TestClient, db_session: Session):
        """Test requesting page beyond available results."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"page": 100, "size": 10})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []


# =============================================================================
# Facets Tests
# =============================================================================


class TestSearchFacets:
    """Tests for search facets (aggregations)."""

    def test_facets_returned(self, client: TestClient, db_session: Session):
        """Test that facets are returned in response."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "facets" in data
        facets = data["facets"]
        assert "genres" in facets
        assert "years" in facets
        assert "ratings" in facets

    def test_genre_facets(self, client: TestClient, db_session: Session):
        """Test genre facets have correct structure."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        genre_facets = data["facets"]["genres"]

        # Should have genre facets with name and count
        assert len(genre_facets) > 0
        for facet in genre_facets:
            assert "name" in facet
            assert "count" in facet
            assert isinstance(facet["count"], int)

    def test_year_facets(self, client: TestClient, db_session: Session):
        """Test year facets have correct structure."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        year_facets = data["facets"]["years"]

        # Should have year facets with year and count
        for facet in year_facets:
            assert "year" in facet
            assert "count" in facet
            assert isinstance(facet["year"], int)

    def test_rating_facets(self, client: TestClient, db_session: Session):
        """Test rating facets have correct structure."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        rating_facets = data["facets"]["ratings"]

        # Should have rating range facets
        for facet in rating_facets:
            assert "range" in facet
            assert "count" in facet


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestSearchResponseStructure:
    """Tests for search response structure."""

    def test_response_structure(self, client: TestClient, db_session: Session):
        """Test complete response structure."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Required fields
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert "facets" in data
        assert "fallback" in data

    def test_book_item_structure(self, client: TestClient, db_session: Session):
        """Test book item structure in results."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for item in data["items"]:
            assert "id" in item
            assert "title" in item
            assert "authors" in item
            assert "genres" in item
            assert isinstance(item["authors"], list)
            assert isinstance(item["genres"], list)

    def test_fallback_indicator(self, client: TestClient, db_session: Session):
        """Test fallback indicator when ES is unavailable."""
        create_test_books(db_session)

        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # In tests, ES is not available, so fallback should be true
        assert data["fallback"] is True


# =============================================================================
# Edge Cases
# =============================================================================


class TestSearchEdgeCases:
    """Tests for search edge cases."""

    def test_empty_database(self, client: TestClient):
        """Test search with empty database."""
        response = client.get("/api/v1/search")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_special_characters_in_query(self, client: TestClient, db_session: Session):
        """Test search with special characters."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"q": "J.R.R."})

        assert response.status_code == status.HTTP_200_OK
        # Should not error, may or may not find results

    def test_very_long_query(self, client: TestClient, db_session: Session):
        """Test search with very long query."""
        create_test_books(db_session)

        long_query = "a" * 200  # Max length is 200
        response = client.get("/api/v1/search", params={"q": long_query})

        assert response.status_code == status.HTTP_200_OK

    def test_query_too_long(self, client: TestClient, db_session: Session):
        """Test search with query exceeding max length."""
        create_test_books(db_session)

        long_query = "a" * 201  # Exceeds max length
        response = client.get("/api/v1/search", params={"q": long_query})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_page_number(self, client: TestClient, db_session: Session):
        """Test search with invalid page number."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"page": 0})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_size(self, client: TestClient, db_session: Session):
        """Test search with invalid page size."""
        create_test_books(db_session)

        response = client.get("/api/v1/search", params={"size": 101})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
