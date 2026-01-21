"""Tests for PollingService filtering by game mode."""

import pytest
from unittest.mock import AsyncMock

from lol_data_center.api_client.riot_client import Region
from lol_data_center.services.polling_service import PollingService
from lol_data_center.events.event_bus import get_event_bus, NewMatchEvent
from lol_data_center.services.match_service import MatchService


class TestPollingServiceFiltering:
    """Ensure polling only processes CLASSIC matches."""

    @pytest.mark.asyncio
    async def test_polling_skips_non_classic(
        self,
        async_session,
        sample_player,
        sample_match_dto,
        mock_riot_client,
    ):
        # Arrange: non-CLASSIC match
        match_id = "EUW1_NON_CLASSIC_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        non_classic = sample_match_dto.model_copy(deep=True)
        non_classic.metadata.match_id = match_id
        non_classic.info.game_mode = "ARAM"
        mock_riot_client.get_match = AsyncMock(return_value=non_classic)

        polling = PollingService(api_client=mock_riot_client)

        # Act: subscribe to events and invoke internal _poll_player with provided session
        event_bus = get_event_bus()
        event_count = 0

        async def count_events(event: NewMatchEvent) -> None:
            nonlocal event_count
            event_count += 1

        event_bus.subscribe(NewMatchEvent, count_events)
        try:
            await polling._poll_player(sample_player, async_session)
        finally:
            event_bus.unsubscribe(NewMatchEvent, count_events)

        # Assert: no events, no match saved
        assert event_count == 0
        ms = MatchService(async_session)
        assert (await ms.match_exists(match_id)) is False

    @pytest.mark.asyncio
    async def test_polling_accepts_classic(
        self,
        async_session,
        sample_player,
        sample_match_dto,
        mock_riot_client,
    ):
        # Arrange: CLASSIC match
        match_id = "EUW1_CLASSIC_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        classic = sample_match_dto.model_copy(deep=True)
        classic.metadata.match_id = match_id
        classic.info.game_mode = "CLASSIC"
        mock_riot_client.get_match = AsyncMock(return_value=classic)

        polling = PollingService(api_client=mock_riot_client)

        # Act: subscribe to events and invoke internal _poll_player with provided session
        event_bus = get_event_bus()
        event_count = 0

        async def count_events(event: NewMatchEvent) -> None:
            nonlocal event_count
            event_count += 1

        event_bus.subscribe(NewMatchEvent, count_events)
        try:
            await polling._poll_player(sample_player, async_session)
        finally:
            event_bus.unsubscribe(NewMatchEvent, count_events)

        # Assert: one event, match saved
        assert event_count == 1
        ms = MatchService(async_session)
        assert (await ms.match_exists(match_id)) is True
