"""
Tests for User Authentication (Phase 3)

Tests the user registration system:
- Successful registration with valid data
- Duplicate email/username rejection
- Password validation (strength requirements)
- Username validation (format requirements)
- Email validation
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.security import verify_password


class TestUserRegistration:
    """Tests for user registration endpoint: POST /api/v1/auth/register"""

    def test_register_success(self, client: TestClient):
        """Test successful user registration with valid data."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123",
                "full_name": "New User",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert data["auth_provider"] == "local"
        assert "id" in data
        assert "created_at" in data
        # Password should NEVER be in response
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_without_full_name(self, client: TestClient):
        """Test registration without optional full_name field."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "minimal@example.com",
                "username": "minimaluser",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["full_name"] is None

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with already registered email."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "firstuser",
                "password": "SecurePass123",
            },
        )

        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "seconduser",
                "password": "SecurePass456",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Email already registered"

    def test_register_duplicate_username(self, client: TestClient):
        """Test registration with already taken username."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "first@example.com",
                "username": "takenuser",
                "password": "SecurePass123",
            },
        )

        # Second registration with same username
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "second@example.com",
                "username": "takenuser",
                "password": "SecurePass456",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Username already taken"

    def test_register_username_normalized_to_lowercase(self, client: TestClient):
        """Test that username is normalized to lowercase."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "upper@example.com",
                "username": "UpperCaseUser",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["username"] == "uppercaseuser"


class TestPasswordValidation:
    """Tests for password strength requirements."""

    def test_password_too_short(self, client: TestClient):
        """Test rejection of password shorter than 8 characters."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "username": "shortpass",
                "password": "Short1",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Check that error is about password length
        errors = response.json()["detail"]
        assert any("password" in str(e).lower() for e in errors)

    def test_password_no_uppercase(self, client: TestClient):
        """Test rejection of password without uppercase letter."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "nouppercase@example.com",
                "username": "nouppercase",
                "password": "lowercase123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("uppercase" in str(e).lower() for e in errors)

    def test_password_no_lowercase(self, client: TestClient):
        """Test rejection of password without lowercase letter."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "nolowercase@example.com",
                "username": "nolowercase",
                "password": "UPPERCASE123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("lowercase" in str(e).lower() for e in errors)

    def test_password_no_number(self, client: TestClient):
        """Test rejection of password without number."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "nonumber@example.com",
                "username": "nonumber",
                "password": "NoNumberHere",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("number" in str(e).lower() for e in errors)


class TestUsernameValidation:
    """Tests for username format requirements."""

    def test_username_too_short(self, client: TestClient):
        """Test rejection of username shorter than 3 characters."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "username": "ab",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_username_starts_with_number(self, client: TestClient):
        """Test rejection of username starting with a number."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "numstart@example.com",
                "username": "123user",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("letter" in str(e).lower() for e in errors)

    def test_username_with_special_chars(self, client: TestClient):
        """Test rejection of username with special characters."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "special@example.com",
                "username": "user@name",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_username_with_underscore_allowed(self, client: TestClient):
        """Test that underscore is allowed in username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "underscore@example.com",
                "username": "user_name_123",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["username"] == "user_name_123"


class TestEmailValidation:
    """Tests for email format validation."""

    def test_invalid_email_format(self, client: TestClient):
        """Test rejection of invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "notanemail",
                "username": "validuser",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_email_missing_domain(self, client: TestClient):
        """Test rejection of email without domain."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@",
                "username": "validuser",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestPasswordHashing:
    """Tests to verify password is properly hashed in database."""

    def test_password_stored_as_hash(
        self, client: TestClient, db_session: Session
    ):
        """Test that password is stored as bcrypt hash, not plain text."""
        password = "SecurePass123"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "hashtest@example.com",
                "username": "hashtest",
                "password": password,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Query the database directly
        user = db_session.query(User).filter_by(email="hashtest@example.com").first()

        assert user is not None
        # Password should NOT be stored as plain text
        assert user.hashed_password != password
        # Password should be a bcrypt hash (starts with $2b$)
        assert user.hashed_password.startswith("$2b$")
        # Verify the password matches using our security function
        assert verify_password(password, user.hashed_password) is True
        # Wrong password should not match
        assert verify_password("WrongPassword123", user.hashed_password) is False
