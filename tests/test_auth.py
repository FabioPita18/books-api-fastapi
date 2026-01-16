"""
Tests for API Key Authentication

Tests the authentication system added in Phase 2D:
- Protected endpoints require API key
- Invalid/missing API keys are rejected
- Public (GET) endpoints work without API key
- API key management endpoints

Note: These tests enable API_KEY_ENABLED to test auth behavior.
The CI pipeline disables it by default for backward compatibility.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app


class TestAPIKeyAuthentication:
    """Tests for API key authentication on protected endpoints."""

    @pytest.fixture
    def auth_client(self, db_session):
        """
        Create a test client with API key authentication ENABLED.

        This fixture overrides the settings to enable API key checking,
        allowing us to test authentication behavior.
        """
        # Store original settings
        settings = get_settings()
        original_enabled = settings.api_key_enabled
        original_admin_key = settings.admin_api_key

        # Enable API key auth and set admin key for testing
        settings.api_key_enabled = True
        settings.admin_api_key = "test-admin-api-key-12345"

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client, settings.admin_api_key

        # Restore original settings
        settings.api_key_enabled = original_enabled
        settings.admin_api_key = original_admin_key
        app.dependency_overrides.clear()

    def test_get_endpoints_public(self, auth_client):
        """Test that GET endpoints work without API key."""
        client, _ = auth_client

        # List books should work
        response = client.get("/api/v1/books/")
        assert response.status_code == status.HTTP_200_OK

        # List authors should work
        response = client.get("/api/v1/authors/")
        assert response.status_code == status.HTTP_200_OK

        # List genres should work
        response = client.get("/api/v1/genres/")
        assert response.status_code == status.HTTP_200_OK

    def test_post_requires_api_key(self, auth_client):
        """Test that POST endpoints require API key."""
        client, _ = auth_client

        book_data = {"title": "Test Book"}
        response = client.post("/api/v1/books/", json=book_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "API key required" in response.json()["detail"]

    def test_post_with_valid_api_key(self, auth_client):
        """Test that POST works with valid API key."""
        client, admin_key = auth_client

        book_data = {"title": "Test Book"}
        response = client.post(
            "/api/v1/books/",
            json=book_data,
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["title"] == "Test Book"

    def test_post_with_invalid_api_key(self, auth_client):
        """Test that POST fails with invalid API key."""
        client, _ = auth_client

        book_data = {"title": "Test Book"}
        response = client.post(
            "/api/v1/books/",
            json=book_data,
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid" in response.json()["detail"]

    def test_put_requires_api_key(self, auth_client, sample_book):
        """Test that PUT endpoints require API key."""
        client, _ = auth_client

        update_data = {"title": "Updated Title"}
        response = client.put(
            f"/api/v1/books/{sample_book.id}",
            json=update_data,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_put_with_valid_api_key(self, auth_client, sample_book):
        """Test that PUT works with valid API key."""
        client, admin_key = auth_client

        update_data = {"title": "Updated Title"}
        response = client.put(
            f"/api/v1/books/{sample_book.id}",
            json=update_data,
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Title"

    def test_delete_requires_api_key(self, auth_client, sample_book):
        """Test that DELETE endpoints require API key."""
        client, _ = auth_client

        response = client.delete(f"/api/v1/books/{sample_book.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_with_valid_api_key(self, auth_client, sample_book):
        """Test that DELETE works with valid API key."""
        client, admin_key = auth_client

        response = client.delete(
            f"/api/v1/books/{sample_book.id}",
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestAPIKeyManagement:
    """Tests for API key management endpoints."""

    @pytest.fixture
    def admin_client(self, db_session):
        """Create a test client with admin privileges."""
        settings = get_settings()
        original_enabled = settings.api_key_enabled
        original_admin_key = settings.admin_api_key

        settings.api_key_enabled = True
        settings.admin_api_key = "test-admin-key"

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client, settings.admin_api_key

        settings.api_key_enabled = original_enabled
        settings.admin_api_key = original_admin_key
        app.dependency_overrides.clear()

    def test_create_api_key(self, admin_client):
        """Test creating a new API key."""
        client, admin_key = admin_client

        key_data = {
            "name": "Test Application",
            "description": "API key for testing",
        }
        response = client.post(
            "/api/v1/api-keys/",
            json=key_data,
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Application"
        assert "key" in data  # Full key shown only on creation
        assert data["key"].startswith("bk_")
        assert "key_prefix" in data

    def test_create_api_key_requires_auth(self, admin_client):
        """Test that creating API key requires authentication."""
        client, _ = admin_client

        key_data = {"name": "Test Key"}
        response = client.post("/api/v1/api-keys/", json=key_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_api_keys(self, admin_client):
        """Test listing API keys."""
        client, admin_key = admin_client

        # First create a key
        client.post(
            "/api/v1/api-keys/",
            json={"name": "Listed Key"},
            headers={"X-API-Key": admin_key},
        )

        # Then list
        response = client.get(
            "/api/v1/api-keys/",
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # Listed keys should NOT include the full key
        if data:
            assert "key" not in data[0] or data[0].get("key") is None

    def test_revoke_api_key(self, admin_client):
        """Test revoking an API key."""
        client, admin_key = admin_client

        # Create a key
        create_response = client.post(
            "/api/v1/api-keys/",
            json={"name": "Key to Revoke"},
            headers={"X-API-Key": admin_key},
        )
        key_id = create_response.json()["id"]

        # Revoke it
        response = client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"X-API-Key": admin_key},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's revoked by checking the key details
        get_response = client.get(
            f"/api/v1/api-keys/{key_id}",
            headers={"X-API-Key": admin_key},
        )
        assert get_response.json()["is_active"] is False


class TestAuthWithDisabledAuth:
    """Tests when API key authentication is disabled."""

    @pytest.fixture
    def no_auth_client(self, db_session):
        """Create a test client with API key authentication DISABLED."""
        settings = get_settings()
        original_enabled = settings.api_key_enabled

        # Explicitly disable API key auth
        settings.api_key_enabled = False

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client

        # Restore
        settings.api_key_enabled = original_enabled
        app.dependency_overrides.clear()

    def test_write_operations_work_without_key(self, no_auth_client):
        """
        Test that write operations work when auth is disabled.
        """
        book_data = {"title": "Book Without Auth"}
        response = no_auth_client.post("/api/v1/books/", json=book_data)

        # Should work because auth is disabled
        assert response.status_code == status.HTTP_201_CREATED


class TestAPIKeyHeader:
    """Tests for API key header handling."""

    @pytest.fixture
    def header_client(self, db_session):
        """Create client with auth enabled for header tests."""
        settings = get_settings()
        settings.api_key_enabled = True
        settings.admin_api_key = "correct-key"

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client

        settings.api_key_enabled = False
        settings.admin_api_key = None
        app.dependency_overrides.clear()

    def test_empty_api_key_header(self, header_client):
        """Test that empty API key header is rejected."""
        response = header_client.post(
            "/api/v1/books/",
            json={"title": "Test"},
            headers={"X-API-Key": ""},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_whitespace_api_key_header(self, header_client):
        """Test that whitespace-only API key is rejected."""
        response = header_client.post(
            "/api/v1/books/",
            json={"title": "Test"},
            headers={"X-API-Key": "   "},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_case_sensitive_header_name(self, header_client):
        """Test that X-API-Key header is case-insensitive (HTTP standard)."""
        response = header_client.post(
            "/api/v1/books/",
            json={"title": "Test"},
            headers={"x-api-key": "correct-key"},  # lowercase
        )

        # HTTP headers are case-insensitive
        assert response.status_code == status.HTTP_201_CREATED
