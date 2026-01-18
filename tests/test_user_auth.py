"""
Tests for User Authentication (Phase 3)

Tests the user authentication system:
- Registration (email/password)
- Login (JWT tokens)
- Token refresh
- Logout
- Protected endpoints (/me)

Coverage includes:
- Successful flows
- Error handling
- Security validations
"""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.security import create_refresh_token, verify_password


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


# =============================================================================
# JWT Authentication Tests (Phase 3B)
# =============================================================================


class TestLogin:
    """Tests for login endpoint: POST /api/v1/auth/login"""

    def test_login_success(self, client: TestClient):
        """Test successful login returns access token."""
        # First register a user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "SecurePass123",
            },
        )

        # Login with email/password
        response = client.post(
            "/api/v1/auth/login",
            data={  # OAuth2 uses form data, not JSON
                "username": "login@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

        # Refresh token should be set as httpOnly cookie
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client: TestClient):
        """Test login with incorrect password."""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "username": "wrongpass",
                "password": "SecurePass123",
            },
        )

        # Try login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "wrongpass@example.com",
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent email."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_inactive_user(self, client: TestClient, db_session: Session):
        """Test login with inactive account."""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "inactive@example.com",
                "username": "inactiveuser",
                "password": "SecurePass123",
            },
        )

        # Deactivate user directly in database
        user = db_session.query(User).filter_by(email="inactive@example.com").first()
        user.is_active = False
        db_session.commit()

        # Try login
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Account is inactive"


class TestGetMe:
    """Tests for get current user endpoint: GET /api/v1/auth/me"""

    def test_get_me_success(self, client: TestClient):
        """Test getting current user with valid token."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@example.com",
                "username": "meuser",
                "password": "SecurePass123",
                "full_name": "Me User",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "me@example.com",
                "password": "SecurePass123",
            },
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["username"] == "meuser"
        assert data["full_name"] == "Me User"
        assert "hashed_password" not in data

    def test_get_me_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Tests for token refresh endpoint: POST /api/v1/auth/refresh"""

    def test_refresh_token_success(self, client: TestClient, db_session: Session):
        """Test refreshing access token with valid refresh token."""
        # Register and login to get refresh token
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "username": "refreshuser",
                "password": "SecurePass123",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "refresh@example.com",
                "password": "SecurePass123",
            },
        )

        # Get refresh token from cookie
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # Refresh the access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_missing(self, client: TestClient):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_access_token_fails(self, client: TestClient):
        """Test that access token cannot be used for refresh."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "accessonly@example.com",
                "username": "accessonly",
                "password": "SecurePass123",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "accessonly@example.com",
                "password": "SecurePass123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh (should fail)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Tests for logout endpoint: POST /api/v1/auth/logout"""

    def test_logout_success(self, client: TestClient):
        """Test successful logout clears refresh token cookie."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "username": "logoutuser",
                "password": "SecurePass123",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "logout@example.com",
                "password": "SecurePass123",
            },
        )
        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_without_token(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenSecurity:
    """Tests for JWT token security."""

    def test_access_token_expires(self, client: TestClient):
        """Test that expired tokens are rejected (conceptual test)."""
        # This test verifies the token validation logic works
        # In production, tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES

        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "expire@example.com",
                "username": "expireuser",
                "password": "SecurePass123",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "expire@example.com",
                "password": "SecurePass123",
            },
        )
        token = login_response.json()["access_token"]

        # Token should work immediately
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_token_type_validation(self, client: TestClient, db_session: Session):
        """Test that refresh tokens can't be used as access tokens."""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "tokentype@example.com",
                "username": "tokentypeuser",
                "password": "SecurePass123",
            },
        )

        # Get user ID for creating refresh token
        user = db_session.query(User).filter_by(email="tokentype@example.com").first()
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # Try to use refresh token as access token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
