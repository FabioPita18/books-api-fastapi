"""
WebSocket Connection Manager

Manages WebSocket connections for real-time updates.

Features:
- Channel-based subscriptions (books, reviews, book:{id}, user:{id})
- Connection tracking per channel
- Broadcast messages to all subscribers
- Authentication support for private channels

Usage:
    manager = ConnectionManager()
    await manager.connect(websocket, "books")
    await manager.broadcast("books", {"type": "book.created", "data": {...}})
    manager.disconnect(websocket, "books")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """Types of WebSocket channels."""

    BOOKS = "books"  # All book events
    REVIEWS = "reviews"  # All review events
    BOOK = "book"  # Specific book events (book:{id})
    USER = "user"  # User-specific events (user:{id})


@dataclass
class Connection:
    """Represents a WebSocket connection with metadata."""

    websocket: WebSocket
    user_id: int | None = None
    authenticated: bool = False
    connected_at: datetime = field(default_factory=datetime.utcnow)


class ConnectionManager:
    """
    Manages WebSocket connections across multiple channels.

    Channels:
    - "books": Public channel for all book events
    - "reviews": Public channel for all review events
    - "book:{id}": Events for a specific book
    - "user:{id}": Private channel for user-specific notifications

    Authentication:
    - Public channels (books, reviews, book:{id}) don't require auth
    - Private channels (user:{id}) require authentication
    """

    def __init__(self):
        # Map of channel -> list of connections
        self.active_connections: dict[str, list[Connection]] = {}
        # Map of websocket -> set of channels (for cleanup)
        self.websocket_channels: dict[WebSocket, set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        channel: str,
        user_id: int | None = None,
    ) -> bool:
        """
        Connect a WebSocket to a channel.

        Args:
            websocket: The WebSocket connection
            channel: Channel name to subscribe to
            user_id: Optional user ID (for authentication)

        Returns:
            True if connection successful, False if unauthorized
        """
        # Check if private channel requires auth
        if channel.startswith("user:"):
            if user_id is None:
                logger.warning(f"Unauthorized attempt to join private channel: {channel}")
                return False

            # Verify user is accessing their own channel
            channel_user_id = channel.split(":")[1]
            if str(user_id) != channel_user_id:
                logger.warning(
                    f"User {user_id} tried to access channel for user {channel_user_id}"
                )
                return False

        await websocket.accept()

        # Create connection record
        connection = Connection(
            websocket=websocket,
            user_id=user_id,
            authenticated=user_id is not None,
        )

        # Add to channel
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(connection)

        # Track which channels this websocket is in
        if websocket not in self.websocket_channels:
            self.websocket_channels[websocket] = set()
        self.websocket_channels[websocket].add(channel)

        logger.info(
            f"WebSocket connected to channel '{channel}' "
            f"(user_id={user_id}, total in channel={len(self.active_connections[channel])})"
        )

        return True

    def disconnect(self, websocket: WebSocket, channel: str | None = None) -> None:
        """
        Disconnect a WebSocket from a channel or all channels.

        Args:
            websocket: The WebSocket connection
            channel: Specific channel to disconnect from, or None for all
        """
        if channel:
            # Disconnect from specific channel
            self._remove_from_channel(websocket, channel)
        else:
            # Disconnect from all channels
            channels = self.websocket_channels.get(websocket, set()).copy()
            for ch in channels:
                self._remove_from_channel(websocket, ch)

        # Clean up websocket tracking
        if websocket in self.websocket_channels:
            if not channel or not self.websocket_channels[websocket]:
                del self.websocket_channels[websocket]

    def _remove_from_channel(self, websocket: WebSocket, channel: str) -> None:
        """Remove a websocket from a specific channel."""
        if channel in self.active_connections:
            self.active_connections[channel] = [
                conn
                for conn in self.active_connections[channel]
                if conn.websocket != websocket
            ]

            # Clean up empty channels
            if not self.active_connections[channel]:
                del self.active_connections[channel]

        # Update websocket tracking
        if websocket in self.websocket_channels:
            self.websocket_channels[websocket].discard(channel)

        logger.info(f"WebSocket disconnected from channel '{channel}'")

    async def broadcast(self, channel: str, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connections in a channel.

        Args:
            channel: Channel to broadcast to
            message: Message dictionary to send

        Returns:
            Number of connections the message was sent to
        """
        if channel not in self.active_connections:
            return 0

        sent_count = 0
        failed_connections: list[Connection] = []

        for connection in self.active_connections[channel]:
            try:
                await connection.websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                failed_connections.append(connection)

        # Clean up failed connections
        for conn in failed_connections:
            self.disconnect(conn.websocket, channel)

        logger.debug(
            f"Broadcast to channel '{channel}': {sent_count} sent, "
            f"{len(failed_connections)} failed"
        )

        return sent_count

    async def send_personal(
        self,
        user_id: int,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific user's private channel.

        Args:
            user_id: User ID to send to
            message: Message dictionary to send

        Returns:
            True if message was sent, False if user not connected
        """
        channel = f"user:{user_id}"
        sent = await self.broadcast(channel, message)
        return sent > 0

    def get_channel_count(self, channel: str) -> int:
        """Get the number of connections in a channel."""
        return len(self.active_connections.get(channel, []))

    def get_total_connections(self) -> int:
        """Get total number of WebSocket connections."""
        return len(self.websocket_channels)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.get_total_connections(),
            "channels": {
                channel: len(connections)
                for channel, connections in self.active_connections.items()
            },
        }


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
