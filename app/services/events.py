"""
Event System for Real-Time Broadcasting

Provides event publishing for real-time updates via WebSocket.

Features:
- Event types for books and reviews
- Publish to WebSocket channels
- Optional Redis pub/sub for horizontal scaling
- Background task support to not block responses

Usage:
    from app.services.events import event_publisher, EventType

    # Publish a book created event
    await event_publisher.publish_book_event(
        EventType.BOOK_CREATED,
        book_id=1,
        data={"title": "New Book", "author": "John Doe"}
    )

    # Publish a review event
    await event_publisher.publish_review_event(
        EventType.REVIEW_CREATED,
        book_id=1,
        review_id=1,
        data={"rating": 5, "title": "Great book!"}
    )
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.services.websocket import get_connection_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Event Types
# =============================================================================


class EventType(StrEnum):
    """Types of events that can be published."""

    # Book events
    BOOK_CREATED = "book.created"
    BOOK_UPDATED = "book.updated"
    BOOK_DELETED = "book.deleted"

    # Review events
    REVIEW_CREATED = "review.created"
    REVIEW_UPDATED = "review.updated"
    REVIEW_DELETED = "review.deleted"

    # User events (for private channels)
    USER_NOTIFICATION = "user.notification"
    USER_REVIEW_LIKED = "user.review_liked"


@dataclass
class Event:
    """
    Represents an event to be published.

    Attributes:
        type: The event type
        data: Event payload data
        timestamp: When the event occurred
        channel: Target WebSocket channel(s)
        user_id: Optional user ID for user-specific events
    """

    type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    channel: str | list[str] | None = None
    user_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "channel": self.channel,
        }

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


# =============================================================================
# Event Publisher
# =============================================================================


class EventPublisher:
    """
    Publishes events to WebSocket clients and optionally to Redis.

    The publisher supports:
    - Direct WebSocket broadcasting via ConnectionManager
    - Redis pub/sub for horizontal scaling (multiple server instances)
    - Background task execution to not block API responses
    """

    def __init__(self):
        self._redis_client = None
        self._redis_channel = "books_api_events"

    def _get_redis_client(self):
        """Get Redis client for pub/sub (lazy initialization)."""
        if self._redis_client is None:
            try:
                from app.services.cache import get_redis_client

                self._redis_client = get_redis_client()
            except Exception as e:
                logger.warning(f"Failed to get Redis client for events: {e}")
        return self._redis_client

    async def publish(self, event: Event) -> int:
        """
        Publish an event to WebSocket clients.

        Args:
            event: The event to publish

        Returns:
            Number of clients the event was sent to
        """
        manager = get_connection_manager()
        total_sent = 0

        # Determine channels to broadcast to
        channels = []
        if event.channel:
            if isinstance(event.channel, list):
                channels = event.channel
            else:
                channels = [event.channel]

        # Broadcast to each channel
        message = event.to_dict()
        for channel in channels:
            sent = await manager.broadcast(channel, message)
            total_sent += sent
            logger.debug(f"Published {event.type.value} to channel '{channel}': {sent} clients")

        # Also publish to Redis for other server instances
        await self._publish_to_redis(event)

        return total_sent

    async def _publish_to_redis(self, event: Event) -> bool:
        """
        Publish event to Redis pub/sub for horizontal scaling.

        Other server instances subscribed to the Redis channel will
        receive and broadcast the event to their connected clients.
        """
        redis = self._get_redis_client()
        if redis is None:
            return False

        try:
            redis.publish(self._redis_channel, event.to_json())
            logger.debug(f"Published {event.type.value} to Redis channel")
            return True
        except Exception as e:
            logger.warning(f"Failed to publish to Redis: {e}")
            return False

    async def publish_book_event(
        self,
        event_type: EventType,
        book_id: int,
        data: dict[str, Any],
    ) -> int:
        """
        Publish a book-related event.

        Broadcasts to:
        - "books" channel (all book events)
        - "book:{id}" channel (specific book events)

        Args:
            event_type: Type of book event
            book_id: ID of the book
            data: Event data (book details)

        Returns:
            Number of clients notified
        """
        event = Event(
            type=event_type,
            data={"book_id": book_id, **data},
            channel=["books", f"book:{book_id}"],
        )
        return await self.publish(event)

    async def publish_review_event(
        self,
        event_type: EventType,
        book_id: int,
        review_id: int,
        data: dict[str, Any],
        user_id: int | None = None,
    ) -> int:
        """
        Publish a review-related event.

        Broadcasts to:
        - "reviews" channel (all review events)
        - "book:{id}" channel (reviews for specific book)
        - "user:{id}" channel (if user_id provided, for notifications)

        Args:
            event_type: Type of review event
            book_id: ID of the book being reviewed
            review_id: ID of the review
            data: Event data (review details)
            user_id: Optional user ID for notifications

        Returns:
            Number of clients notified
        """
        channels = ["reviews", f"book:{book_id}"]

        # Add user channel for notifications (e.g., notify book owner)
        if user_id:
            channels.append(f"user:{user_id}")

        event = Event(
            type=event_type,
            data={"book_id": book_id, "review_id": review_id, **data},
            channel=channels,
            user_id=user_id,
        )
        return await self.publish(event)

    async def publish_user_notification(
        self,
        user_id: int,
        notification_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Publish a user-specific notification.

        Broadcasts to:
        - "user:{id}" channel (private user channel)

        Args:
            user_id: ID of the user to notify
            notification_type: Type of notification
            data: Notification data

        Returns:
            Number of clients notified (0 or 1)
        """
        event = Event(
            type=EventType.USER_NOTIFICATION,
            data={"notification_type": notification_type, **data},
            channel=f"user:{user_id}",
            user_id=user_id,
        )
        return await self.publish(event)


# =============================================================================
# Background Task Helper
# =============================================================================


def publish_event_background(event: Event) -> None:
    """
    Publish an event in the background without blocking.

    Use this in API endpoints to not delay the response.

    Usage:
        from fastapi import BackgroundTasks

        @router.post("/books")
        def create_book(background_tasks: BackgroundTasks):
            # ... create book ...
            background_tasks.add_task(
                publish_event_background,
                Event(type=EventType.BOOK_CREATED, data={...}, channel="books")
            )
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(event_publisher.publish(event))
        else:
            loop.run_until_complete(event_publisher.publish(event))
    except RuntimeError:
        # No event loop, create a new one
        asyncio.run(event_publisher.publish(event))


async def publish_book_event_async(
    event_type: EventType,
    book_id: int,
    data: dict[str, Any],
) -> None:
    """Async helper to publish book events."""
    await event_publisher.publish_book_event(event_type, book_id, data)


async def publish_review_event_async(
    event_type: EventType,
    book_id: int,
    review_id: int,
    data: dict[str, Any],
    user_id: int | None = None,
) -> None:
    """Async helper to publish review events."""
    await event_publisher.publish_review_event(
        event_type, book_id, review_id, data, user_id
    )


# =============================================================================
# Global Event Publisher Instance
# =============================================================================

event_publisher = EventPublisher()


def get_event_publisher() -> EventPublisher:
    """Get the global event publisher instance."""
    return event_publisher
