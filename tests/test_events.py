"""
Event System Tests

Tests for the event publishing system including:
- Event creation and serialization
- EventPublisher functionality
- Integration with WebSocket broadcasting
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.events import (
    Event,
    EventPublisher,
    EventType,
    get_event_publisher,
)

# =============================================================================
# Event Tests
# =============================================================================


class TestEventType:
    """Tests for EventType enum."""

    def test_book_event_types(self):
        """Test book event types exist."""
        assert EventType.BOOK_CREATED == "book.created"
        assert EventType.BOOK_UPDATED == "book.updated"
        assert EventType.BOOK_DELETED == "book.deleted"

    def test_review_event_types(self):
        """Test review event types exist."""
        assert EventType.REVIEW_CREATED == "review.created"
        assert EventType.REVIEW_UPDATED == "review.updated"
        assert EventType.REVIEW_DELETED == "review.deleted"

    def test_user_event_types(self):
        """Test user event types exist."""
        assert EventType.USER_NOTIFICATION == "user.notification"


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.BOOK_CREATED,
            data={"title": "Test Book", "author": "Test Author"},
            channel="books",
        )

        assert event.type == EventType.BOOK_CREATED
        assert event.data["title"] == "Test Book"
        assert event.channel == "books"
        assert event.timestamp is not None

    def test_event_with_custom_timestamp(self):
        """Test creating an event with custom timestamp."""
        custom_time = datetime(2024, 1, 20, 12, 0, 0, tzinfo=UTC)
        event = Event(
            type=EventType.BOOK_UPDATED,
            data={"id": 1},
            timestamp=custom_time,
        )

        assert event.timestamp == custom_time

    def test_event_with_multiple_channels(self):
        """Test creating an event with multiple channels."""
        event = Event(
            type=EventType.REVIEW_CREATED,
            data={"rating": 5},
            channel=["reviews", "book:1"],
        )

        assert event.channel == ["reviews", "book:1"]

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = Event(
            type=EventType.BOOK_CREATED,
            data={"title": "Test"},
            channel="books",
        )

        result = event.to_dict()

        assert result["type"] == "book.created"
        assert result["data"] == {"title": "Test"}
        assert result["channel"] == "books"
        assert "timestamp" in result

    def test_event_to_json(self):
        """Test converting event to JSON."""
        event = Event(
            type=EventType.BOOK_DELETED,
            data={"id": 1},
            channel="books",
        )

        json_str = event.to_json()

        assert '"type": "book.deleted"' in json_str
        assert '"data": {"id": 1}' in json_str


# =============================================================================
# EventPublisher Tests
# =============================================================================


class TestEventPublisher:
    """Tests for EventPublisher class."""

    def test_publisher_creation(self):
        """Test creating an event publisher."""
        publisher = EventPublisher()
        assert publisher is not None

    @pytest.mark.asyncio
    async def test_publish_book_event(self):
        """Test publishing a book event."""
        publisher = EventPublisher()

        # Mock the connection manager
        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=2)
            mock_get_manager.return_value = mock_manager

            sent = await publisher.publish_book_event(
                EventType.BOOK_CREATED,
                book_id=1,
                data={"title": "New Book"},
            )

            # Should broadcast to both "books" and "book:1" channels
            assert mock_manager.broadcast.call_count == 2
            assert sent == 4  # 2 clients per channel

    @pytest.mark.asyncio
    async def test_publish_review_event(self):
        """Test publishing a review event."""
        publisher = EventPublisher()

        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=1)
            mock_get_manager.return_value = mock_manager

            await publisher.publish_review_event(
                EventType.REVIEW_CREATED,
                book_id=1,
                review_id=5,
                data={"rating": 5},
            )

            # Should broadcast to "reviews" and "book:1" channels
            assert mock_manager.broadcast.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_review_event_with_user_notification(self):
        """Test publishing a review event with user notification."""
        publisher = EventPublisher()

        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=1)
            mock_get_manager.return_value = mock_manager

            await publisher.publish_review_event(
                EventType.REVIEW_CREATED,
                book_id=1,
                review_id=5,
                data={"rating": 5},
                user_id=10,  # Notify user 10
            )

            # Should broadcast to "reviews", "book:1", and "user:10" channels
            assert mock_manager.broadcast.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_user_notification(self):
        """Test publishing a user notification."""
        publisher = EventPublisher()

        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=1)
            mock_get_manager.return_value = mock_manager

            await publisher.publish_user_notification(
                user_id=5,
                notification_type="new_follower",
                data={"follower_name": "John"},
            )

            # Should broadcast to "user:5" channel
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            assert call_args[0][0] == "user:5"

    @pytest.mark.asyncio
    async def test_publish_to_empty_channel(self):
        """Test publishing to a channel with no subscribers."""
        publisher = EventPublisher()

        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=0)  # No subscribers
            mock_get_manager.return_value = mock_manager

            sent = await publisher.publish_book_event(
                EventType.BOOK_CREATED,
                book_id=1,
                data={"title": "Test"},
            )

            assert sent == 0


class TestEventPublisherRedis:
    """Tests for EventPublisher Redis integration."""

    @pytest.mark.asyncio
    async def test_publish_to_redis(self):
        """Test that events are published to Redis."""
        publisher = EventPublisher()

        # Mock both the connection manager and Redis
        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=0)
            mock_get_manager.return_value = mock_manager

            # Mock Redis client
            mock_redis = MagicMock()
            publisher._redis_client = mock_redis

            event = Event(
                type=EventType.BOOK_CREATED,
                data={"id": 1},
                channel="books",
            )

            await publisher.publish(event)

            # Should attempt to publish to Redis
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_continues_on_redis_failure(self):
        """Test that publishing continues even if Redis fails."""
        publisher = EventPublisher()

        with patch("app.services.events.get_connection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(return_value=1)
            mock_get_manager.return_value = mock_manager

            # Mock Redis client that raises an exception
            mock_redis = MagicMock()
            mock_redis.publish.side_effect = Exception("Redis error")
            publisher._redis_client = mock_redis

            event = Event(
                type=EventType.BOOK_CREATED,
                data={"id": 1},
                channel="books",
            )

            # Should not raise an exception
            sent = await publisher.publish(event)

            # WebSocket broadcast should still work
            assert sent == 1


# =============================================================================
# Global Event Publisher Tests
# =============================================================================


class TestGlobalEventPublisher:
    """Tests for the global event publisher instance."""

    def test_get_event_publisher(self):
        """Test getting the global event publisher."""
        publisher = get_event_publisher()
        assert publisher is not None
        assert isinstance(publisher, EventPublisher)

    def test_get_event_publisher_returns_same_instance(self):
        """Test that get_event_publisher returns the same instance."""
        publisher1 = get_event_publisher()
        publisher2 = get_event_publisher()
        assert publisher1 is publisher2
