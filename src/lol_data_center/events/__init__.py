"""Events package."""

from lol_data_center.events.event_bus import EventBus, NewMatchEvent, get_event_bus

__all__ = [
    "EventBus",
    "NewMatchEvent",
    "get_event_bus",
]
