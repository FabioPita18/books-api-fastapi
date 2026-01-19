"""
Pydantic Schemas Package

This package contains Pydantic models for request/response validation.

WHY Separate Schemas from SQLAlchemy Models?
============================================
1. Security: Control exactly what data is exposed in API responses
2. Validation: Different rules for create vs update vs response
3. Decoupling: Database schema can evolve independently of API
4. Documentation: Schemas generate OpenAPI documentation

Schema Naming Convention:
- XxxBase: Shared fields between create/update
- XxxCreate: Fields required when creating a new record
- XxxUpdate: Fields allowed when updating (usually all optional)
- XxxResponse: Fields returned in API responses
- XxxInDB: Internal representation (usually not exposed)
"""

# Import all schemas for easy access
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
)
from app.schemas.author import (
    AuthorBase,
    AuthorCreate,
    AuthorResponse,
    AuthorUpdate,
)
from app.schemas.book import (
    BookBase,
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
)
from app.schemas.genre import (
    GenreBase,
    GenreCreate,
    GenreResponse,
    GenreUpdate,
)
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserInDB,
    UserPublicResponse,
    UserResponse,
    UserUpdate,
)
from app.schemas.review import (
    BookRatingStats,
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewResponseSimple,
    ReviewUpdate,
)

__all__ = [
    # Author schemas
    "AuthorBase",
    "AuthorCreate",
    "AuthorUpdate",
    "AuthorResponse",
    # Genre schemas
    "GenreBase",
    "GenreCreate",
    "GenreUpdate",
    "GenreResponse",
    # Book schemas
    "BookBase",
    "BookCreate",
    "BookUpdate",
    "BookResponse",
    "BookListResponse",
    # API Key schemas
    "APIKeyCreate",
    "APIKeyCreatedResponse",
    "APIKeyResponse",
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserPublicResponse",
    "UserInDB",
    "PasswordChange",
    # Auth/Token schemas
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    # Review schemas
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "ReviewResponseSimple",
    "ReviewListResponse",
    "BookRatingStats",
]
