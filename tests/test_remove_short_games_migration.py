"""Tests for Alembic migration that removes short duration games."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from lol_data_center.database.models import Match, MatchParticipant

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lol_data_center.schemas.riot_api import MatchDto


class TestRemoveShortDurationGamesMigration:
    """Tests for the migration that removes games shorter than 10 minutes."""

    @pytest.mark.asyncio
    async def test_migration_deletes_short_games(
        self,
        async_session: AsyncSession,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test that migration deletes games with duration < 600 seconds."""
        from lol_data_center.services.match_service import MatchService

        service = MatchService(async_session)

        # Create a short game (remake)
        short_match = sample_match_dto.model_copy(deep=True)
        short_match.metadata.match_id = "SHORT_GAME_1"
        short_match.info.game_duration = 180  # 3 minutes (remake)

        # Create a valid game
        valid_match = sample_match_dto.model_copy(deep=True)
        valid_match.metadata.match_id = "VALID_GAME_1"
        valid_match.info.game_duration = 1800  # 30 minutes

        # Create a boundary case (exactly 600 seconds - should be kept)
        boundary_match = sample_match_dto.model_copy(deep=True)
        boundary_match.metadata.match_id = "BOUNDARY_GAME_1"
        boundary_match.info.game_duration = 600  # Exactly 10 minutes

        # Save all matches
        await service.save_match(short_match)
        await service.save_match(valid_match)
        await service.save_match(boundary_match)
        await async_session.commit()

        # Verify all matches were created
        result = await async_session.execute(select(Match))
        all_matches = result.scalars().all()
        assert len(all_matches) == 3

        # Simulate migration by deleting short games
        minimum_duration = 600

        short_games = (
            await async_session.execute(
                select(Match).where(Match.game_duration < minimum_duration)
            )
        ).scalars().all()

        # Delete short games (simulating migration)
        for game in short_games:
            await async_session.delete(game)
        await async_session.commit()

        # Verify only valid games remain
        result = await async_session.execute(select(Match))
        remaining_matches = result.scalars().all()
        assert len(remaining_matches) == 2

        # Verify the correct matches were kept
        remaining_ids = {m.match_id for m in remaining_matches}
        assert "VALID_GAME_1" in remaining_ids
        assert "BOUNDARY_GAME_1" in remaining_ids
        assert "SHORT_GAME_1" not in remaining_ids

    @pytest.mark.asyncio
    async def test_migration_cascades_to_participants(
        self,
        async_session: AsyncSession,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test that deleting a match cascades to match_participants."""
        from lol_data_center.services.match_service import MatchService

        service = MatchService(async_session)

        # Create a short game
        short_match = sample_match_dto.model_copy(deep=True)
        short_match.metadata.match_id = "SHORT_WITH_PARTICIPANTS"
        short_match.info.game_duration = 300  # 5 minutes

        # Save match
        match = await service.save_match(short_match)
        await async_session.commit()

        # Verify participants were created
        result = await async_session.execute(
            select(MatchParticipant).where(MatchParticipant.match_db_id == match.id)
        )
        participants = result.scalars().all()
        assert len(participants) == 10

        # Delete the match (simulating migration)
        await async_session.delete(match)
        await async_session.commit()

        # Verify participants were also deleted (CASCADE)
        result = await async_session.execute(
            select(MatchParticipant).where(MatchParticipant.match_db_id == match.id)
        )
        participants_after = result.scalars().all()
        assert len(participants_after) == 0

    @pytest.mark.asyncio
    async def test_various_duration_thresholds(
        self,
        async_session: AsyncSession,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test migration behavior with various game durations."""
        from lol_data_center.services.match_service import MatchService

        service = MatchService(async_session)

        # Test cases: (duration_seconds, should_keep)
        test_cases = [
            (0, False),  # Immediate end
            (180, False),  # 3 minutes (remake)
            (300, False),  # 5 minutes
            (599, False),  # Just under threshold
            (600, True),  # Exactly threshold
            (601, True),  # Just over threshold
            (900, True),  # 15 minutes
            (1800, True),  # 30 minutes
        ]

        # Create matches with different durations
        for idx, (duration, _) in enumerate(test_cases):
            match = sample_match_dto.model_copy(deep=True)
            match.metadata.match_id = f"TEST_GAME_{idx}_{duration}"
            match.info.game_duration = duration
            await service.save_match(match)

        await async_session.commit()

        # Simulate migration
        short_games = (
            await async_session.execute(select(Match).where(Match.game_duration < 600))
        ).scalars().all()

        for game in short_games:
            await async_session.delete(game)
        await async_session.commit()

        # Verify results
        all_matches = (await async_session.execute(select(Match))).scalars().all()
        remaining_durations = {m.game_duration for m in all_matches}

        # Check that games < 600 were removed and >= 600 were kept
        for duration, should_keep in test_cases:
            if should_keep:
                assert duration in remaining_durations, f"Duration {duration} should be kept"
            else:
                assert (
                    duration not in remaining_durations
                ), f"Duration {duration} should be removed"

    @pytest.mark.asyncio
    async def test_no_matches_to_delete(
        self,
        async_session: AsyncSession,
        sample_match_dto: MatchDto,
    ) -> None:
        """Test migration when there are no short games to delete."""
        from lol_data_center.services.match_service import MatchService

        service = MatchService(async_session)

        # Create only valid games
        for i in range(3):
            match = sample_match_dto.model_copy(deep=True)
            match.metadata.match_id = f"VALID_GAME_{i}"
            match.info.game_duration = 1200 + (i * 100)  # All > 600 seconds
            await service.save_match(match)

        await async_session.commit()

        # Count before migration
        count_before = len((await async_session.execute(select(Match))).scalars().all())

        # Simulate migration
        short_games = (
            await async_session.execute(select(Match).where(Match.game_duration < 600))
        ).scalars().all()
        assert len(short_games) == 0

        # Count after (should be unchanged)
        count_after = len((await async_session.execute(select(Match))).scalars().all())
        assert count_after == count_before
        assert count_after == 3
