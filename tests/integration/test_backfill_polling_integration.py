"""Integration tests for backfill + polling workflow.

This test verifies that after backfilling a player's match history,
the polling service does not re-process or re-publish events for those
already-backfilled matches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from lol_data_center.api_client.riot_client import Region, RiotApiClient
from lol_data_center.events.event_bus import NewMatchEvent, get_event_bus
from lol_data_center.services.backfill_service import BackfillService
from lol_data_center.services.polling_service import PollingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lol_data_center.database.models import TrackedPlayer
    from lol_data_center.schemas.riot_api import MatchDto


class TestBackfillPollingIntegration:
    """Integration tests for backfill + polling interaction."""

    @pytest.mark.asyncio
    async def test_backfill_then_poll_no_duplicates(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test that polling after backfill does not re-process matches.

        Scenario:
        1. Backfill loads 3 matches
        2. Polling runs immediately after
        3. Riot API returns the same 3 match IDs (no new matches)
        4. Polling should NOT publish any events

        This validates the fix for the duplicate matches issue.
        """
        # Step 1: Setup mock API client
        mock_client = MagicMock(spec=RiotApiClient)

        # Backfill will fetch these match IDs
        backfill_match_ids = ["EUW1_MATCH_1", "EUW1_MATCH_2", "EUW1_MATCH_3"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=backfill_match_ids)

        # Both backfill and polling will get these match details
        match_1 = sample_match_dto.model_copy(deep=True)
        match_1.metadata.match_id = "EUW1_MATCH_1"
        match_2 = sample_match_dto.model_copy(deep=True)
        match_2.metadata.match_id = "EUW1_MATCH_2"
        match_3 = sample_match_dto.model_copy(deep=True)
        match_3.metadata.match_id = "EUW1_MATCH_3"

        mock_client.get_match = AsyncMock(side_effect=[match_1, match_2, match_3])

        # Step 2: Run backfill
        backfill_service = BackfillService(async_session, mock_client)
        saved_count = await backfill_service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        # Verify backfill saved all 3 matches
        assert saved_count == 3

        # Step 3: Setup polling service
        # Polling will see the same match IDs (simulating no new matches)
        mock_client.get_match_ids = AsyncMock(return_value=backfill_match_ids)

        polling_service = PollingService(api_client=mock_client)

        # Step 4: Subscribe to events to count how many are published
        event_bus = get_event_bus()
        event_count = 0

        async def count_events(event: NewMatchEvent) -> None:
            nonlocal event_count
            event_count += 1

        event_bus.subscribe(NewMatchEvent, count_events)

        try:
            # Step 5: Poll the player
            await polling_service._poll_player(sample_player, async_session)
        finally:
            event_bus.unsubscribe(NewMatchEvent, count_events)

        # Step 6: Verify NO events were published
        # This is the key assertion - polling should skip all existing matches
        assert event_count == 0

        # Step 7: Verify get_match was NOT called during polling
        # (it was called 3 times during backfill, but 0 times during polling)
        assert mock_client.get_match.call_count == 3

    @pytest.mark.asyncio
    async def test_backfill_then_poll_with_new_match(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test that polling after backfill correctly processes NEW matches.

        Scenario:
        1. Backfill loads 2 matches
        2. Player plays a new match
        3. Polling runs and finds 3 matches (2 old + 1 new)
        4. Polling should publish event ONLY for the new match

        This ensures our fix doesn't break normal polling behavior.
        """
        # Step 1: Setup mock API client
        mock_client = MagicMock(spec=RiotApiClient)

        # Backfill will fetch these 2 match IDs
        backfill_match_ids = ["EUW1_MATCH_1", "EUW1_MATCH_2"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=backfill_match_ids)

        match_1 = sample_match_dto.model_copy(deep=True)
        match_1.metadata.match_id = "EUW1_MATCH_1"
        match_2 = sample_match_dto.model_copy(deep=True)
        match_2.metadata.match_id = "EUW1_MATCH_2"

        mock_client.get_match = AsyncMock(side_effect=[match_1, match_2])

        # Step 2: Run backfill
        backfill_service = BackfillService(async_session, mock_client)
        saved_count = await backfill_service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )
        assert saved_count == 2

        # Step 3: Setup polling - now there's a NEW match
        new_match_ids = [
            "EUW1_MATCH_1",  # Old
            "EUW1_MATCH_2",  # Old
            "EUW1_MATCH_NEW",  # NEW!
        ]
        mock_client.get_match_ids = AsyncMock(return_value=new_match_ids)

        # Configure mock to return new match details
        match_new = sample_match_dto.model_copy(deep=True)
        match_new.metadata.match_id = "EUW1_MATCH_NEW"
        mock_client.get_match = AsyncMock(return_value=match_new)

        polling_service = PollingService(api_client=mock_client)

        # Step 4: Subscribe to events
        event_bus = get_event_bus()
        events = []

        async def capture_events(event: NewMatchEvent) -> None:
            events.append(event)

        event_bus.subscribe(NewMatchEvent, capture_events)

        try:
            # Step 5: Poll the player
            await polling_service._poll_player(sample_player, async_session)
        finally:
            event_bus.unsubscribe(NewMatchEvent, capture_events)

        # Step 6: Verify exactly 1 event was published (for the new match)
        assert len(events) == 1
        assert events[0].match_id == "EUW1_MATCH_NEW"

        # Step 7: Verify get_match was called only once (for the new match)
        # The 2 existing matches should be skipped without fetching
        assert mock_client.get_match.call_count == 1
