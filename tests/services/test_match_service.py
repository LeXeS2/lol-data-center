"""Tests for MatchService."""

import pytest
from unittest.mock import AsyncMock

from lol_data_center.services.match_service import MatchService


class TestMatchService:
    """Tests for MatchService."""

    @pytest.mark.asyncio
    async def test_match_exists_false(self, async_session):
        """Test match_exists returns False for non-existent match."""
        service = MatchService(async_session)

        exists = await service.match_exists("NONEXISTENT_12345")

        assert exists is False

    @pytest.mark.asyncio
    async def test_save_match(self, async_session, sample_match_dto):
        """Test saving a match to the database."""
        from sqlalchemy import select
        from lol_data_center.database.models import MatchParticipant

        service = MatchService(async_session)

        match = await service.save_match(sample_match_dto)

        assert match.match_id == "EUW1_12345678"
        assert match.game_mode == "CLASSIC"

        # Query participants separately to avoid lazy loading
        result = await async_session.execute(
            select(MatchParticipant).where(MatchParticipant.match_db_id == match.id)
        )
        participants = result.scalars().all()
        assert len(participants) == 10

    @pytest.mark.asyncio
    async def test_save_match_idempotent(self, async_session, sample_match_dto):
        """Test that saving the same match twice is idempotent."""
        service = MatchService(async_session)

        match1 = await service.save_match(sample_match_dto)
        match2 = await service.save_match(sample_match_dto)

        # Should return the same match
        assert match1.id == match2.id

    @pytest.mark.asyncio
    async def test_update_player_records(
        self,
        async_session,
        sample_player,
        sample_participant_dto,
    ):
        """Test updating player records."""
        service = MatchService(async_session)

        # Set kills higher than current max (15)
        sample_participant_dto.kills = 20

        broken_records = await service.update_player_records(
            sample_player,
            sample_participant_dto,
            "EUW1_12345678",
        )

        assert "kills" in broken_records
        assert broken_records["kills"] == (15, 20)  # Old, new

    @pytest.mark.asyncio
    async def test_get_recent_matches_for_player(
        self,
        async_session,
        sample_player,
        sample_match_dto,
    ):
        """Test getting recent matches for a player."""
        service = MatchService(async_session)

        # First save a match
        await service.save_match(sample_match_dto)

        # Get recent matches
        matches = await service.get_recent_matches_for_player(sample_player.puuid)

        assert len(matches) == 1
        assert matches[0].puuid == sample_player.puuid
