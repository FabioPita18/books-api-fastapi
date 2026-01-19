"""
Tests for Reviews (Phase 3D)

Tests the review system:
- List reviews for a book
- Create a review (authenticated)
- Get a single review
- Update a review (owner only)
- Delete a review (owner or superuser)
- Get book rating statistics
- List reviews by user
- Report/unreport reviews

Business Rules:
- One review per user per book
- Only review author can update
- Only review author or superuser can delete
"""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book
from app.models.review import Review
from app.models.user import User
from app.services.security import create_access_token


# =============================================================================
# Helper Functions
# =============================================================================


def get_auth_header(user: User) -> dict:
    """Create authorization header for a user."""
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# List Reviews for Book
# =============================================================================


class TestListBookReviews:
    """Tests for GET /api/v1/books/{book_id}/reviews"""

    def test_list_reviews_empty(self, client: TestClient, sample_book: Book):
        """Test listing reviews for a book with no reviews."""
        response = client.get(f"/api/v1/books/{sample_book.id}/reviews")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_list_reviews_with_data(
        self, client: TestClient, sample_review: Review
    ):
        """Test listing reviews for a book with reviews."""
        response = client.get(
            f"/api/v1/books/{sample_review.book_id}/reviews"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

        review = data["items"][0]
        assert review["rating"] == 4
        assert review["title"] == "Great book!"
        assert "user" in review
        assert "book" in review

    def test_list_reviews_book_not_found(self, client: TestClient):
        """Test listing reviews for non-existent book."""
        response = client.get("/api/v1/books/99999/reviews")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_reviews_pagination(
        self,
        client: TestClient,
        db_session: Session,
        sample_book: Book,
    ):
        """Test pagination of reviews."""
        # Create multiple users and reviews
        from app.services.security import hash_password

        users = []
        for i in range(15):
            user = User(
                email=f"reviewer{i}@example.com",
                username=f"reviewer{i}",
                hashed_password=hash_password("Pass123"),
                is_active=True,
            )
            db_session.add(user)
            users.append(user)
        db_session.commit()

        for i, user in enumerate(users):
            review = Review(
                book_id=sample_book.id,
                user_id=user.id,
                rating=(i % 5) + 1,
                title=f"Review {i}",
            )
            db_session.add(review)
        db_session.commit()

        # Test first page
        response = client.get(
            f"/api/v1/books/{sample_book.id}/reviews?per_page=5"
        )
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 5
        assert data["pages"] == 3

        # Test second page
        response = client.get(
            f"/api/v1/books/{sample_book.id}/reviews?page=2&per_page=5"
        )
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2


# =============================================================================
# Create Review
# =============================================================================


class TestCreateReview:
    """Tests for POST /api/v1/books/{book_id}/reviews"""

    def test_create_review_success(
        self,
        client: TestClient,
        sample_book: Book,
        sample_user: User,
    ):
        """Test creating a review with valid data."""
        response = client.post(
            f"/api/v1/books/{sample_book.id}/reviews",
            json={
                "rating": 5,
                "title": "Excellent!",
                "content": "A masterpiece of literature.",
            },
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["rating"] == 5
        assert data["title"] == "Excellent!"
        assert data["content"] == "A masterpiece of literature."
        assert data["book_id"] == sample_book.id
        assert data["user_id"] == sample_user.id

    def test_create_review_rating_only(
        self,
        client: TestClient,
        sample_book: Book,
        sample_user: User,
    ):
        """Test creating a review with only rating (title/content optional)."""
        response = client.post(
            f"/api/v1/books/{sample_book.id}/reviews",
            json={"rating": 3},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["rating"] == 3
        assert data["title"] is None
        assert data["content"] is None

    def test_create_review_duplicate(
        self,
        client: TestClient,
        sample_review: Review,
        sample_user: User,
    ):
        """Test creating duplicate review for same book."""
        response = client.post(
            f"/api/v1/books/{sample_review.book_id}/reviews",
            json={"rating": 3},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already reviewed" in response.json()["detail"].lower()

    def test_create_review_unauthenticated(
        self, client: TestClient, sample_book: Book
    ):
        """Test creating review without authentication."""
        response = client.post(
            f"/api/v1/books/{sample_book.id}/reviews",
            json={"rating": 5},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_review_book_not_found(
        self, client: TestClient, sample_user: User
    ):
        """Test creating review for non-existent book."""
        response = client.post(
            "/api/v1/books/99999/reviews",
            json={"rating": 5},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_review_invalid_rating_too_low(
        self,
        client: TestClient,
        sample_book: Book,
        sample_user: User,
    ):
        """Test creating review with rating below 1."""
        response = client.post(
            f"/api/v1/books/{sample_book.id}/reviews",
            json={"rating": 0},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_review_invalid_rating_too_high(
        self,
        client: TestClient,
        sample_book: Book,
        sample_user: User,
    ):
        """Test creating review with rating above 5."""
        response = client.post(
            f"/api/v1/books/{sample_book.id}/reviews",
            json={"rating": 6},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Get Single Review
# =============================================================================


class TestGetReview:
    """Tests for GET /api/v1/reviews/{review_id}"""

    def test_get_review_success(self, client: TestClient, sample_review: Review):
        """Test getting a review by ID."""
        response = client.get(f"/api/v1/reviews/{sample_review.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_review.id
        assert data["rating"] == sample_review.rating
        assert data["title"] == sample_review.title

    def test_get_review_not_found(self, client: TestClient):
        """Test getting non-existent review."""
        response = client.get("/api/v1/reviews/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Update Review
# =============================================================================


class TestUpdateReview:
    """Tests for PUT /api/v1/reviews/{review_id}"""

    def test_update_review_success(
        self,
        client: TestClient,
        sample_review: Review,
        sample_user: User,
    ):
        """Test updating own review."""
        response = client.put(
            f"/api/v1/reviews/{sample_review.id}",
            json={
                "rating": 5,
                "title": "Updated title",
                "content": "Updated content",
            },
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["rating"] == 5
        assert data["title"] == "Updated title"
        assert data["content"] == "Updated content"

    def test_update_review_partial(
        self,
        client: TestClient,
        sample_review: Review,
        sample_user: User,
    ):
        """Test partial update of review."""
        response = client.put(
            f"/api/v1/reviews/{sample_review.id}",
            json={"rating": 2},  # Only update rating
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["rating"] == 2
        # Original title should be preserved
        assert data["title"] == sample_review.title

    def test_update_review_not_owner(
        self,
        client: TestClient,
        sample_review: Review,
        second_user: User,
    ):
        """Test updating another user's review fails."""
        response = client.put(
            f"/api/v1/reviews/{sample_review.id}",
            json={"rating": 1},
            headers=get_auth_header(second_user),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "own reviews" in response.json()["detail"].lower()

    def test_update_review_unauthenticated(
        self, client: TestClient, sample_review: Review
    ):
        """Test updating review without authentication."""
        response = client.put(
            f"/api/v1/reviews/{sample_review.id}",
            json={"rating": 1},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_review_not_found(
        self, client: TestClient, sample_user: User
    ):
        """Test updating non-existent review."""
        response = client.put(
            "/api/v1/reviews/99999",
            json={"rating": 5},
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Delete Review
# =============================================================================


class TestDeleteReview:
    """Tests for DELETE /api/v1/reviews/{review_id}"""

    def test_delete_review_by_owner(
        self,
        client: TestClient,
        sample_review: Review,
        sample_user: User,
    ):
        """Test owner can delete their review."""
        response = client.delete(
            f"/api/v1/reviews/{sample_review.id}",
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        get_response = client.get(f"/api/v1/reviews/{sample_review.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_review_by_superuser(
        self,
        client: TestClient,
        sample_review: Review,
        superuser: User,
    ):
        """Test superuser can delete any review."""
        response = client.delete(
            f"/api/v1/reviews/{sample_review.id}",
            headers=get_auth_header(superuser),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_review_not_owner(
        self,
        client: TestClient,
        sample_review: Review,
        second_user: User,
    ):
        """Test non-owner cannot delete review."""
        response = client.delete(
            f"/api/v1/reviews/{sample_review.id}",
            headers=get_auth_header(second_user),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_review_unauthenticated(
        self, client: TestClient, sample_review: Review
    ):
        """Test deleting review without authentication."""
        response = client.delete(f"/api/v1/reviews/{sample_review.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_review_not_found(
        self, client: TestClient, sample_user: User
    ):
        """Test deleting non-existent review."""
        response = client.delete(
            "/api/v1/reviews/99999",
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Book Rating Statistics
# =============================================================================


class TestBookRatingStats:
    """Tests for GET /api/v1/books/{book_id}/rating"""

    def test_rating_stats_no_reviews(
        self, client: TestClient, sample_book: Book
    ):
        """Test rating stats for book with no reviews."""
        response = client.get(f"/api/v1/books/{sample_book.id}/rating")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["book_id"] == sample_book.id
        assert data["average_rating"] == 0.0
        assert data["total_reviews"] == 0
        assert data["rating_distribution"] == {
            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
        }

    def test_rating_stats_with_reviews(
        self,
        client: TestClient,
        db_session: Session,
        sample_book: Book,
    ):
        """Test rating stats calculation with multiple reviews."""
        from app.services.security import hash_password

        # Create users and reviews with different ratings
        ratings = [5, 4, 4, 3, 5]  # avg = 4.2
        for i, rating in enumerate(ratings):
            user = User(
                email=f"rater{i}@example.com",
                username=f"rater{i}",
                hashed_password=hash_password("Pass123"),
                is_active=True,
            )
            db_session.add(user)
            db_session.flush()

            review = Review(
                book_id=sample_book.id,
                user_id=user.id,
                rating=rating,
            )
            db_session.add(review)
        db_session.commit()

        response = client.get(f"/api/v1/books/{sample_book.id}/rating")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_reviews"] == 5
        assert data["average_rating"] == 4.2
        # Distribution: 3->1, 4->2, 5->2
        assert data["rating_distribution"]["3"] == 1
        assert data["rating_distribution"]["4"] == 2
        assert data["rating_distribution"]["5"] == 2

    def test_rating_stats_book_not_found(self, client: TestClient):
        """Test rating stats for non-existent book."""
        response = client.get("/api/v1/books/99999/rating")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# List User Reviews
# =============================================================================


class TestListUserReviews:
    """Tests for GET /api/v1/users/{user_id}/reviews"""

    def test_list_user_reviews_empty(
        self, client: TestClient, sample_user: User
    ):
        """Test listing reviews for user with no reviews."""
        response = client.get(f"/api/v1/users/{sample_user.id}/reviews")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_user_reviews_with_data(
        self, client: TestClient, sample_review: Review
    ):
        """Test listing reviews for user with reviews."""
        response = client.get(
            f"/api/v1/users/{sample_review.user_id}/reviews"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == sample_review.id

    def test_list_user_reviews_user_not_found(self, client: TestClient):
        """Test listing reviews for non-existent user."""
        response = client.get("/api/v1/users/99999/reviews")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Report Reviews
# =============================================================================


class TestReportReview:
    """Tests for POST /api/v1/reviews/{review_id}/report"""

    def test_report_review_success(
        self,
        client: TestClient,
        sample_review: Review,
        second_user: User,
    ):
        """Test reporting a review."""
        response = client.post(
            f"/api/v1/reviews/{sample_review.id}/report",
            headers=get_auth_header(second_user),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_report_review_unauthenticated(
        self, client: TestClient, sample_review: Review
    ):
        """Test reporting without authentication."""
        response = client.post(
            f"/api/v1/reviews/{sample_review.id}/report",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_report_review_not_found(
        self, client: TestClient, sample_user: User
    ):
        """Test reporting non-existent review."""
        response = client.post(
            "/api/v1/reviews/99999/report",
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# List Reported Reviews (Superuser only)
# =============================================================================


class TestListReportedReviews:
    """Tests for GET /api/v1/reviews/reported"""

    def test_list_reported_reviews_superuser(
        self,
        client: TestClient,
        db_session: Session,
        sample_review: Review,
        superuser: User,
    ):
        """Test superuser can list reported reviews."""
        # Mark review as reported
        sample_review.reported = True
        db_session.commit()

        response = client.get(
            "/api/v1/reviews/reported",
            headers=get_auth_header(superuser),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == sample_review.id

    def test_list_reported_reviews_not_superuser(
        self, client: TestClient, sample_user: User
    ):
        """Test non-superuser cannot list reported reviews."""
        response = client.get(
            "/api/v1/reviews/reported",
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Unreport Review (Superuser only)
# =============================================================================


class TestUnreportReview:
    """Tests for POST /api/v1/reviews/{review_id}/unreport"""

    def test_unreport_review_superuser(
        self,
        client: TestClient,
        db_session: Session,
        sample_review: Review,
        superuser: User,
    ):
        """Test superuser can unreport a review."""
        # Mark as reported first
        sample_review.reported = True
        db_session.commit()

        response = client.post(
            f"/api/v1/reviews/{sample_review.id}/unreport",
            headers=get_auth_header(superuser),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unreport_review_not_superuser(
        self, client: TestClient, sample_review: Review, sample_user: User
    ):
        """Test non-superuser cannot unreport reviews."""
        response = client.post(
            f"/api/v1/reviews/{sample_review.id}/unreport",
            headers=get_auth_header(sample_user),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
