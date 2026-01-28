"""Tests for PollingService filtering by allowed queues."""

from __future__ import annotations

from datetime import UTC, datetime
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
    """Ensure polling only processes matches in allowed queues."""

    @pytest.mark.asyncio
    async def test_polling_skips_disallowed_queue(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
        # Arrange: disallowed queue (e.g., ARAM 450)
        match_id = "EUW1_NON_CLASSIC_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        non_classic = sample_match_dto.model_copy(deep=True)
        non_classic.metadata.match_id = match_id
        non_classic.info.game_mode = "ARAM"
        non_classic.info.queue_id = 450
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
    async def test_polling_accepts_allowed_queue(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
        # Arrange: allowed queue (e.g., Ranked Solo/Duo 420)
        match_id = "EUW1_CLASSIC_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        classic = sample_match_dto.model_copy(deep=True)
        classic.metadata.match_id = match_id
        classic.info.game_mode = "CLASSIC"
        classic.info.queue_id = 420
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

    @pytest.mark.asyncio
    async def test_polling_uses_datetime_filter(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
        """Test that polling uses last_polled_at as start_time filter."""
        # Arrange: Set last_polled_at to a specific time
        last_polled = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        sample_player.last_polled_at = last_polled

        match_id = "EUW1_DATETIME_TEST_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        classic = sample_match_dto.model_copy(deep=True)
        classic.metadata.match_id = match_id
        classic.info.game_mode = "CLASSIC"
        mock_riot_client.get_match = AsyncMock(return_value=classic)

        polling = PollingService(api_client=mock_riot_client)

        # Act
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

        # Assert: get_match_ids was called with start_time parameter
        mock_riot_client.get_match_ids.assert_called_once()
        call_args = mock_riot_client.get_match_ids.call_args
        assert call_args is not None
        assert call_args.kwargs["start_time"] == int(last_polled.timestamp())

        # Assert: match was processed
        assert event_count == 1

    @pytest.mark.asyncio
    async def test_polling_without_last_polled_at(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
        """Test that polling works when last_polled_at is None."""
        # Arrange: Ensure last_polled_at is None
        sample_player.last_polled_at = None

        match_id = "EUW1_NO_DATETIME_1"
        mock_riot_client.get_match_ids.return_value = [match_id]

        classic = sample_match_dto.model_copy(deep=True)
        classic.metadata.match_id = match_id
        classic.info.game_mode = "CLASSIC"
        mock_riot_client.get_match = AsyncMock(return_value=classic)

        polling = PollingService(api_client=mock_riot_client)

        # Act
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

        # Assert: get_match_ids was called with start_time=None
        mock_riot_client.get_match_ids.assert_called_once()
        call_args = mock_riot_client.get_match_ids.call_args
        assert call_args is not None
        assert call_args.kwargs["start_time"] is None

        # Assert: match was processed
        assert event_count == 1

    @pytest.mark.asyncio
    async def test_polling_skips_existing_matches(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
        mock_riot_client: MagicMock,
    ) -> None:
        """Test that polling skips matches that already exist in the database.

        This is critical for the backfill use case - after backfill saves matches,
        the polling service should not process them again even if they're returned
        by the Riot API.
        """
        # Arrange: Pre-save a match (simulating backfill)
        match_id = "EUW1_EXISTING_MATCH"
        existing_match = sample_match_dto.model_copy(deep=True)
        existing_match.metadata.match_id = match_id
        existing_match.info.game_mode = "CLASSIC"
        existing_match.info.queue_id = 420

        match_service = MatchService(async_session)
        await match_service.save_match(existing_match)

        # Configure mock client to return the existing match ID
        mock_riot_client.get_match_ids.return_value = [match_id]

        polling = PollingService(api_client=mock_riot_client)

        # Act: subscribe to events and poll
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

        # Assert: No events should be published for existing matches
        assert event_count == 0

        # Assert: Riot API's get_match should NOT be called for existing matches
        mock_riot_client.get_match.assert_not_called()
