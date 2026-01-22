"""Tests for match timeline functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from lol_data_center.database.models import Match, MatchTimeline
from lol_data_center.schemas.riot_api import MatchTimelineDto
from lol_data_center.services.match_service import MatchService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestMatchTimeline:
    """Tests for match timeline functionality."""

    @pytest.mark.asyncio
    async def test_save_match_timeline(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test saving match timeline to database."""
        from datetime import datetime

        # Create a match first
        match = Match(
            match_id="EUW1_12345678",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.commit()

        # Create timeline DTO
        timeline_dto = MatchTimelineDto(
            metadata={"matchId": "EUW1_12345678", "participants": []},
            info={
                "frameInterval": 60000,
                "frames": [
                    {
                        "events": [],
                        "participantFrames": {},
                        "timestamp": 0,
                    }
                ],
            },
        )

        # Save timeline
        service = MatchService(async_session)
        saved_timeline = await service.save_match_timeline("EUW1_12345678", timeline_dto)

        assert saved_timeline.match_id == "EUW1_12345678"
        assert saved_timeline.timeline_data["metadata"]["matchId"] == "EUW1_12345678"
        assert "frames" in saved_timeline.timeline_data["info"]

    @pytest.mark.asyncio
    async def test_get_match_timeline(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test retrieving match timeline from database."""
        from datetime import datetime

        # Create a match first
        match = Match(
            match_id="EUW1_12345678",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.commit()

        # Create timeline directly in DB
        timeline = MatchTimeline(
            match_id="EUW1_12345678",
            timeline_data={
                "metadata": {"matchId": "EUW1_12345678"},
                "info": {"frameInterval": 60000, "frames": []},
            },
        )
        async_session.add(timeline)
        await async_session.commit()

        # Retrieve timeline
        service = MatchService(async_session)
        retrieved = await service.get_match_timeline("EUW1_12345678")

        assert retrieved is not None
        assert retrieved.metadata["matchId"] == "EUW1_12345678"
        assert retrieved.info["frameInterval"] == 60000

    @pytest.mark.asyncio
    async def test_get_match_timeline_not_found(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test retrieving non-existent match timeline."""
        service = MatchService(async_session)
        retrieved = await service.get_match_timeline("NONEXISTENT")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_fetch_and_save_timeline(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test fetching timeline from API and saving to database."""
        from datetime import datetime

        from lol_data_center.api_client.riot_client import Region

        # Create a match first
        match = Match(
            match_id="EUW1_12345678",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.commit()

        # Mock Riot API client
        mock_client = AsyncMock()
        mock_client.get_match_timeline = AsyncMock(
            return_value=MatchTimelineDto(
                metadata={"matchId": "EUW1_12345678"},
                info={"frameInterval": 60000, "frames": []},
            )
        )

        # Fetch and save timeline
        service = MatchService(async_session)
        saved_timeline = await service.fetch_and_save_timeline(
            "EUW1_12345678", mock_client, Region.EUROPE
        )

        assert saved_timeline is not None
        assert saved_timeline.match_id == "EUW1_12345678"
        mock_client.get_match_timeline.assert_called_once_with("EUW1_12345678", Region.EUROPE)

    @pytest.mark.asyncio
    async def test_save_timeline_duplicate(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test that saving duplicate timeline returns existing one."""
        from datetime import datetime

        # Create a match first
        match = Match(
            match_id="EUW1_12345678",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.commit()

        # Create timeline DTO
        timeline_dto = MatchTimelineDto(
            metadata={"matchId": "EUW1_12345678"},
            info={"frameInterval": 60000, "frames": []},
        )

        # Save timeline twice
        service = MatchService(async_session)
        first = await service.save_match_timeline("EUW1_12345678", timeline_dto)
        second = await service.save_match_timeline("EUW1_12345678", timeline_dto)

        # Should return the same instance
        assert first.id == second.id
