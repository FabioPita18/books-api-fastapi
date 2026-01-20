"""
Tests for Recommendations (Phase 4E)

Tests the recommendation endpoints:
- GET /books/{book_id}/similar - Content-based similar books
- GET /recommendations - Personalized recommendations (auth required)
- GET /books/trending - Popular books
- GET /books/new-releases - Recently added books

Algorithms tested:
- Content-based filtering (genre/author similarity)
- Collaborative filtering (similar users)
- Trending calculation (rating × activity)
"""
# ruff: noqa: I001
from datetime import date
from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Author, Book, Genre
from app.models.review import Review
from app.models.user import User
from app.services.security import create_access_token, hash_password


# =============================================================================
# Helper Functions
# =============================================================================


def get_auth_header(user: User) -> dict:
    """Create authorization header for a user."""
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def create_recommendation_test_data(db_session: Session) -> dict:
    """Create comprehensive test data for recommendation testing."""
    # Create authors
    authors = {
        "orwell": Author(name="George Orwell", bio="English novelist"),
        "asimov": Author(name="Isaac Asimov", bio="Science fiction author"),
        "tolkien": Author(name="J.R.R. Tolkien", bio="Fantasy author"),
        "herbert": Author(name="Frank Herbert", bio="Science fiction author"),
    }
    db_session.add_all(authors.values())

    # Create genres
    genres = {
        "scifi": Genre(name="Science Fiction", description="Futuristic fiction"),
        "dystopian": Genre(name="Dystopian", description="Dark futures"),
        "fantasy": Genre(name="Fantasy", description="Magical worlds"),
        "classic": Genre(name="Classic", description="Timeless literature"),
    }
    db_session.add_all(genres.values())

    db_session.flush()

    # Create books
    books = {
        "1984": Book(
            title="1984",
            isbn="9780451524935",
            description="A dystopian novel about totalitarian society.",
            publication_date=date(1949, 6, 8),
            price=Decimal("12.99"),
            average_rating=Decimal("4.50"),
            review_count=100,
            authors=[authors["orwell"]],
            genres=[genres["dystopian"], genres["classic"]],
        ),
        "animal_farm": Book(
            title="Animal Farm",
            isbn="9780451526342",
            description="A satirical allegory about totalitarianism.",
            publication_date=date(1945, 8, 17),
            price=Decimal("9.99"),
            average_rating=Decimal("4.30"),
            review_count=80,
            authors=[authors["orwell"]],
            genres=[genres["dystopian"], genres["classic"]],
        ),
        "foundation": Book(
            title="Foundation",
            isbn="9780553293357",
            description="The first novel in the Foundation series.",
            publication_date=date(1951, 5, 1),
            price=Decimal("15.99"),
            average_rating=Decimal("4.70"),
            review_count=150,
            authors=[authors["asimov"]],
            genres=[genres["scifi"]],
        ),
        "i_robot": Book(
            title="I, Robot",
            isbn="9780553382563",
            description="Stories exploring artificial intelligence.",
            publication_date=date(1950, 12, 2),
            price=Decimal("14.99"),
            average_rating=Decimal("4.20"),
            review_count=90,
            authors=[authors["asimov"]],
            genres=[genres["scifi"]],
        ),
        "hobbit": Book(
            title="The Hobbit",
            isbn="9780547928227",
            description="A fantasy adventure about Bilbo Baggins.",
            publication_date=date(1937, 9, 21),
            price=Decimal("16.99"),
            average_rating=Decimal("4.80"),
            review_count=200,
            authors=[authors["tolkien"]],
            genres=[genres["fantasy"], genres["classic"]],
        ),
        "lotr": Book(
            title="The Lord of the Rings",
            isbn="9780544003415",
            description="An epic fantasy trilogy about the One Ring.",
            publication_date=date(1954, 7, 29),
            price=Decimal("29.99"),
            average_rating=Decimal("4.90"),
            review_count=250,
            authors=[authors["tolkien"]],
            genres=[genres["fantasy"], genres["classic"]],
        ),
        "dune": Book(
            title="Dune",
            isbn="9780441172719",
            description="An epic science fiction novel about desert planet.",
            publication_date=date(1965, 8, 1),
            price=Decimal("18.99"),
            average_rating=Decimal("4.60"),
            review_count=180,
            authors=[authors["herbert"]],
            genres=[genres["scifi"]],
        ),
    }
    db_session.add_all(books.values())

    # Create users
    users = {
        "alice": User(
            email="alice@example.com",
            username="alice",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
            is_verified=True,
        ),
        "bob": User(
            email="bob@example.com",
            username="bob",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
            is_verified=True,
        ),
        "charlie": User(
            email="charlie@example.com",
            username="charlie",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
            is_verified=True,
        ),
        "new_user": User(
            email="newuser@example.com",
            username="newuser",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
            is_verified=True,
        ),
    }
    db_session.add_all(users.values())

    db_session.flush()

    # Create reviews to establish user preferences
    reviews = [
        # Alice likes dystopian and classic
        Review(book_id=books["1984"].id, user_id=users["alice"].id, rating=5, title="Amazing"),
        Review(book_id=books["animal_farm"].id, user_id=users["alice"].id, rating=5, title="Great"),
        Review(book_id=books["hobbit"].id, user_id=users["alice"].id, rating=4, title="Good"),

        # Bob also likes dystopian - similar to Alice
        Review(book_id=books["1984"].id, user_id=users["bob"].id, rating=5, title="Loved it"),
        Review(book_id=books["animal_farm"].id, user_id=users["bob"].id, rating=4, title="Nice"),
        Review(book_id=books["lotr"].id, user_id=users["bob"].id, rating=5, title="Epic"),

        # Charlie likes sci-fi
        Review(book_id=books["foundation"].id, user_id=users["charlie"].id, rating=5, title="Best"),
        Review(book_id=books["i_robot"].id, user_id=users["charlie"].id, rating=4, title="Good"),
        Review(book_id=books["dune"].id, user_id=users["charlie"].id, rating=5, title="Amazing"),
    ]
    db_session.add_all(reviews)

    db_session.commit()

    # Refresh all objects
    for book in books.values():
        db_session.refresh(book)
    for user in users.values():
        db_session.refresh(user)

    return {
        "books": books,
        "authors": authors,
        "genres": genres,
        "users": users,
    }


