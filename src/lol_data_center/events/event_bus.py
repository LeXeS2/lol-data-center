"""Event bus for publishing and subscribing to events.

This implements a simple publish-subscribe pattern for decoupling components.
Multiple listeners can subscribe to events like NewMatchEvent.
"""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.riot_api import MatchDto, ParticipantDto

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class NewMatchEvent:
    """Event published when a new match is detected for a tracked player.

    Attributes:
        player_puuid: PUUID of the tracked player
        player_name: Display name of the player (Riot ID)
        match_id: ID of the new match
        match_data: Full match data from the API
        participant_data: The player's stats in this match
        timestamp: When the event was created
    """

    player_puuid: str
    player_name: str
    match_id: str
    match_data: MatchDto
    participant_data: ParticipantDto
    timestamp: datetime = field(default_factory=datetime.utcnow)


# Type alias for event handlers
EventHandler = Callable[[T], Awaitable[None]]


class EventBus:
    """Async event bus for publishing and subscribing to events.

    This allows multiple components to listen for events without tight coupling.
    Handlers are called concurrently but errors in one handler don't affect others.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[type[Any], list[EventHandler[Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Async function to call when event is published
        """
        self._handlers[event_type].append(handler)
        logger.info(
            "Handler subscribed to event",
            event_type=event_type.__name__,
            handler=handler.__qualname__,
        )

    def unsubscribe(
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> bool:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler to remove

        Returns:
            True if the handler was found and removed
        """
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.info(
                "Handler unsubscribed from event",
                event_type=event_type.__name__,
                handler=handler.__qualname__,
            )
            return True
        return False

    async def publish(self, event: T) -> int:
        """Publish an event to all subscribed handlers.

        Handlers are called concurrently. Errors in one handler don't affect others.

        Args:
            event: The event to publish

        Returns:
            Number of handlers that successfully processed the event
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(
                "No handlers for event",
                event_type=event_type.__name__,
            )
            return 0

        logger.info(
            "Publishing event",
            event_type=event_type.__name__,
            handler_count=len(handlers),
        )

        # Call all handlers concurrently
        results = await asyncio.gather(
            *[self._safe_call(handler, event) for handler in handlers],
            return_exceptions=True,
        )

        # Count successful handlers
        success_count = sum(1 for r in results if r is True)

        if success_count < len(handlers):
            logger.warning(
                "Some handlers failed",
                event_type=event_type.__name__,
                success_count=success_count,
                total_handlers=len(handlers),
            )

        return success_count

    async def _safe_call(
        self,
        handler: EventHandler[T],
        event: T,
    ) -> bool:
        """Safely call a handler, catching any exceptions.

        Args:
            handler: The handler to call
            event: The event to pass

        Returns:
            True if the handler succeeded, False otherwise
        """
        try:
            await handler(event)
            return True
        except Exception as e:
            logger.error(
                "Handler raised exception",
                handler=handler.__qualname__,
                event_type=type(event).__name__,
                error=str(e),
                exc_info=True,
            )
            return False

    def get_handler_count(self, event_type: type[T]) -> int:
        """Get the number of handlers for an event type."""
        return len(self._handlers.get(event_type, []))

    def clear(self) -> None:
        """Remove all handlers (useful for testing)."""
        self._handlers.clear()


# Singleton event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the event bus (for testing)."""
    global _event_bus
    if _event_bus is not None:
        _event_bus.clear()
    _event_bus = None
