"""
WebSocket Tests

Tests for WebSocket functionality including:
- Connection and disconnection
- Channel subscriptions
- Message handling
- Authentication
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.models.user import User
from app.services.security import create_access_token
from app.services.websocket import ConnectionManager

# =============================================================================
# Helper Functions
# =============================================================================


def get_auth_token(user: User) -> str:
    """Generate an auth token for a user."""
    return create_access_token({"sub": str(user.id)})


# =============================================================================
# ConnectionManager Unit Tests
# =============================================================================


class TestConnectionManager:
    """Unit tests for the ConnectionManager class."""

    def test_initial_state(self):
        """Test that ConnectionManager starts with no connections."""
        manager = ConnectionManager()
        assert manager.get_total_connections() == 0
        assert manager.get_stats()["channels"] == {}

    def test_get_channel_count_empty(self):
        """Test channel count for non-existent channel."""
        manager = ConnectionManager()
        assert manager.get_channel_count("books") == 0

    def test_stats_structure(self):
        """Test the stats structure."""
        manager = ConnectionManager()
        stats = manager.get_stats()
        assert "total_connections" in stats
        assert "channels" in stats
        assert isinstance(stats["channels"], dict)


# =============================================================================
# WebSocket Endpoint Tests
# =============================================================================


class TestWebSocketEndpoint:
    """Tests for the WebSocket endpoint."""

    def test_connect_to_public_channel(self, client: TestClient):
        """Test connecting to a public channel."""
        with client.websocket_connect("/ws/books") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["channel"] == "books"
            assert data["authenticated"] is False

    def test_connect_to_book_channel(self, client: TestClient):
        """Test connecting to a specific book channel."""
        with client.websocket_connect("/ws/book:1") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["channel"] == "book:1"

    def test_connect_to_reviews_channel(self, client: TestClient):
        """Test connecting to the reviews channel."""
        with client.websocket_connect("/ws/reviews") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["channel"] == "reviews"

    def test_ping_pong(self, client: TestClient):
        """Test ping/pong keep-alive."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping", "timestamp": "2024-01-20T12:00:00Z"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
            assert data["timestamp"] == "2024-01-20T12:00:00Z"

    def test_unknown_message_type(self, client: TestClient):
        """Test handling of unknown message types."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Unknown message type" in data["message"]


class TestWebSocketAuthentication:
    """Tests for WebSocket authentication."""

    def test_connect_with_token(self, client: TestClient, sample_user: User):
        """Test connecting with a valid JWT token."""
        token = get_auth_token(sample_user)

        with client.websocket_connect(f"/ws/books?token={token}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["authenticated"] is True

    def test_connect_with_invalid_token(self, client: TestClient):
        """Test connecting with an invalid token."""
        with client.websocket_connect("/ws/books?token=invalid_token") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            # Invalid token should result in unauthenticated connection
            assert data["authenticated"] is False

    def test_auth_message(self, client: TestClient, sample_user: User):
        """Test authenticating via message after connection."""
        token = get_auth_token(sample_user)

        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome (unauthenticated)
            data = websocket.receive_json()
            assert data["authenticated"] is False

            # Send auth message
            websocket.send_json({"type": "auth", "token": token})

            # Should receive auth success
            data = websocket.receive_json()
            assert data["type"] == "auth_success"
            assert data["user_id"] == sample_user.id

    def test_auth_message_invalid_token(self, client: TestClient):
        """Test authenticating with invalid token via message."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Send auth with invalid token
            websocket.send_json({"type": "auth", "token": "invalid"})

            # Should receive auth failed
            data = websocket.receive_json()
            assert data["type"] == "auth_failed"


class TestPrivateChannels:
    """Tests for private (user) channels."""

    def test_connect_to_own_user_channel(self, client: TestClient, sample_user: User):
        """Test connecting to own user channel with valid token."""
        token = get_auth_token(sample_user)

        with client.websocket_connect(f"/ws/user:{sample_user.id}?token={token}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["channel"] == f"user:{sample_user.id}"
            assert data["authenticated"] is True

    def test_connect_to_user_channel_without_auth(self, client: TestClient, sample_user: User):
        """Test connecting to user channel without authentication."""
        # Should be rejected (close with 4001)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws/user:{sample_user.id}"):
                # Should not reach here
                pass

    def test_connect_to_other_user_channel(
        self, client: TestClient, sample_user: User, second_user: User
    ):
        """Test connecting to another user's channel."""
        token = get_auth_token(sample_user)

        # Try to connect to second_user's channel with sample_user's token
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/ws/user:{second_user.id}?token={token}"
            ):
                # Should not reach here
                pass


class TestChannelSubscription:
    """Tests for subscribing to additional channels."""

    def test_subscribe_to_additional_channel(self, client: TestClient):
        """Test subscribing to an additional channel after initial connection."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Subscribe to another channel
            websocket.send_json({"type": "subscribe", "channel": "reviews"})

            # Should receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["channel"] == "reviews"

    def test_unsubscribe_from_channel(self, client: TestClient):
        """Test unsubscribing from a channel."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Subscribe to another channel first
            websocket.send_json({"type": "subscribe", "channel": "reviews"})
            websocket.receive_json()  # subscription confirmation

            # Unsubscribe
            websocket.send_json({"type": "unsubscribe", "channel": "reviews"})

            # Should receive unsubscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "unsubscribed"
            assert data["channel"] == "reviews"

    def test_subscribe_to_private_channel_requires_auth(self, client: TestClient, sample_user: User):
        """Test that subscribing to private channels requires authentication."""
        with client.websocket_connect("/ws/books") as websocket:
            # Receive welcome (unauthenticated)
            websocket.receive_json()

            # Try to subscribe to user channel without auth
            websocket.send_json({"type": "subscribe", "channel": f"user:{sample_user.id}"})

            # Should receive subscription failed
            data = websocket.receive_json()
            assert data["type"] == "subscribe_failed"
            assert "Authentication required" in data["message"]


# =============================================================================
# WebSocket Stats Endpoint Tests
# =============================================================================


class TestWebSocketStats:
    """Tests for the WebSocket stats endpoint."""

    def test_get_stats_endpoint(self, client: TestClient):
        """Test the /ws/stats endpoint."""
        response = client.get("/ws/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total_connections" in data
        assert "channels" in data
