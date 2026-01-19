"""
Authentication Router

Handles user authentication endpoints:
- Registration (email/password)
- Login (email/password → JWT tokens)
- Token refresh (refresh token → new access token)
- Logout (invalidate refresh token)
- Get current user (from JWT token)
- OAuth callbacks (Phase 3C)

Security:
=========
- Passwords are hashed with bcrypt before storage
- Plain text passwords are never logged or stored
- JWT tokens are used for session management
- Access tokens are short-lived (15 min default)
- Refresh tokens are longer-lived (7 days default)
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import ActiveUser, DbSession
from app.models.user import AuthProvider, User
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.rate_limiter import limiter
from app.services.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token_type,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        409: {"description": "Conflict (email/username already exists)"},
    },
)


# -------------------------------------------------------------------------
# Registration Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Create a new user account with email and password.

    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    **Username Requirements:**
    - 3-50 characters
    - Must start with a letter
    - Only letters, numbers, and underscores
    """,
)
@limiter.limit("5/minute")  # Strict rate limit to prevent spam registrations
def register(
    request: Request,
    user_data: UserCreate,
    db: DbSession,
) -> UserResponse:
    """
    Register a new user with email and password.

    1. Validates email and password format (handled by Pydantic)
    2. Checks for duplicate email/username
    3. Hashes password with bcrypt
    4. Creates user record
    5. Returns user data (without password)
    """
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    existing_email = db.execute(stmt).scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username already exists
    stmt = select(User).where(User.username == user_data.username.lower())
    existing_username = db.execute(stmt).scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create new user with hashed password
    user = User(
        email=user_data.email,
        username=user_data.username.lower(),  # Normalize to lowercase
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        auth_provider=AuthProvider.LOCAL.value,
        is_active=True,
        is_verified=False,  # Email verification not implemented yet
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    return UserResponse.model_validate(user)


# -------------------------------------------------------------------------
# Login Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="""
    Authenticate with email and password to receive JWT tokens.

    **Returns:**
    - `access_token`: Short-lived token for API authentication (15 min)
    - `token_type`: Always "bearer"
    - `expires_in`: Token lifetime in seconds

    **Refresh Token:**
    A refresh token is also set as an httpOnly cookie for security.
    Use the `/auth/refresh` endpoint to get a new access token.

    **Usage:**
    Include the access token in the Authorization header:
    ```
    Authorization: Bearer <access_token>
    ```

    **Note:** Use email address in the 'username' field (OAuth2 standard).
    """,
)
@limiter.limit("10/minute")  # Rate limit login attempts
def login(
    request: Request,
    response: Response,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Uses OAuth2 password flow (form data with username/password).
    The 'username' field should contain the user's email address.

    The refresh token is set as an httpOnly cookie for security.
    """
    email = form_data.username  # OAuth2 uses 'username' field for the identifier
    password = form_data.password

    # Look up user by email
    stmt = select(User).where(User.email == email)
    user = db.execute(stmt).scalar_one_or_none()

    # Check if user exists and password is correct
    if not user or not user.hashed_password:
        logger.warning(f"Login failed: user not found for {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Login failed: incorrect password for {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: inactive account {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last login timestamp
    user.last_login_at = datetime.now(UTC)
    db.commit()

    # Set refresh token as httpOnly cookie (more secure than returning in body)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # Not accessible via JavaScript
        secure=settings.environment == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,  # Days to seconds
    )

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,  # Minutes to seconds
    )


