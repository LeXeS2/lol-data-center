"""Tests for map visualization service."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import (
    Match,
    MatchParticipant,
    MatchTimeline,
    TimelineParticipantFrame,
)
from lol_data_center.services.map_visualization_service import MapVisualizationService


@pytest_asyncio.fixture
async def match_with_positions(
    async_session: AsyncSession,
    tracked_player,
) -> Match:
    """Create a match with timeline and position data."""
    def create_match(match_id: str, game_creation: datetime) -> Match:
        match_obj = Match(
            match_id=match_id,
            data_version="2",
            game_creation=game_creation,
            game_duration=1800,
            game_end_timestamp=game_creation.replace(minute=game_creation.minute + 30),
            game_mode="CLASSIC",
            game_name="",
            game_type="MATCHED_GAME",
            game_version="14.1.123.456",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
            tournament_code=None,
        )
        async_session.add(match_obj)
        return match_obj

    def create_participant(
        match_obj: Match,
        team_id: int,
        champion_name: str,
        team_position: str,
    ) -> MatchParticipant:
        participant = MatchParticipant(
            match_db_id=match_obj.id,
            match_id=match_obj.match_id,
            puuid=tracked_player.puuid,
            player_id=tracked_player.id,
            game_creation=match_obj.game_creation,
            summoner_name=tracked_player.game_name,
            summoner_id=None,
            riot_id_game_name=tracked_player.game_name,
            riot_id_tagline=tracked_player.tag_line,
            profile_icon=1,
            summoner_level=100,
            champion_id=1,
            champion_name=champion_name,
            champion_level=1,
            team_id=team_id,
            team_position=team_position,
            individual_position=team_position,
            lane=team_position,
            role="SOLO",
            kills=1,
            deaths=1,
            assists=1,
            kda=2.0,
            total_damage_dealt=1,
            total_damage_dealt_to_champions=1,
            total_damage_taken=1,
            damage_self_mitigated=1,
            largest_killing_spree=1,
            largest_multi_kill=1,
            killing_sprees=1,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            gold_earned=1,
            gold_spent=1,
            total_minions_killed=1,
            neutral_minions_killed=0,
            vision_score=1,
            wards_placed=1,
            wards_killed=0,
            vision_wards_bought_in_game=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
            win=True,
            first_blood_kill=False,
            first_blood_assist=False,
            first_tower_kill=False,
            first_tower_assist=False,
            game_ended_in_surrender=False,
            game_ended_in_early_surrender=False,
            time_played=match_obj.game_duration,
            item0=0,
            item1=0,
            item2=0,
            item3=0,
            item4=0,
            item5=0,
            item6=0,
            summoner1_id=1,
            summoner2_id=2,
        )
        async_session.add(participant)
        return participant

    # Blue-side match (team 100)
    match_blue = create_match(
        "test-match-viz-blue",
        datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
    )
    await async_session.flush()
    create_participant(match_blue, team_id=100, champion_name="Ashe", team_position="TOP")

    timeline_blue = MatchTimeline(
        match_db_id=match_blue.id,
        match_id=match_blue.match_id,
        data_version="2",
        frame_interval=60000,
        game_id=123456,
        events={},
        events_filtered=False,
    )
    async_session.add(timeline_blue)
    await async_session.flush()

    blue_positions = [(1200, 1800), (1600, 2200)]
    for i, (x, y) in enumerate(blue_positions):
        frame = TimelineParticipantFrame(
            timeline_id=timeline_blue.id,
            match_id=match_blue.match_id,
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
            position_x=x,
            position_y=y,
            time_enemy_spent_controlled=0,
        )
        async_session.add(frame)

    # Red-side match (team 200) to verify mirroring
    match_red = create_match(
        "test-match-viz-red",
        datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC),
    )
    await async_session.flush()
    create_participant(match_red, team_id=200, champion_name="LeeSin", team_position="JUNGLE")

    timeline_red = MatchTimeline(
        match_db_id=match_red.id,
        match_id=match_red.match_id,
        data_version="2",
        frame_interval=60000,
        game_id=123457,
        events={},
        events_filtered=False,
    )
    async_session.add(timeline_red)
    await async_session.flush()

    red_positions = [(14000, 13000), (13500, 12500)]
    for i, (x, y) in enumerate(red_positions):
        frame = TimelineParticipantFrame(
            timeline_id=timeline_red.id,
            match_id=match_red.match_id,
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
            position_x=x,
            position_y=y,
            time_enemy_spent_controlled=0,
        )
        async_session.add(frame)

    await async_session.commit()
    return match_blue


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


@pytest.mark.asyncio
async def test_filter_by_role(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Ensure role filter limits frames to matching games."""
    service = MapVisualizationService(async_session)

    x_positions, y_positions = await service._load_positions(
        tracked_player.puuid,
        role="JUNGLE",
        champion=None,
    )

    assert list(zip(x_positions.tolist(), y_positions.tolist())) == [
        (2000, 1000),
        (2500, 1500),
    ]


@pytest.mark.asyncio
async def test_filter_by_champion(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Ensure champion filter limits frames to matching champion."""
    service = MapVisualizationService(async_session)

    x_positions, y_positions = await service._load_positions(
        tracked_player.puuid,
        role=None,
        champion="ashe",
    )

    assert list(zip(x_positions.tolist(), y_positions.tolist())) == [
        (1200, 1800),
        (1600, 2200),
    ]


@pytest.mark.asyncio
async def test_positions_are_mirrored_for_red_side(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    """Verify red-side positions are mirrored to bottom-side perspective."""
    service = MapVisualizationService(async_session)

    x_positions, y_positions = await service._load_positions(
        tracked_player.puuid,
        role=None,
        champion=None,
    )

    assert set(zip(x_positions.tolist(), y_positions.tolist())) == {
        (1200, 1800),
        (1600, 2200),
        (2000, 1000),
        (2500, 1500),
    }


@pytest.mark.asyncio
async def test_validate_filters_accepts_valid_inputs(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    service = MapVisualizationService(async_session)

    await service.validate_filters(
        tracked_player.puuid,
        role="TOP",
        champion="Ashe",
    )


@pytest.mark.asyncio
async def test_validate_filters_invalid_role(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    service = MapVisualizationService(async_session)

    with pytest.raises(ValueError, match="Invalid role"):
        await service.validate_filters(tracked_player.puuid, role="INVALID", champion=None)


@pytest.mark.asyncio
async def test_validate_filters_unknown_champion(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    service = MapVisualizationService(async_session)

    with pytest.raises(ValueError, match="Champion 'Zed' not found"):
        await service.validate_filters(tracked_player.puuid, champion="Zed")


@pytest.mark.asyncio
async def test_validate_filters_missing_combination(
    async_session: AsyncSession,
    tracked_player,
    match_with_positions: Match,
) -> None:
    service = MapVisualizationService(async_session)

    with pytest.raises(ValueError, match="No games found for champion 'Ashe' in role 'JUNGLE'"):
        await service.validate_filters(tracked_player.puuid, role="JUNGLE", champion="Ashe")





