"""Tests for PollingService filtering by game mode."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from lol_data_center.events.event_bus import NewMatchEvent, get_event_bus
from lol_data_center.services.match_service import MatchService
from lol_data_center.services.polling_service import PollingService

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    from lol_data_center.database.models import TrackedPlayer
    from lol_data_center.schemas.riot_api import MatchDto


class TestPollingServiceFiltering:
    """Ensure polling only processes CLASSIC matches."""

    @pytest.mark.asyncio
    async def test_polling_skips_non_classic(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
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
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
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
