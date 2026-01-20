"""
WebSocket Router

Handles WebSocket connections for real-time updates.

Endpoints:
- /ws/{channel}: Subscribe to a channel for real-time updates

Channels:
- "books": All book events (created, updated, deleted)
- "reviews": All review events
- "book:{id}": Events for a specific book
- "user:{id}": Private user notifications (requires auth)

Authentication:
- Pass JWT token as query parameter: /ws/books?token=<jwt>
- Or send token in first message: {"type": "auth", "token": "<jwt>"}
- Private channels require authentication
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.security import verify_token_type
from app.services.websocket import get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["WebSocket"],
)


def get_user_from_token(db: Session, token: str | None) -> User | None:
    """
    Get user from JWT token.

    Args:
        db: Database session
        token: JWT access token

    Returns:
        User if token is valid, None otherwise
    """
    if not token:
        return None

    payload = verify_token_type(token, "access")
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        stmt = select(User).where(User.id == int(user_id))
        user = db.execute(stmt).scalar_one_or_none()
        return user
    except Exception as e:
        logger.warning(f"Error fetching user from token: {e}")
        return None


@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time updates.

    Connect to a channel to receive events. Public channels (books, reviews,
    book:{id}) don't require authentication. Private channels (user:{id})
    require a valid JWT token.

    Authentication options:
    1. Query parameter: /ws/books?token=<jwt>
    2. First message: {"type": "auth", "token": "<jwt>"}

    Message format (received):
    ```json
    {
        "type": "event_type",
        "data": {...},
        "timestamp": "2024-01-20T12:00:00Z"
    }
    ```

    Event types:
    - book.created, book.updated, book.deleted
    - review.created, review.updated, review.deleted
    - notification (for user channels)
    """
    manager = get_connection_manager()

    # Authenticate if token provided
    user = get_user_from_token(db, token)
    user_id = user.id if user else None

    # Try to connect
    connected = await manager.connect(
        websocket=websocket,
        channel=channel,
        user_id=user_id,
    )

    if not connected:
        # Connection rejected (unauthorized for private channel)
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "channel": channel,
            "authenticated": user_id is not None,
            "message": f"Connected to channel '{channel}'",
        })

        # Listen for messages
        while True:
            data = await websocket.receive_json()
            await handle_message(websocket, channel, data, user_id, manager, db)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from channel '{channel}'")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, channel)


async def handle_message(
    websocket: WebSocket,
    channel: str,
    data: dict[str, Any],
    user_id: int | None,
    manager,
    db: Session,
) -> None:
    """
    Handle incoming WebSocket messages.

    Supported message types:
    - auth: Authenticate with token
    - ping: Keep-alive ping
    - subscribe: Subscribe to additional channel
    - unsubscribe: Unsubscribe from channel
    """
    message_type = data.get("type", "")

    if message_type == "auth":
        # Handle authentication
        token = data.get("token")
        user = get_user_from_token(db, token)

        if user:
            await websocket.send_json({
                "type": "auth_success",
                "user_id": user.id,
                "message": "Authentication successful",
            })
        else:
            await websocket.send_json({
                "type": "auth_failed",
                "message": "Invalid or expired token",
            })

    elif message_type == "ping":
        # Respond to keep-alive ping
        await websocket.send_json({
            "type": "pong",
            "timestamp": data.get("timestamp"),
        })

    elif message_type == "subscribe":
        # Subscribe to additional channel
        new_channel = data.get("channel")
        if new_channel:
            user = get_user_from_token(db, data.get("token")) if data.get("token") else None
            new_user_id = user.id if user else user_id

            # Note: Can't call connect again (websocket already accepted)
            # Just add to internal tracking
            if new_channel not in manager.active_connections:
                manager.active_connections[new_channel] = []

            # Check authorization for private channels
            if new_channel.startswith("user:"):
                if new_user_id is None:
                    await websocket.send_json({
                        "type": "subscribe_failed",
                        "channel": new_channel,
                        "message": "Authentication required for private channels",
                    })
                    return

                channel_user_id = new_channel.split(":")[1]
                if str(new_user_id) != channel_user_id:
                    await websocket.send_json({
                        "type": "subscribe_failed",
                        "channel": new_channel,
                        "message": "Unauthorized for this channel",
                    })
                    return

            from app.services.websocket import Connection

            connection = Connection(
                websocket=websocket,
                user_id=new_user_id,
                authenticated=new_user_id is not None,
            )
            manager.active_connections[new_channel].append(connection)

            if websocket not in manager.websocket_channels:
                manager.websocket_channels[websocket] = set()
            manager.websocket_channels[websocket].add(new_channel)

            await websocket.send_json({
                "type": "subscribed",
                "channel": new_channel,
                "message": f"Subscribed to channel '{new_channel}'",
            })

    elif message_type == "unsubscribe":
        # Unsubscribe from channel
        unsub_channel = data.get("channel")
        if unsub_channel and unsub_channel != channel:
            manager.disconnect(websocket, unsub_channel)
            await websocket.send_json({
                "type": "unsubscribed",
                "channel": unsub_channel,
                "message": f"Unsubscribed from channel '{unsub_channel}'",
            })

    else:
        # Unknown message type
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
        })


@router.get("/ws/stats", tags=["WebSocket"])
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns the number of active connections per channel.
    """
    manager = get_connection_manager()
    return manager.get_stats()
