"""
GraphQL Context

Provides request context to all GraphQL resolvers including:
- Database session for queries
- Current authenticated user (if any)
- Request information

The context is created fresh for each GraphQL request and passed
to all resolvers via the `info` parameter.
"""

from typing import TYPE_CHECKING

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext

from app.database import SessionLocal
from app.services.security import verify_token_type

if TYPE_CHECKING:
    from app.models.user import User


class GraphQLContext(BaseContext):
    """
    Context object available to all GraphQL resolvers.

    Inherits from Strawberry's BaseContext for proper integration.

    Attributes:
        db: SQLAlchemy database session
        user: Currently authenticated user (None if not authenticated)
    """

    def __init__(self, db: Session, user: "User | None" = None):
        self.db = db
        self.user = user


def get_user_from_token(db: Session, token: str | None) -> "User | None":
    """
    Extract and validate user from JWT token.

    Args:
        db: Database session
        token: JWT access token (without 'Bearer ' prefix)

    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        return None

    from app.models.user import User

    # Verify token and extract payload
    payload = verify_token_type(token, "access")
    if payload is None:
        return None

    # Get user ID from token
    user_id = payload.get("sub")
    if user_id is None:
        return None

    # Fetch user from database
    stmt = select(User).where(User.id == int(user_id))
    user = db.execute(stmt).scalar_one_or_none()

    # Check if user is active
    if user and not user.is_active:
        return None

    return user


async def get_context(request: Request) -> GraphQLContext:
    """
    Create GraphQL context for each request.

    This function is called by Strawberry for every GraphQL request.
    It extracts the JWT token from the Authorization header and
    creates a database session.

    Args:
        request: FastAPI request object

    Returns:
        GraphQLContext with db session and optional user
    """
    # Create database session
    db = SessionLocal()

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove 'Bearer ' prefix

    # Get user from token (if valid)
    user = get_user_from_token(db, token)

    return GraphQLContext(db=db, user=user)
