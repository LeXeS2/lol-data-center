"""Tests for the event bus."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lol_data_center.events.event_bus import EventBus, NewMatchEvent, reset_event_bus

if TYPE_CHECKING:
    from lol_data_center.schemas.riot_api import MatchDto, ParticipantDto


class TestEventBus:
    """Tests for the EventBus class."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()
        yield
        reset_event_bus()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(
        self,
        sample_match_dto: MatchDto,
        sample_participant_dto: ParticipantDto,
    ) -> None:
        """Test subscribing and publishing events."""
        bus = EventBus()
        received_events: list[NewMatchEvent] = []

        async def handler(event: NewMatchEvent) -> None:
            received_events.append(event)

        bus.subscribe(NewMatchEvent, handler)

        event = NewMatchEvent(
            player_puuid="test-puuid",
            player_name="TestPlayer#EUW",
            match_id="EUW1_12345",
            match_data=sample_match_dto,
            participant_data=sample_participant_dto,
        )

        await bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].player_puuid == "test-puuid"
        assert received_events[0].match_id == "EUW1_12345"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(
        self,
        sample_match_dto: MatchDto,
        sample_participant_dto: ParticipantDto,
    ) -> None:
        """Test multiple subscribers receive the same event."""
        bus = EventBus()
        handler1_count = 0
        handler2_count = 0

        async def handler1(event: NewMatchEvent) -> None:
            nonlocal handler1_count
            handler1_count += 1

        async def handler2(event: NewMatchEvent) -> None:
            nonlocal handler2_count
            handler2_count += 1

        bus.subscribe(NewMatchEvent, handler1)
        bus.subscribe(NewMatchEvent, handler2)

        event = NewMatchEvent(
            player_puuid="test-puuid",
            player_name="TestPlayer#EUW",
            match_id="EUW1_12345",
            match_data=sample_match_dto,
            participant_data=sample_participant_dto,
        )

        await bus.publish(event)

        assert handler1_count == 1
        assert handler2_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(
        self,
        sample_match_dto: MatchDto,
        sample_participant_dto: ParticipantDto,
    ) -> None:
        """Test unsubscribing from events."""
        bus = EventBus()
        call_count = 0

        async def handler(event: NewMatchEvent) -> None:
            nonlocal call_count
            call_count += 1

        bus.subscribe(NewMatchEvent, handler)
        bus.unsubscribe(NewMatchEvent, handler)

        event = NewMatchEvent(
            player_puuid="test-puuid",
            player_name="TestPlayer#EUW",
            match_id="EUW1_12345",
            match_data=sample_match_dto,
            participant_data=sample_participant_dto,
        )

        await bus.publish(event)

        assert call_count == 0

    @pytest.mark.asyncio
    async def test_handler_error_isolation(
        self,
        sample_match_dto: MatchDto,
        sample_participant_dto: ParticipantDto,
    ) -> None:
        """Test that errors in one handler don't affect others."""
        bus = EventBus()
        handler2_called = False

        async def failing_handler(event: NewMatchEvent) -> None:
            raise ValueError("Intentional error")

        async def working_handler(event: NewMatchEvent) -> None:
            nonlocal handler2_called
            handler2_called = True

        bus.subscribe(NewMatchEvent, failing_handler)
        bus.subscribe(NewMatchEvent, working_handler)

        event = NewMatchEvent(
            player_puuid="test-puuid",
            player_name="TestPlayer#EUW",
            match_id="EUW1_12345",
            match_data=sample_match_dto,
            participant_data=sample_participant_dto,
        )

        # Should not raise
        success_count = await bus.publish(event)

        # One handler succeeded, one failed
        assert success_count == 1
        assert handler2_called is True

    @pytest.mark.asyncio
    async def test_no_handlers(
        self,
        sample_match_dto: MatchDto,
        sample_participant_dto: ParticipantDto,
    ) -> None:
        """Test publishing to event with no handlers."""
        bus = EventBus()

        event = NewMatchEvent(
            player_puuid="test-puuid",
            player_name="TestPlayer#EUW",
            match_id="EUW1_12345",
            match_data=sample_match_dto,
            participant_data=sample_participant_dto,
        )

        # Should not raise
        success_count = await bus.publish(event)
        assert success_count == 0

    def test_get_handler_count(self) -> None:
        """Test getting handler count."""
        bus = EventBus()

        async def handler(event: NewMatchEvent) -> None:
            pass

        assert bus.get_handler_count(NewMatchEvent) == 0

        bus.subscribe(NewMatchEvent, handler)
        assert bus.get_handler_count(NewMatchEvent) == 1

        bus.subscribe(NewMatchEvent, handler)  # Same handler again
        assert bus.get_handler_count(NewMatchEvent) == 2

    def test_clear(self) -> None:
        """Test clearing all handlers."""
        bus = EventBus()

        async def handler(event: NewMatchEvent) -> None:
            pass

        bus.subscribe(NewMatchEvent, handler)
        assert bus.get_handler_count(NewMatchEvent) == 1

        bus.clear()
        assert bus.get_handler_count(NewMatchEvent) == 0
