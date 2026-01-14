"""
Books API Application Package

This is the main application package for the Books API.
All core modules, routers, and utilities are organized within this package.

Package Structure:
- config.py: Application configuration using Pydantic Settings
- database.py: SQLAlchemy database connection and session management
- main.py: FastAPI application factory and configuration
- dependencies.py: Dependency injection functions
- models/: SQLAlchemy ORM models
- schemas/: Pydantic request/response schemas
- routers/: API route handlers
- services/: Business logic (caching, rate limiting)
- utils/: Helper functions
"""

__version__ = "0.1.0"
