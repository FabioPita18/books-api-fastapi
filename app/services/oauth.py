"""
OAuth Service

Handles OAuth authentication with external providers (Google, GitHub).

This service:
1. Generates authorization URLs for OAuth providers
2. Handles OAuth callbacks and token exchange
3. Extracts user information from OAuth responses
4. Creates or links user accounts

Supported Providers:
- Google (email, profile)
- GitHub (user, user:email)
"""

import logging
from dataclasses import dataclass

import httpx
from authlib.integrations.starlette_client import OAuth

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# OAuth Client Configuration
# =============================================================================

oauth = OAuth()

# Register Google OAuth
if settings.google_client_id:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )

# Register GitHub OAuth
if settings.github_client_id:
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={
            "scope": "user:email",
        },
    )


# =============================================================================
# OAuth User Data
# =============================================================================


@dataclass
class OAuthUserData:
    """
    Normalized user data from OAuth providers.

    Different providers return data in different formats.
    This class normalizes the data for consistent handling.
    """

    email: str
    provider: str  # 'google' or 'github'
    provider_user_id: str
    full_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None  # GitHub provides username, Google doesn't


# =============================================================================
# Google OAuth Functions
# =============================================================================


async def get_google_auth_url(redirect_uri: str) -> str:
    """
    Generate Google OAuth authorization URL.

    Args:
        redirect_uri: URL to redirect to after authorization

    Returns:
        Authorization URL to redirect user to
    """
    if not settings.google_client_id:
        raise ValueError("Google OAuth not configured")

    # Build authorization URL manually for simplicity
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    query = "&".join(f"{k}={v}" for k, v in params.items())

    return f"{base_url}?{query}"


async def handle_google_callback(code: str, redirect_uri: str) -> OAuthUserData:
    """
    Handle Google OAuth callback.

    1. Exchange authorization code for access token
    2. Fetch user info from Google API
    3. Return normalized user data

    Args:
        code: Authorization code from Google
        redirect_uri: Redirect URI (must match the one used in auth URL)

    Returns:
        OAuthUserData with user information
    """
    if not settings.google_client_id:
        raise ValueError("Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

        if token_response.status_code != 200:
            logger.error(f"Google token exchange failed: {token_response.text}")
            raise ValueError("Failed to exchange code for token")

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Fetch user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            logger.error(f"Google user info failed: {user_response.text}")
            raise ValueError("Failed to fetch user info")

        user_data = user_response.json()

        logger.info(f"Google OAuth successful for: {user_data.get('email')}")

        return OAuthUserData(
            email=user_data["email"],
            provider="google",
            provider_user_id=user_data["id"],
            full_name=user_data.get("name"),
            avatar_url=user_data.get("picture"),
        )


# =============================================================================
# GitHub OAuth Functions
# =============================================================================


async def get_github_auth_url(redirect_uri: str) -> str:
    """
    Generate GitHub OAuth authorization URL.

    Args:
        redirect_uri: URL to redirect to after authorization

    Returns:
        Authorization URL to redirect user to
    """
    if not settings.github_client_id:
        raise ValueError("GitHub OAuth not configured")

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
    }

    base_url = "https://github.com/login/oauth/authorize"
    query = "&".join(f"{k}={v}" for k, v in params.items())

    return f"{base_url}?{query}"


async def handle_github_callback(code: str, redirect_uri: str) -> OAuthUserData:
    """
    Handle GitHub OAuth callback.

    1. Exchange authorization code for access token
    2. Fetch user info from GitHub API
    3. Fetch user email (may be private)
    4. Return normalized user data

    Args:
        code: Authorization code from GitHub
        redirect_uri: Redirect URI (must match the one used in auth URL)

    Returns:
        OAuthUserData with user information
    """
    if not settings.github_client_id:
        raise ValueError("GitHub OAuth not configured")

    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            logger.error(f"GitHub token exchange failed: {token_response.text}")
            raise ValueError("Failed to exchange code for token")

        token_data = token_response.json()

        if "error" in token_data:
            logger.error(f"GitHub OAuth error: {token_data}")
            raise ValueError(token_data.get("error_description", "OAuth failed"))

        access_token = token_data["access_token"]

        # Fetch user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if user_response.status_code != 200:
            logger.error(f"GitHub user info failed: {user_response.text}")
            raise ValueError("Failed to fetch user info")

        user_data = user_response.json()

        # GitHub email might be private, fetch from emails endpoint
        email = user_data.get("email")
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            if emails_response.status_code == 200:
                emails = emails_response.json()
                # Get primary verified email
                for e in emails:
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break
                # Fallback to first verified email
                if not email:
                    for e in emails:
                        if e.get("verified"):
                            email = e["email"]
                            break

        if not email:
            raise ValueError("Could not get email from GitHub")

        logger.info(f"GitHub OAuth successful for: {email}")

        return OAuthUserData(
            email=email,
            provider="github",
            provider_user_id=str(user_data["id"]),
            full_name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
            username=user_data.get("login"),
        )


# =============================================================================
# Helper Functions
# =============================================================================


def is_google_configured() -> bool:
    """Check if Google OAuth is configured."""
    return bool(settings.google_client_id and settings.google_client_secret)


def is_github_configured() -> bool:
    """Check if GitHub OAuth is configured."""
    return bool(settings.github_client_id and settings.github_client_secret)
