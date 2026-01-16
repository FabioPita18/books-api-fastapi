"""
API Keys Router

Endpoints for managing API keys.

Security Notes:
- Creating and revoking keys requires admin authentication
- The full key is only shown once during creation
- Keys are stored as hashes (never plain text)
"""


from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbSession, RequireAPIKey
from app.models import APIKey
from app.schemas import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse
from app.services.auth import create_api_key, revoke_api_key
from app.services.rate_limiter import limiter

settings = get_settings()

router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
    responses={
        401: {"description": "Unauthorized - API key required"},
        404: {"description": "API key not found"},
    },
)


@router.post(
    "/",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Create a new API key. Requires admin authentication. "
                "The full key is only shown once in the response - save it securely!",
)
@limiter.limit(settings.rate_limit_write)
def create_new_api_key(
    request: Request,
    key_data: APIKeyCreate,
    db: DbSession,
    _: RequireAPIKey,  # Requires authentication
) -> APIKeyCreatedResponse:
    """
    Create a new API key.

    IMPORTANT: The full key is only returned in this response.
    It cannot be retrieved again - store it securely!
    """
    plain_key, api_key = create_api_key(
        db=db,
        name=key_data.name,
        description=key_data.description,
        expires_at=key_data.expires_at,
    )

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get(
    "/",
    response_model=list[APIKeyResponse],
    summary="List all API keys",
    description="List all API keys. Requires authentication. "
                "Does not return the actual keys, only prefixes.",
)
@limiter.limit(settings.rate_limit_default)
def list_api_keys(
    request: Request,
    db: DbSession,
    _: RequireAPIKey,  # Requires authentication
) -> list[APIKeyResponse]:
    """
    List all API keys.

    Only returns key metadata (never the actual keys).
    """
    stmt = select(APIKey).order_by(APIKey.created_at.desc())
    keys = db.execute(stmt).scalars().all()
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="Get details about a specific API key. Requires authentication.",
)
@limiter.limit(settings.rate_limit_default)
def get_api_key(
    request: Request,
    key_id: int,
    db: DbSession,
    _: RequireAPIKey,  # Requires authentication
) -> APIKeyResponse:
    """
    Get details about a specific API key.

    Only returns metadata (never the actual key).
    """
    stmt = select(APIKey).where(APIKey.id == key_id)
    api_key = db.execute(stmt).scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with id {key_id} not found",
        )

    return APIKeyResponse.model_validate(api_key)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    description="Revoke (deactivate) an API key. Requires authentication. "
                "The key will no longer work for authentication.",
)
@limiter.limit(settings.rate_limit_write)
def revoke_key(
    request: Request,
    key_id: int,
    db: DbSession,
    _: RequireAPIKey,  # Requires authentication
) -> None:
    """
    Revoke an API key.

    The key is not deleted, but marked as inactive.
    It will no longer work for authentication.
    """
    api_key = revoke_api_key(db, key_id)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with id {key_id} not found",
        )
