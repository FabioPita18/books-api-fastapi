# ruff: noqa: I001
"""
Tests for User Profile Endpoints

Tests cover:
- GET /users/me - Current user profile
- PUT /users/me - Update profile
- PUT /users/me/password - Change password
- GET /users/me/reviews - User's reviews
- GET /users/{user_id} - Public user profile
"""

import os

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-at-least-32-characters-long"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.user import User
from app.services.security import create_access_token


# =============================================================================
# Helper Functions
# =============================================================================


def get_auth_headers(user: User) -> dict:
    """Generate auth headers for a user."""
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Test: GET /users/me
# =============================================================================


class TestGetCurrentUser:
    """Tests for GET /users/me endpoint."""

    def test_get_me_success(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test getting current user profile."""
        response = client.get(
            "/api/v1/users/me",
            headers=get_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["email"] == sample_user.email
        assert data["username"] == sample_user.username

    def test_get_me_unauthenticated(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/users/me")

        assert response.status_code == 401


# =============================================================================
# Test: PUT /users/me
# =============================================================================


class TestUpdateProfile:
    """Tests for PUT /users/me endpoint."""

    def test_update_profile_full_name(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test updating full name."""
        response = client.put(
            "/api/v1/users/me",
            headers=get_auth_headers(sample_user),
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_update_profile_bio(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test updating bio."""
        response = client.put(
            "/api/v1/users/me",
            headers=get_auth_headers(sample_user),
            json={"bio": "I love reading books!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "I love reading books!"

    def test_update_profile_avatar_url(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test updating avatar URL."""
        avatar_url = "https://example.com/avatar.jpg"
        response = client.put(
            "/api/v1/users/me",
            headers=get_auth_headers(sample_user),
            json={"avatar_url": avatar_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == avatar_url

    def test_update_profile_multiple_fields(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test updating multiple fields at once."""
        response = client.put(
            "/api/v1/users/me",
            headers=get_auth_headers(sample_user),
            json={
                "full_name": "New Name",
                "bio": "New bio",
                "avatar_url": "https://example.com/new.jpg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["bio"] == "New bio"
        assert data["avatar_url"] == "https://example.com/new.jpg"

    def test_update_profile_unauthenticated(self, client: TestClient):
        """Test updating profile without authentication."""
        response = client.put(
            "/api/v1/users/me",
            json={"full_name": "Hacker"},
        )

        assert response.status_code == 401


# =============================================================================
# Test: PUT /users/me/password
# =============================================================================


class TestChangePassword:
    """Tests for PUT /users/me/password endpoint."""

    def test_change_password_success(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test changing password successfully."""
        response = client.put(
            "/api/v1/users/me/password",
            headers=get_auth_headers(sample_user),
            json={
                "current_password": "SecurePass123",
                "new_password": "NewSecure456",
            },
        )

        assert response.status_code == 204

    def test_change_password_wrong_current(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test changing password with wrong current password."""
        response = client.put(
            "/api/v1/users/me/password",
            headers=get_auth_headers(sample_user),
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewSecure456",
            },
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_weak_new_password(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test changing password with weak new password."""
        response = client.put(
            "/api/v1/users/me/password",
            headers=get_auth_headers(sample_user),
            json={
                "current_password": "SecurePass123",
                "new_password": "weak",  # Too short, no uppercase, no number
            },
        )

        assert response.status_code == 422  # Validation error

    def test_change_password_unauthenticated(self, client: TestClient):
        """Test changing password without authentication."""
        response = client.put(
            "/api/v1/users/me/password",
            json={
                "current_password": "SecurePass123",
                "new_password": "NewSecure456",
            },
        )

        assert response.status_code == 401

    def test_change_password_oauth_user(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that OAuth-only users cannot change password."""
        # Create OAuth user (no password)
        oauth_user = User(
            email="oauth@example.com",
            username="oauthuser",
            hashed_password=None,  # OAuth users have no password
            auth_provider="google",
            provider_user_id="12345",
            is_active=True,
            is_verified=True,
        )
        db_session.add(oauth_user)
        db_session.commit()
        db_session.refresh(oauth_user)

        response = client.put(
            "/api/v1/users/me/password",
            headers=get_auth_headers(oauth_user),
            json={
                "current_password": "anything",
                "new_password": "NewSecure456",
            },
        )

        assert response.status_code == 400
        assert "oauth" in response.json()["detail"].lower()


# =============================================================================
# Test: GET /users/me/reviews
# =============================================================================


class TestGetMyReviews:
    """Tests for GET /users/me/reviews endpoint."""

    def test_get_my_reviews_empty(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test getting reviews when user has none."""
        response = client.get(
            "/api/v1/users/me/reviews",
            headers=get_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_my_reviews_with_data(
        self,
        client: TestClient,
        sample_user: User,
        sample_review: Review,
    ):
        """Test getting reviews when user has reviews."""
        response = client.get(
            "/api/v1/users/me/reviews",
            headers=get_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["id"] == sample_review.id

    def test_get_my_reviews_unauthenticated(self, client: TestClient):
        """Test getting reviews without authentication."""
        response = client.get("/api/v1/users/me/reviews")

        assert response.status_code == 401


# =============================================================================
# Test: GET /users/{user_id}
# =============================================================================


class TestGetPublicProfile:
    """Tests for GET /users/{user_id} endpoint."""

    def test_get_public_profile_success(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test getting a public user profile."""
        response = client.get(f"/api/v1/users/{sample_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["username"] == sample_user.username
        # Should NOT include email
        assert "email" not in data
        # Should NOT include is_active
        assert "is_active" not in data

    def test_get_public_profile_not_found(self, client: TestClient):
        """Test getting a non-existent user profile."""
        response = client.get("/api/v1/users/99999")

        assert response.status_code == 404

    def test_get_public_profile_inactive_user(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that inactive users are not exposed."""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password="hashed",
            is_active=False,
            is_verified=True,
        )
        db_session.add(inactive_user)
        db_session.commit()
        db_session.refresh(inactive_user)

        response = client.get(f"/api/v1/users/{inactive_user.id}")

        # Should return 404, not expose that user exists but is inactive
        assert response.status_code == 404

    def test_public_profile_limited_fields(
        self,
        client: TestClient,
        sample_user: User,
    ):
        """Test that public profile only shows limited fields."""
        response = client.get(f"/api/v1/users/{sample_user.id}")

        assert response.status_code == 200
        data = response.json()

        # Should include these public fields
        assert "id" in data
        assert "username" in data
        assert "full_name" in data
        assert "avatar_url" in data
        assert "bio" in data
        assert "created_at" in data

        # Should NOT include these private fields
        assert "email" not in data
        assert "is_active" not in data
        assert "is_verified" not in data
        assert "auth_provider" not in data
        assert "hashed_password" not in data
