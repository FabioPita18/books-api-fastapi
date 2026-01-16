"""
API Key Model

Represents API keys for authentication.

Security Features:
- Keys are stored as hashed values (never plain text)
- Supports key expiration
- Tracks last usage for auditing
- Can be revoked without deletion
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class APIKey(Base):
    """
    API Key model for authentication.

    Table: api_keys

    Security Notes:
    - key_hash stores a SHA-256 hash of the actual key
    - The plain key is only shown once during creation
    - key_prefix stores first 8 chars for identification

    Example:
        api_key = APIKey(
            name="Production App",
            key_hash="hashed_value_here",
            key_prefix="bk_live_",
        )
    """

    __tablename__ = "api_keys"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------------------------
    # Key Fields
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name for the API key"
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash of the API key"
    )

    key_prefix: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        comment="First 8 characters of key for identification"
    )

    # -------------------------------------------------------------------------
    # Status & Permissions
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the key is currently active"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the key's purpose"
    )

    # -------------------------------------------------------------------------
    # Expiration
    # -------------------------------------------------------------------------
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the key expires (null = never)"
    )

    # -------------------------------------------------------------------------
    # Audit Fields
    # -------------------------------------------------------------------------
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the key was last used"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the key was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When the key was last updated"
    )

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')"