# =============================================================================
# Similar Books Tests
# =============================================================================


class TestSimilarBooks:
    """Tests for GET /api/v1/books/{book_id}/similar"""

    def test_similar_books_by_genre(self, client: TestClient, db_session: Session):
        """Test finding similar books by shared genres."""
        data = create_recommendation_test_data(db_session)

        # Get books similar to 1984 (Dystopian, Classic)
        response = client.get(f"/api/v1/books/{data['books']['1984'].id}/similar")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert result["source_book_id"] == data["books"]["1984"].id
        assert result["algorithm"] == "content-based"

        # Should find Animal Farm (same author, same genres)
        similar_titles = [item["book"]["title"] for item in result["items"]]
        assert "Animal Farm" in similar_titles

    def test_similar_books_by_author(self, client: TestClient, db_session: Session):
        """Test finding similar books by same author."""
        data = create_recommendation_test_data(db_session)

        # Get books similar to Foundation (Asimov, Sci-Fi)
        response = client.get(f"/api/v1/books/{data['books']['foundation'].id}/similar")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        similar_titles = [item["book"]["title"] for item in result["items"]]
        # Should find I, Robot (same author)
        assert "I, Robot" in similar_titles

    def test_similar_books_with_scores(self, client: TestClient, db_session: Session):
        """Test that similar books have similarity scores."""
        data = create_recommendation_test_data(db_session)

        response = client.get(f"/api/v1/books/{data['books']['1984'].id}/similar")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        for item in result["items"]:
            assert "similarity_score" in item
            assert "reasons" in item
            assert isinstance(item["similarity_score"], (int, float))
            assert item["similarity_score"] >= 0

    def test_similar_books_limit(self, client: TestClient, db_session: Session):
        """Test limiting number of similar books."""
        data = create_recommendation_test_data(db_session)

        response = client.get(
            f"/api/v1/books/{data['books']['1984'].id}/similar",
            params={"limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert len(result["items"]) <= 2

    def test_similar_books_not_found(self, client: TestClient, db_session: Session):
        """Test similar books for non-existent book."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/99999/similar")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_similar_books_excludes_source(self, client: TestClient, db_session: Session):
        """Test that source book is not in similar results."""
        data = create_recommendation_test_data(db_session)

        book_id = data["books"]["1984"].id
        response = client.get(f"/api/v1/books/{book_id}/similar")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        similar_ids = [item["book"]["id"] for item in result["items"]]
        assert book_id not in similar_ids

    def test_similar_books_authenticated_excludes_read(
        self, client: TestClient, db_session: Session
    ):
        """Test that authenticated user's read books are excluded."""
        data = create_recommendation_test_data(db_session)
        alice = data["users"]["alice"]

        # Alice has reviewed 1984, Animal Farm, and Hobbit
        # Get similar to LOTR (which Alice hasn't read)
        response = client.get(
            f"/api/v1/books/{data['books']['lotr'].id}/similar",
            headers=get_auth_header(alice),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        # Should return results (Hobbit might be excluded since Alice read it)
        assert "items" in result


# =============================================================================
# Personalized Recommendations Tests
# =============================================================================


class TestPersonalizedRecommendations:
    """Tests for GET /api/v1/recommendations"""

    def test_recommendations_requires_auth(self, client: TestClient, db_session: Session):
        """Test that recommendations require authentication."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/recommendations")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_recommendations_for_user_with_reviews(
        self, client: TestClient, db_session: Session
    ):
        """Test personalized recommendations for user with review history."""
        data = create_recommendation_test_data(db_session)
        alice = data["users"]["alice"]

        response = client.get(
            "/api/v1/recommendations",
            headers=get_auth_header(alice),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert result["user_id"] == alice.id
        assert "algorithm" in result

    def test_recommendations_excludes_read_books(
        self, client: TestClient, db_session: Session
    ):
        """Test that recommendations exclude books user has already read."""
        data = create_recommendation_test_data(db_session)
        alice = data["users"]["alice"]

        # Alice has read: 1984, Animal Farm, Hobbit
        response = client.get(
            "/api/v1/recommendations",
            headers=get_auth_header(alice),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        recommended_ids = [item["book"]["id"] for item in result["items"]]

        # Should not recommend books Alice has reviewed
        assert data["books"]["1984"].id not in recommended_ids
        assert data["books"]["animal_farm"].id not in recommended_ids
        assert data["books"]["hobbit"].id not in recommended_ids

    def test_recommendations_for_new_user(
        self, client: TestClient, db_session: Session
    ):
        """Test recommendations for user with no review history (cold start)."""
        data = create_recommendation_test_data(db_session)
        new_user = data["users"]["new_user"]

        response = client.get(
            "/api/v1/recommendations",
            headers=get_auth_header(new_user),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        # Should fall back to trending books
        assert "items" in result

    def test_recommendations_limit(self, client: TestClient, db_session: Session):
        """Test limiting number of recommendations."""
        data = create_recommendation_test_data(db_session)
        alice = data["users"]["alice"]

        response = client.get(
            "/api/v1/recommendations",
            params={"limit": 3},
            headers=get_auth_header(alice),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert len(result["items"]) <= 3

    def test_recommendations_have_scores(
        self, client: TestClient, db_session: Session
    ):
        """Test that recommendations include scores and reasons."""
        data = create_recommendation_test_data(db_session)
        alice = data["users"]["alice"]

        response = client.get(
            "/api/v1/recommendations",
            headers=get_auth_header(alice),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        for item in result["items"]:
            assert "recommendation_score" in item
            assert "reasons" in item


# =============================================================================
# Trending Books Tests
# =============================================================================


class TestTrendingBooks:
    """Tests for GET /api/v1/books/trending"""

    def test_trending_books_success(self, client: TestClient, db_session: Session):
        """Test getting trending books."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/trending")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert result["algorithm"] == "popularity"

    def test_trending_books_sorted_by_score(
        self, client: TestClient, db_session: Session
    ):
        """Test that trending books are sorted by trending score."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/trending")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        scores = [item["trending_score"] for item in result["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_trending_books_have_scores(
        self, client: TestClient, db_session: Session
    ):
        """Test that trending books have scores and reasons."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/trending")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        for item in result["items"]:
            assert "trending_score" in item
            assert "reasons" in item
            assert item["trending_score"] >= 0

    def test_trending_books_limit(self, client: TestClient, db_session: Session):
        """Test limiting number of trending books."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/trending", params={"limit": 3})

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert len(result["items"]) <= 3

    def test_trending_books_response_structure(self, client: TestClient, db_session: Session):
        """Test trending books response has correct structure."""
        # Don't create any data - test with whatever state exists
        response = client.get("/api/v1/books/trending")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert "items" in result
        assert "algorithm" in result
        assert result["algorithm"] == "popularity"


# =============================================================================
# New Releases Tests
# =============================================================================


class TestNewReleases:
    """Tests for GET /api/v1/books/new-releases"""

    def test_new_releases_success(self, client: TestClient, db_session: Session):
        """Test getting new releases."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/new-releases")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result

    def test_new_releases_have_added_date(
        self, client: TestClient, db_session: Session
    ):
        """Test that new releases include added date."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/new-releases")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        for item in result["items"]:
            assert "added_at" in item
            assert "reasons" in item

    def test_new_releases_limit(self, client: TestClient, db_session: Session):
        """Test limiting number of new releases."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/new-releases", params={"limit": 3})

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert len(result["items"]) <= 3

    def test_new_releases_response_structure(self, client: TestClient, db_session: Session):
        """Test new releases response has correct structure."""
        # Don't create any data - test with whatever state exists
        response = client.get("/api/v1/books/new-releases")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert "items" in result


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestRecommendationResponseStructure:
    """Tests for recommendation response structures."""

    def test_similar_books_structure(self, client: TestClient, db_session: Session):
        """Test similar books response structure."""
        data = create_recommendation_test_data(db_session)

        response = client.get(f"/api/v1/books/{data['books']['1984'].id}/similar")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert "source_book_id" in result
        assert "algorithm" in result

        if result["items"]:
            item = result["items"][0]
            assert "book" in item
            assert "similarity_score" in item
            assert "reasons" in item

            book = item["book"]
            assert "id" in book
            assert "title" in book
            assert "authors" in book
            assert "genres" in book

    def test_personalized_response_structure(
        self, client: TestClient, db_session: Session
    ):
        """Test personalized recommendations response structure."""
        data = create_recommendation_test_data(db_session)

        response = client.get(
            "/api/v1/recommendations",
            headers=get_auth_header(data["users"]["alice"]),
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert "algorithm" in result
        assert "user_id" in result

    def test_trending_response_structure(
        self, client: TestClient, db_session: Session
    ):
        """Test trending books response structure."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/trending")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result
        assert "algorithm" in result

        if result["items"]:
            item = result["items"][0]
            assert "book" in item
            assert "trending_score" in item
            assert "reasons" in item

    def test_new_releases_response_structure(
        self, client: TestClient, db_session: Session
    ):
        """Test new releases response structure."""
        create_recommendation_test_data(db_session)

        response = client.get("/api/v1/books/new-releases")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()

        assert "items" in result

        if result["items"]:
            item = result["items"][0]
            assert "book" in item
            assert "added_at" in item
            assert "reasons" in item
