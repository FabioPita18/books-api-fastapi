"""
API Routers Package

This package contains FastAPI routers that handle API endpoints.

WHY Routers?
============
1. Organization: Group related endpoints together
2. Modularity: Each router can have its own prefix, tags, dependencies
3. Maintainability: Easy to find and modify endpoint code
4. Scalability: Add new routers without changing existing code

Router Structure:
- books.py: /api/v1/books/* endpoints
- authors.py: /api/v1/authors/* endpoints
- genres.py: /api/v1/genres/* endpoints
- api_keys.py: /api/v1/api-keys/* endpoints
- auth.py: /api/v1/auth/* endpoints (registration, login, OAuth)

Each router is imported and registered in main.py.
"""

from app.routers.api_keys import router as api_keys_router
from app.routers.auth import router as auth_router
from app.routers.authors import router as authors_router
from app.routers.books import router as books_router
from app.routers.genres import router as genres_router
from app.routers.reviews import router as reviews_router
from app.routers.search import router as search_router
from app.routers.users import router as users_router

__all__ = [
    "books_router",
    "authors_router",
    "genres_router",
    "api_keys_router",
    "auth_router",
    "reviews_router",
    "search_router",
    "users_router",
]
