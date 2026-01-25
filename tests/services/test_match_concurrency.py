"""Tests for concurrent match saving."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from lol_data_center.database.engine import get_async_session
from lol_data_center.services.match_service import MatchService

if TYPE_CHECKING:
    from lol_data_center.schemas.riot_api import MatchDto


class TestMatchConcurrency:
    """Tests for concurrent match operations."""

    @pytest.mark.asyncio
    async def test_concurrent_save_match(self, sample_match_dto: MatchDto) -> None:
        """Test that concurrent saves of the same match don't cause errors.

        This simulates the edge case where multiple users add players who played
        the same match, and the polling service tries to save the match concurrently.
        """

        async def save_match_task() -> None:
            """Task that saves the match in a separate session."""
            async with get_async_session() as session:
                service = MatchService(session)
                await service.save_match(sample_match_dto)

        # Run multiple concurrent saves
        tasks = [save_match_task() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Verify the match was saved exactly once
        async with get_async_session() as session:
            service = MatchService(session)
            exists = await service.match_exists(sample_match_dto.metadata.match_id)
            assert exists is True

            # Verify only one match record exists
            from sqlalchemy import func, select

            from lol_data_center.database.models import Match

            result = await session.execute(
                select(func.count(Match.id)).where(
                    Match.match_id == sample_match_dto.metadata.match_id
                )
            )
            count = result.scalar_one()
            assert count == 1

            # Verify participants were saved correctly
            from lol_data_center.database.models import MatchParticipant

            result = await session.execute(
                select(func.count(MatchParticipant.id)).where(
                    MatchParticipant.match_id == sample_match_dto.metadata.match_id
                )
            )
            participant_count = result.scalar_one()
            assert participant_count == 10
