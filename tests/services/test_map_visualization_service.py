"""Tests for map visualization service."""

from datetime import UTC, datetime

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import Match, MatchTimeline, TimelineParticipantFrame
from lol_data_center.services.map_visualization_service import (
    MAP_HEIGHT,
    MAP_WIDTH,
    MapVisualizationService,
)


@pytest_asyncio.fixture
async def match_with_positions(
    async_session: AsyncSession,
    tracked_player,
) -> Match:
    """Create a match with timeline and position data."""
    match = Match(
        match_id="test-match-viz-123",
        data_version="2",
        game_creation=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
        game_duration=1800,
        game_end_timestamp=datetime(2026, 1, 24, 12, 30, 0, tzinfo=UTC),
        game_mode="CLASSIC",
        game_name="",
        game_type="MATCHED_GAME",
        game_version="14.1.123.456",
        map_id=11,
        platform_id="EUW1",
        queue_id=420,
        tournament_code=None,
    )
    async_session.add(match)
    await async_session.flush()

    timeline = MatchTimeline(
        match_db_id=match.id,
        match_id=match.match_id,
        data_version="2",
        frame_interval=60000,
        game_id=123456,
        events={},
        events_filtered=False,
    )
    async_session.add(timeline)
    await async_session.flush()

    # Create position frames with sample data
    np.random.seed(42)
    positions_x = np.random.normal(loc=7500, scale=2000, size=20).astype(int)
    positions_y = np.random.normal(loc=7500, scale=2000, size=20).astype(int)

    positions_x = np.clip(positions_x, 0, MAP_WIDTH)
    positions_y = np.clip(positions_y, 0, MAP_HEIGHT)

    for i, (x, y) in enumerate(zip(positions_x, positions_y)):
        x_int = int(x)
        y_int = int(y)

        frame = TimelineParticipantFrame(
            timeline_id=timeline.id,
            match_id=match.match_id,
            puuid=tracked_player.puuid,
            player_id=tracked_player.id,
            timestamp=60000 * (i + 1),
            participant_id=1,
            level=i + 1,
            current_gold=i * 100,
            total_gold=i * 200,
            gold_per_second=100,
            xp=i * 500,
            minions_killed=i * 5,
            jungle_minions_killed=i,
            position_x=x_int,
            position_y=y_int,
            time_enemy_spent_controlled=0,
        )
        async_session.add(frame)

    await async_session.commit()
    return match


@pytest.mark.asyncio
async def test_generate_player_heatmap(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Test generating a player heatmap."""
    service = MapVisualizationService(async_session)

    heatmap_bytes = await service.generate_player_heatmap(tracked_player.puuid)

    # Verify PNG output
    assert isinstance(heatmap_bytes, bytes)
    assert len(heatmap_bytes) > 0
    assert heatmap_bytes[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_generate_player_heatmap_no_data(
    async_session: AsyncSession,
) -> None:
    """Test that error is raised when no data exists."""
    service = MapVisualizationService(async_session)

    with pytest.raises(ValueError, match="No position data found"):
        await service.generate_player_heatmap("nonexistent-puuid")


@pytest.mark.asyncio
async def test_generate_player_heatmap_with_map_overlay(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Test generating heatmap with map overlay."""
    service = MapVisualizationService(async_session)

    heatmap_bytes = await service.generate_player_heatmap_with_map_overlay(
        tracked_player.puuid
    )

    # Verify PNG output
    assert isinstance(heatmap_bytes, bytes)
    assert len(heatmap_bytes) > 0
    assert heatmap_bytes[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_generate_player_heatmap_max_samples(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Test max_samples parameter."""
    service = MapVisualizationService(async_session)

    heatmap_bytes = await service.generate_player_heatmap(
        tracked_player.puuid,
        max_samples=5,
    )

    # Verify PNG output
    assert isinstance(heatmap_bytes, bytes)
    assert len(heatmap_bytes) > 0
    assert heatmap_bytes[:8] == b"\x89PNG\r\n\x1a\n"