# -------------------------------------------------------------------------
# Token Refresh Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Get a new access token using a refresh token.

    **Methods:**
    1. **Cookie (recommended)**: Refresh token from httpOnly cookie (automatic)
    2. **Body**: Pass refresh_token in request body

    Returns a new access token. The refresh token remains valid.
    """,
)
def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
    body: RefreshTokenRequest = None,
) -> TokenResponse:
    """
    Exchange refresh token for new access token.

    Checks for refresh token in:
    1. Request body (RefreshTokenRequest)
    2. Cookie (refresh_token)
    """
    # Get refresh token from body or cookie
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    else:
        token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the refresh token
    payload = verify_token_type(token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    stmt = select(User).where(User.id == int(user_id))
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create new access token
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)

    logger.info(f"Token refreshed for user: {user.email}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


# -------------------------------------------------------------------------
# Logout Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="""
    Logout the current user by clearing the refresh token cookie.

    **Note:** This only clears the cookie. The access token remains valid
    until it expires (15 min default). For immediate token invalidation,
    consider implementing a token blacklist with Redis.
    """,
)
def logout(
    response: Response,
    current_user: ActiveUser,
) -> None:
    """
    Logout user by clearing refresh token cookie.

    The access token will naturally expire. For high-security applications,
    implement a token blacklist in Redis.
    """
    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )

    logger.info(f"User logged out: {current_user.email}")

    return None


# -------------------------------------------------------------------------
# Get Current User Endpoint
# -------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="""
    Get the currently authenticated user's profile.

    Requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <access_token>
    ```
    """,
)
def get_me(
    current_user: ActiveUser,
) -> UserResponse:
    """
    Return the current authenticated user's profile.

    Uses the ActiveUser dependency which:
    1. Extracts and validates the JWT token
    2. Looks up the user in the database
    3. Verifies the user is active
    """
    return UserResponse.model_validate(current_user)


# =============================================================================
# OAuth Endpoints (Social Login)
# =============================================================================


@router.get(
    "/google",
    summary="Login with Google",
    description="""
    Redirect to Google OAuth login page.

    After successful authentication, Google will redirect back to
    `/api/v1/auth/google/callback` with an authorization code.
    """,
    responses={
        302: {"description": "Redirect to Google OAuth"},
        400: {"description": "Google OAuth not configured"},
    },
)
async def google_login(request: Request):
    """Redirect to Google OAuth authorization page."""
    from starlette.responses import RedirectResponse

    from app.services.oauth import get_google_auth_url, is_google_configured

    if not is_google_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    redirect_uri = settings.google_redirect_uri
    auth_url = await get_google_auth_url(redirect_uri)

    return RedirectResponse(url=auth_url)


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="""
    Handle Google OAuth callback after user authorizes.

    This endpoint:
    1. Exchanges the authorization code for tokens
    2. Fetches user info from Google
    3. Creates or links user account
    4. Returns JWT tokens
    """,
)
async def google_callback(
    request: Request,
    response: Response,
    db: DbSession,
    code: str = None,
    error: str = None,
):
    """Handle Google OAuth callback."""
    from app.services.oauth import handle_google_callback, is_google_configured

    if not is_google_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code required",
        )

    try:
        oauth_data = await handle_google_callback(code, settings.google_redirect_uri)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    # Find or create user
    user = await _get_or_create_oauth_user(db, oauth_data)

    # Generate tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last login
    user.last_login_at = datetime.now(UTC)
    db.commit()

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    logger.info(f"Google OAuth login: {user.email}")

    # For API testing, return JSON. For frontend, redirect with token.
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get(
    "/github",
    summary="Login with GitHub",
    description="""
    Redirect to GitHub OAuth login page.

    After successful authentication, GitHub will redirect back to
    `/api/v1/auth/github/callback` with an authorization code.
    """,
    responses={
        302: {"description": "Redirect to GitHub OAuth"},
        400: {"description": "GitHub OAuth not configured"},
    },
)
async def github_login(request: Request):
    """Redirect to GitHub OAuth authorization page."""
    from starlette.responses import RedirectResponse

    from app.services.oauth import get_github_auth_url, is_github_configured

    if not is_github_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth is not configured",
        )

    redirect_uri = settings.github_redirect_uri
    auth_url = await get_github_auth_url(redirect_uri)

    return RedirectResponse(url=auth_url)


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback",
    description="""
    Handle GitHub OAuth callback after user authorizes.

    This endpoint:
    1. Exchanges the authorization code for tokens
    2. Fetches user info from GitHub
    3. Creates or links user account
    4. Returns JWT tokens
    """,
)
async def github_callback(
    request: Request,
    response: Response,
    db: DbSession,
    code: str = None,
    error: str = None,
):
    """Handle GitHub OAuth callback."""
    from app.services.oauth import handle_github_callback, is_github_configured

    if not is_github_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth is not configured",
        )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code required",
        )

    try:
        oauth_data = await handle_github_callback(code, settings.github_redirect_uri)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    # Find or create user
    user = await _get_or_create_oauth_user(db, oauth_data)

    # Generate tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last login
    user.last_login_at = datetime.now(UTC)
    db.commit()

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    logger.info(f"GitHub OAuth login: {user.email}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


# =============================================================================
# OAuth Helper Functions
# =============================================================================


async def _get_or_create_oauth_user(db, oauth_data) -> User:
    """
    Get existing user or create new one from OAuth data.

    Account linking rules:
    1. If provider_user_id matches existing OAuth user, return that user
    2. If email matches existing user, link OAuth to that account
    3. Otherwise, create new user

    Args:
        db: Database session
        oauth_data: Normalized OAuth user data

    Returns:
        User object (existing or newly created)
    """
    from app.services.oauth import OAuthUserData

    oauth_data: OAuthUserData = oauth_data

    # Check for existing OAuth user (same provider + provider_user_id)
    stmt = select(User).where(
        User.auth_provider == oauth_data.provider,
        User.provider_user_id == oauth_data.provider_user_id,
    )
    existing_oauth_user = db.execute(stmt).scalar_one_or_none()

    if existing_oauth_user:
        logger.info(f"Found existing OAuth user: {existing_oauth_user.email}")
        return existing_oauth_user

    # Check for existing user with same email (link accounts)
    stmt = select(User).where(User.email == oauth_data.email)
    existing_email_user = db.execute(stmt).scalar_one_or_none()

    if existing_email_user:
        # Link OAuth to existing account
        logger.info(f"Linking OAuth to existing user: {existing_email_user.email}")
        existing_email_user.auth_provider = oauth_data.provider
        existing_email_user.provider_user_id = oauth_data.provider_user_id
        if oauth_data.avatar_url and not existing_email_user.avatar_url:
            existing_email_user.avatar_url = oauth_data.avatar_url
        db.commit()
        return existing_email_user

    # Create new user
    # Generate username from email or OAuth username
    base_username = oauth_data.username or oauth_data.email.split("@")[0]
    username = base_username.lower()

    # Ensure username is unique
    counter = 1
    original_username = username
    while True:
        stmt = select(User).where(User.username == username)
        if db.execute(stmt).scalar_one_or_none() is None:
            break
        username = f"{original_username}{counter}"
        counter += 1

    new_user = User(
        email=oauth_data.email,
        username=username,
        full_name=oauth_data.full_name,
        avatar_url=oauth_data.avatar_url,
        auth_provider=oauth_data.provider,
        provider_user_id=oauth_data.provider_user_id,
        is_active=True,
        is_verified=True,  # OAuth emails are considered verified
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Created new OAuth user: {new_user.email}")

    return new_user
