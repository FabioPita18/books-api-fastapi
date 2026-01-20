"""
Services Package

This package contains business logic services that are:
- Separate from HTTP handling (routers)
- Reusable across different parts of the application
- Easier to test in isolation

Current services:
- auth.py: API key authentication and JWT token handling
- cache.py: Redis caching utilities with automatic invalidation
- elasticsearch.py: Elasticsearch client for advanced search
- oauth.py: OAuth social login (Google, GitHub)
- rate_limiter.py: Rate limiting with slowapi and Redis backend
- ratings.py: Book rating aggregation calculations
- recommendations.py: Book recommendation algorithms
- search.py: Advanced search with Elasticsearch/PostgreSQL fallback
- security.py: Password hashing and JWT utilities
"""
