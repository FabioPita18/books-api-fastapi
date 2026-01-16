"""
API Key Pydantic Schemas

These schemas define the shape of data for API key operations.

Security Note:
- APIKeyCreate returns the full key ONCE during creation
- APIKeyResponse never includes the actual key, only the prefix
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreate(BaseModel):
    """
    Schema for creating a new API key.

    Only requires a name. Optionally accepts description and expiration.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the API key",
        examples=["Production App", "Mobile Client", "Testing"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional description of the key's purpose",
        examples=["Key for the production web application"],
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration date (null = never expires)",
        examples=["2025-12-31T23:59:59Z"],
    )


class APIKeyCreatedResponse(BaseModel):
    """
    Response when a new API key is created.

    IMPORTANT: This is the ONLY time the full key is shown.
    Store it securely - it cannot be retrieved again!
    """

    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key: str = Field(
        ...,
        description="The full API key. SAVE THIS - it won't be shown again!",
    )
    key_prefix: str = Field(
        ...,
        description="Key prefix for identification",
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Production App",
                "key": "bk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                "key_prefix": "bk_a1b2c3d4",
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class APIKeyResponse(BaseModel):
    """
    Schema for API key responses.

    Never includes the actual key - only the prefix for identification.
    """

    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key_prefix: str = Field(
        ...,
        description="Key prefix for identification (first 12 chars)",
    )
    description: Optional[str] = Field(
        None,
        description="Key description",
    )
    is_active: bool = Field(..., description="Whether the key is active")
    expires_at: Optional[datetime] = Field(
        None,
        description="Expiration date (null = never)",
    )
    last_used_at: Optional[datetime] = Field(
        None,
        description="When the key was last used",
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Production App",
                "key_prefix": "bk_a1b2c3d4",
                "description": "Key for the production web application",
                "is_active": True,
                "expires_at": None,
                "last_used_at": "2024-01-20T15:45:00Z",
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )
