# ruff: noqa: I001
"""
Tests for OAuth Social Login

Tests cover:
- Google OAuth callback handling
- GitHub OAuth callback handling
- Account creation from OAuth
- Account linking (existing email)
- OAuth error handling

These tests mock external OAuth provider responses to test
the callback handling logic without making real HTTP requests.
"""

import os

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-at-least-32-characters-long"
os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
os.environ["GITHUB_CLIENT_ID"] = "test-github-client-id"
os.environ["GITHUB_CLIENT_SECRET"] = "test-github-client-secret"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.security import hash_password


def create_mock_response(status_code: int, json_data: dict | None = None, text: str = ""):
    """Create a mock httpx response with sync json() method."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = text
    return response


# =============================================================================
# Mock Response Helpers
# =============================================================================


def mock_google_token_response():
    """Mock successful Google token exchange response."""
    return {
        "access_token": "mock-google-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "mock-refresh-token",
    }


def mock_google_user_response(
    email: str = "googleuser@gmail.com",
    user_id: str = "google-123456",
    name: str = "Google User",
    picture: str = "https://example.com/avatar.jpg",
):
    """Mock Google user info response."""
    return {
        "id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "verified_email": True,
    }


def mock_github_token_response():
    """Mock successful GitHub token exchange response."""
    return {
        "access_token": "mock-github-access-token",
        "token_type": "bearer",
        "scope": "user:email",
    }


def mock_github_user_response(
    email: str = "githubuser@github.com",
    user_id: int = 789012,
    login: str = "githubuser",
    name: str = "GitHub User",
    avatar_url: str = "https://avatars.githubusercontent.com/u/789012",
):
    """Mock GitHub user info response."""
    return {
        "id": user_id,
        "login": login,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
    }


def mock_github_emails_response(primary_email: str = "githubuser@github.com"):
    """Mock GitHub emails endpoint response."""
    return [
        {"email": primary_email, "primary": True, "verified": True},
        {"email": "secondary@example.com", "primary": False, "verified": True},
    ]


# =============================================================================
# Test: Google OAuth Callback
# =============================================================================


class TestGoogleOAuthCallback:
    """Tests for Google OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_google_callback_creates_new_user(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that Google OAuth creates a new user."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            # Setup mock responses
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Token exchange response (sync json method)
            token_response = create_mock_response(200, mock_google_token_response())

            # User info response (sync json method)
            user_response = create_mock_response(200, mock_google_user_response())

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/google/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_google_callback_links_existing_account(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that Google OAuth links to existing account with same email."""
        # Create existing user with same email
        existing_user = User(
            email="googleuser@gmail.com",
            username="existinguser",
            hashed_password=hash_password("SecurePass123"),
            is_active=True,
            is_verified=True,
            auth_provider="local",
        )
        db_session.add(existing_user)
        db_session.commit()
        db_session.refresh(existing_user)

        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_google_token_response())
            user_response = create_mock_response(
                200, mock_google_user_response(email="googleuser@gmail.com")
            )

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/google/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200

            # Verify the existing user was updated
            db_session.refresh(existing_user)
            assert existing_user.auth_provider == "google"
            assert existing_user.provider_user_id == "google-123456"

    def test_google_callback_missing_code(self, client: TestClient):
        """Test that missing code returns error."""
        response = client.get("/api/v1/auth/google/callback")

        assert response.status_code == 400
        assert "code" in response.json()["detail"].lower()

    def test_google_callback_with_error(self, client: TestClient):
        """Test that OAuth error is handled."""
        response = client.get(
            "/api/v1/auth/google/callback",
            params={"error": "access_denied"},
        )

        assert response.status_code == 400
        assert "error" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_google_callback_token_exchange_fails(
        self,
        client: TestClient,
    ):
        """Test handling of failed token exchange."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Token exchange fails
            token_response = create_mock_response(400, None, "Invalid code")

            mock_instance.post.return_value = token_response

            response = client.get(
                "/api/v1/auth/google/callback",
                params={"code": "invalid-code"},
            )

            assert response.status_code == 400


# =============================================================================
# Test: GitHub OAuth Callback
# =============================================================================


class TestGitHubOAuthCallback:
    """Tests for GitHub OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_github_callback_creates_new_user(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that GitHub OAuth creates a new user."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_github_token_response())
            user_response = create_mock_response(200, mock_github_user_response())

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_github_callback_fetches_private_email(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that GitHub OAuth fetches email from emails endpoint if not in profile."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_github_token_response())
            user_response = create_mock_response(200, mock_github_user_response(email=None))
            emails_response = create_mock_response(
                200, mock_github_emails_response("private@github.com")
            )

            mock_instance.post.return_value = token_response
            # First get is user info, second is emails
            mock_instance.get.side_effect = [user_response, emails_response]

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_github_callback_links_existing_account(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that GitHub OAuth links to existing account with same email."""
        # Create existing user
        existing_user = User(
            email="githubuser@github.com",
            username="existingghuser",
            hashed_password=hash_password("SecurePass123"),
            is_active=True,
            is_verified=True,
            auth_provider="local",
        )
        db_session.add(existing_user)
        db_session.commit()
        db_session.refresh(existing_user)

        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_github_token_response())
            user_response = create_mock_response(
                200, mock_github_user_response(email="githubuser@github.com")
            )

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200

            # Verify the existing user was updated
            db_session.refresh(existing_user)
            assert existing_user.auth_provider == "github"
            assert existing_user.provider_user_id == "789012"

    def test_github_callback_missing_code(self, client: TestClient):
        """Test that missing code returns error."""
        response = client.get("/api/v1/auth/github/callback")

        assert response.status_code == 400
        assert "code" in response.json()["detail"].lower()

    def test_github_callback_with_error(self, client: TestClient):
        """Test that OAuth error is handled."""
        response = client.get(
            "/api/v1/auth/github/callback",
            params={"error": "access_denied"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_github_callback_oauth_error_in_token(
        self,
        client: TestClient,
    ):
        """Test handling of OAuth error in token response."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Token response with error
            token_response = create_mock_response(200, {
                "error": "bad_verification_code",
                "error_description": "The code passed is incorrect or expired.",
            })

            mock_instance.post.return_value = token_response

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "expired-code"},
            )

            assert response.status_code == 400


# =============================================================================
# Test: OAuth Login Redirects
# =============================================================================


class TestOAuthLoginRedirects:
    """Tests for OAuth login redirect endpoints."""

    def test_google_login_redirects(self, client: TestClient):
        """Test that Google login endpoint returns redirect."""
        response = client.get(
            "/api/v1/auth/google",
            follow_redirects=False,
        )

        assert response.status_code == 307  # Temporary redirect
        assert "accounts.google.com" in response.headers["location"]

    def test_github_login_redirects(self, client: TestClient):
        """Test that GitHub login endpoint returns redirect."""
        response = client.get(
            "/api/v1/auth/github",
            follow_redirects=False,
        )

        assert response.status_code == 307  # Temporary redirect
        assert "github.com" in response.headers["location"]


# =============================================================================
# Test: OAuth Account Creation
# =============================================================================


class TestOAuthAccountCreation:
    """Tests for OAuth account creation logic."""

    @pytest.mark.asyncio
    async def test_oauth_creates_unique_username(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that OAuth creates unique username when collision occurs."""
        # Create user with username that would be generated
        existing_user = User(
            email="other@example.com",
            username="googleuser",  # Same as would be derived from Google email
            hashed_password=hash_password("SecurePass123"),
            is_active=True,
            is_verified=True,
        )
        db_session.add(existing_user)
        db_session.commit()

        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_google_token_response())
            user_response = create_mock_response(200, mock_google_user_response(
                email="googleuser@gmail.com",
                user_id="new-google-id",
            ))

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/google/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200

            # Verify a new user was created with modified username
            from sqlalchemy import select
            stmt = select(User).where(User.provider_user_id == "new-google-id")
            new_user = db_session.execute(stmt).scalar_one_or_none()
            assert new_user is not None
            # Username should be incremented (googleuser1, googleuser2, etc.)
            assert new_user.username.startswith("googleuser")
            assert new_user.username != "googleuser"

    @pytest.mark.asyncio
    async def test_oauth_user_is_verified(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that OAuth users are marked as verified."""
        with patch("app.services.oauth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            token_response = create_mock_response(200, mock_google_token_response())
            user_response = create_mock_response(200, mock_google_user_response(
                email="newverified@gmail.com",
                user_id="verified-user-id",
            ))

            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response

            response = client.get(
                "/api/v1/auth/google/callback",
                params={"code": "mock-auth-code"},
            )

            assert response.status_code == 200

            # Verify user is marked as verified
            from sqlalchemy import select
            stmt = select(User).where(User.email == "newverified@gmail.com")
            user = db_session.execute(stmt).scalar_one()
            assert user.is_verified is True
            assert user.is_active is True
