"""Tests for BackfillService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from lol_data_center.api_client.riot_client import Region, RiotApiClient
from lol_data_center.services.backfill_service import BackfillService
from lol_data_center.services.match_service import MatchService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lol_data_center.database.models import TrackedPlayer
    from lol_data_center.schemas.riot_api import MatchDto


class TestBackfillService:
    """Tests for BackfillService."""

    @pytest.mark.asyncio
    async def test_backfill_player_history_no_matches(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test backfill when player has no match history."""
        # Create mock client
        mock_client = MagicMock(spec=RiotApiClient)
        mock_client.fetch_all_match_ids = AsyncMock(return_value=[])

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        assert saved_count == 0
        mock_client.fetch_all_match_ids.assert_called_once_with(
            puuid=sample_player.puuid,
            region=Region.EUROPE,
        )

    @pytest.mark.asyncio
    async def test_backfill_player_history_new_matches(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill successfully saves new matches."""
        # Create mock client
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = ["EUW1_MATCH_1", "EUW1_MATCH_2", "EUW1_MATCH_3"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)

        # Mock get_match to return sample match data
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        assert saved_count == 3
        assert mock_client.get_match.call_count == 3

        # Verify matches were fetched with correct IDs
        calls = mock_client.get_match.call_args_list
        assert calls[0].args[0] == "EUW1_MATCH_1"
        assert calls[1].args[0] == "EUW1_MATCH_2"
        assert calls[2].args[0] == "EUW1_MATCH_3"

    @pytest.mark.asyncio
    async def test_backfill_player_history_skips_existing_matches(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill skips matches that already exist in database."""
        # Pre-save one match
        match_service = MatchService(async_session)
        await match_service.save_match(sample_match_dto)

        # Create mock client
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = [
            "EUW1_12345678",  # Already exists
            "EUW1_MATCH_NEW_1",
            "EUW1_MATCH_NEW_2",
        ]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        # Should only save 2 new matches (skip the existing one)
        assert saved_count == 2
        # Should only call get_match for the 2 new matches
        assert mock_client.get_match.call_count == 2

    @pytest.mark.asyncio
    async def test_backfill_player_history_with_progress_callback(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill calls progress callback correctly."""
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = ["EUW1_MATCH_1", "EUW1_MATCH_2", "EUW1_MATCH_3"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        # Track progress callback calls
        progress_calls = []

        def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
            progress_callback=track_progress,
        )

        assert saved_count == 3
        assert len(progress_calls) == 3
        assert progress_calls == [(1, 3), (2, 3), (3, 3)]

    @pytest.mark.asyncio
    async def test_backfill_player_history_continues_on_error(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill continues processing after individual match errors."""
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = ["EUW1_MATCH_1", "EUW1_MATCH_2", "EUW1_MATCH_3"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)

        # Second match fails, others succeed
        mock_client.get_match = AsyncMock(
            side_effect=[
                sample_match_dto,
                Exception("API error"),
                sample_match_dto,
            ]
        )

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        # Should save 2 out of 3 matches (skip the errored one)
        assert saved_count == 2
        assert mock_client.get_match.call_count == 3

    @pytest.mark.asyncio
    async def test_backfill_player_history_large_batch(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill handles large number of matches."""
        mock_client = MagicMock(spec=RiotApiClient)

        # Simulate 250 matches
        match_ids = [f"EUW1_MATCH_{i}" for i in range(250)]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        assert saved_count == 250
        assert mock_client.get_match.call_count == 250

    @pytest.mark.asyncio
    async def test_backfill_player_history_different_regions(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill with different regions."""
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = ["NA1_MATCH_1", "NA1_MATCH_2"]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.AMERICAS,
        )

        assert saved_count == 2

        # Verify region was used correctly
        mock_client.fetch_all_match_ids.assert_called_once_with(
            puuid=sample_player.puuid,
            region=Region.AMERICAS,
        )

        # Verify all get_match calls used the same region
        for call in mock_client.get_match.call_args_list:
            assert call.args[1] == Region.AMERICAS

    @pytest.mark.asyncio
    async def test_backfill_player_history_mixed_existing_and_new(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test backfill with mix of existing and new matches."""
        # Pre-save 2 matches
        match_service = MatchService(async_session)
        await match_service.save_match(sample_match_dto)

        # Modify and save another match
        sample_match_dto.metadata.match_id = "EUW1_EXISTING_2"
        await match_service.save_match(sample_match_dto)

        # Create mock client
        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = [
            "EUW1_12345678",  # Exists
            "EUW1_NEW_1",
            "EUW1_EXISTING_2",  # Exists
            "EUW1_NEW_2",
            "EUW1_NEW_3",
        ]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)

        # Reset match ID for return value
        sample_match_dto.metadata.match_id = "EUW1_NEW_X"
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
        )

        # Should only save 3 new matches (skip 2 existing)
        assert saved_count == 3
        # Should only fetch details for the 3 new matches
        assert mock_client.get_match.call_count == 3

    @pytest.mark.asyncio
    async def test_backfill_player_history_progress_callback_with_skips(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test progress callback is called even for skipped matches."""
        # Pre-save one match
        match_service = MatchService(async_session)
        await match_service.save_match(sample_match_dto)

        mock_client = MagicMock(spec=RiotApiClient)
        match_ids = [
            "EUW1_12345678",  # Exists - will be skipped
            "EUW1_NEW_1",
            "EUW1_NEW_2",
        ]
        mock_client.fetch_all_match_ids = AsyncMock(return_value=match_ids)

        # Reset match ID for new matches
        sample_match_dto.metadata.match_id = "EUW1_NEW_X"
        mock_client.get_match = AsyncMock(return_value=sample_match_dto)

        service = BackfillService(async_session, mock_client)

        progress_calls = []

        def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        saved_count = await service.backfill_player_history(
            player=sample_player,
            region=Region.EUROPE,
            progress_callback=track_progress,
        )

        assert saved_count == 2  # Only 2 new matches saved
        # But progress should be called for all 3 matches
        assert len(progress_calls) == 3
        assert progress_calls == [(1, 3), (2, 3), (3, 3)]
