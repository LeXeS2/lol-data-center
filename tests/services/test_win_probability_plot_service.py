"""Tests for win probability plot service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import (
    Match,
    MatchParticipant,
    MatchTimeline,
    TimelineParticipantFrame,
)
from lol_data_center.ml.win_probability import WinProbabilityPredictor
from lol_data_center.services.win_probability_plot_service import WinProbabilityPlotService


@pytest_asyncio.fixture
async def match_with_timeline(
    async_session: AsyncSession,
    sample_player,
) -> tuple[Match, MatchParticipant]:
    """Create a match with timeline data."""
    # Create match
    match_obj = Match(
        match_id="TEST_MATCH_123",
        data_version="2",
        game_creation=datetime(2026, 2, 6, 12, 0, 0, tzinfo=UTC),
        game_duration=1800,  # 30 minutes
        game_end_timestamp=datetime(2026, 2, 6, 12, 30, 0, tzinfo=UTC),
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
    await async_session.flush()

    # Create participant
    participant = MatchParticipant(
        match_db_id=match_obj.id,
        match_id=match_obj.match_id,
        puuid=sample_player.puuid,
        player_id=sample_player.id,
        game_creation=match_obj.game_creation,
        summoner_name=sample_player.game_name,
        summoner_id=None,
        riot_id_game_name=sample_player.game_name,
        riot_id_tagline=sample_player.tag_line,
        profile_icon=1,
        summoner_level=100,
        champion_id=1,
        champion_name="Aatrox",
        champion_level=18,
        team_id=100,
        team_position="TOP",
        individual_position="TOP",
        lane="TOP",
        role="SOLO",
        kills=10,
        deaths=2,
        assists=5,
        kda=7.5,
        total_damage_dealt=50000,
        total_damage_dealt_to_champions=25000,
        total_damage_taken=15000,
        damage_self_mitigated=10000,
        largest_killing_spree=5,
        largest_multi_kill=2,
        killing_sprees=3,
        double_kills=2,
        triple_kills=0,
        quadra_kills=0,
        penta_kills=0,
        gold_earned=15000,
        gold_spent=14000,
        total_minions_killed=200,
        neutral_minions_killed=0,
        vision_score=30,
        wards_placed=15,
        wards_killed=5,
        vision_wards_bought_in_game=3,
        turret_kills=2,
        turret_takedowns=2,
        inhibitor_kills=0,
        inhibitor_takedowns=0,
        baron_kills=0,
        dragon_kills=1,
        objective_stolen=0,
        total_heal=5000,
        total_heals_on_teammates=0,
        total_damage_shielded_on_teammates=0,
        total_time_cc_dealt=50,
        time_ccing_others=50,
        first_blood_kill=True,
        first_blood_assist=False,
        first_tower_kill=True,
        first_tower_assist=False,
        game_ended_in_surrender=False,
        game_ended_in_early_surrender=False,
        time_played=1800,
        item0=0,
        item1=0,
        item2=0,
        item3=0,
        item4=0,
        item5=0,
        item6=0,
        summoner1_id=4,
        summoner2_id=14,
        win=True,
    )
    async_session.add(participant)
    await async_session.flush()

    # Create timeline
    timeline = MatchTimeline(
        match_db_id=match_obj.id,
        match_id=match_obj.match_id,
        data_version="2",
        frame_interval=60000,  # 1 minute
        game_id=12345,
        events={"events": []},
        events_filtered=False,
    )
    async_session.add(timeline)
    await async_session.flush()

    # Create timeline frames (every minute for 5 minutes)
    for minute in range(1, 6):
        timestamp_ms = minute * 60000
        frame = TimelineParticipantFrame(
            timeline_id=timeline.id,
            match_id=match_obj.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            timestamp=timestamp_ms,
            participant_id=1,
            level=minute * 3,  # Level increases
            current_gold=1000 * minute,
            total_gold=2000 * minute,
            gold_per_second=10,
            xp=500 * minute,
            minions_killed=10 * minute,
            jungle_minions_killed=0,
            position_x=5000,
            position_y=5000,
            time_enemy_spent_controlled=0,
            # Damage stats
            total_damage_done_to_champions=500 * minute,
            total_damage_taken=300 * minute,
        )
        async_session.add(frame)

    await async_session.commit()

    return (match_obj, participant)


@pytest.mark.asyncio
async def test_get_player_nth_last_match(
    async_session: AsyncSession,
    sample_player,
    match_with_timeline,
) -> None:
    """Test getting the nth last match for a player."""
    service = WinProbabilityPlotService(async_session)

    # Get most recent match (n=1)
    result = await service.get_player_nth_last_match(sample_player.puuid, 1)
    assert result is not None
    match, participant = result
    assert match.match_id == "TEST_MATCH_123"
    assert participant.puuid == sample_player.puuid


@pytest.mark.asyncio
async def test_get_player_nth_last_match_not_found(
    async_session: AsyncSession,
    sample_player,
    match_with_timeline,
) -> None:
    """Test getting a match that doesn't exist."""
    service = WinProbabilityPlotService(async_session)

    # Try to get 10th match when only 1 exists
    result = await service.get_player_nth_last_match(sample_player.puuid, 10)
    assert result is None


@pytest.mark.asyncio
async def test_get_player_nth_last_match_invalid_n(
    async_session: AsyncSession,
    sample_player,
) -> None:
    """Test getting match with invalid n parameter."""
    service = WinProbabilityPlotService(async_session)

    # n must be >= 1
    with pytest.raises(ValueError, match="n must be >= 1"):
        await service.get_player_nth_last_match(sample_player.puuid, 0)


@pytest.mark.asyncio
async def test_extract_features_from_frame(
    async_session: AsyncSession,
    match_with_timeline,
) -> None:
    """Test feature extraction from a timeline frame."""
    service = WinProbabilityPlotService(async_session)
    match, participant = match_with_timeline

    # Get a frame
    from sqlalchemy import select

    result = await async_session.execute(
        select(TimelineParticipantFrame)
        .where(TimelineParticipantFrame.match_id == match.match_id)
        .limit(1)
    )
    frame = result.scalar_one()

    # Extract features
    features = service._extract_features_from_frame(frame, frame.timestamp)

    # Verify basic features are present
    assert "game_duration_minutes" in features
    assert "champion_level" in features
    assert "gold_per_min" in features
    assert "cs_per_min" in features

    # Verify calculations
    assert features["champion_level"] == frame.level
    assert features["game_duration_minutes"] == frame.timestamp / 60000.0


@pytest.mark.asyncio
async def test_generate_win_probability_plot_no_timeline(
    async_session: AsyncSession,
    sample_player,
) -> None:
    """Test plot generation when no timeline data exists."""
    service = WinProbabilityPlotService(async_session)

    # Create a match without timeline
    match_obj = Match(
        match_id="NO_TIMELINE_MATCH",
        data_version="2",
        game_creation=datetime(2026, 2, 6, 12, 0, 0, tzinfo=UTC),
        game_duration=1800,
        game_end_timestamp=datetime(2026, 2, 6, 12, 30, 0, tzinfo=UTC),
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
    await async_session.commit()

    # Try to generate plot without timeline
    with pytest.raises(ValueError, match="No timeline data found"):
        await service.generate_win_probability_plot(
            match_id="NO_TIMELINE_MATCH",
            puuid=sample_player.puuid,
            predictor=None,
        )


@pytest.mark.asyncio
async def test_generate_win_probability_plot_no_model(
    async_session: AsyncSession,
    sample_player,
    match_with_timeline,
) -> None:
    """Test plot generation when model is not available."""
    service = WinProbabilityPlotService(async_session)
    match, participant = match_with_timeline

    # Try to generate plot without model
    with pytest.raises(ValueError, match="Win probability model not available"):
        await service.generate_win_probability_plot(
            match_id=match.match_id,
            puuid=sample_player.puuid,
            predictor=None,
        )


@pytest.mark.asyncio
async def test_generate_win_probability_plot_success(
    async_session: AsyncSession,
    sample_player,
    match_with_timeline,
) -> None:
    """Test successful plot generation with mock predictor."""
    service = WinProbabilityPlotService(async_session)
    match, participant = match_with_timeline

    # Create mock predictor
    predictor = MagicMock(spec=WinProbabilityPredictor)
    predictor.model = MagicMock()  # Model is available

    # Mock predict_win_probability to return increasing probabilities
    prediction_count = [0]

    def mock_predict(features):
        prediction_count[0] += 1
        # Return increasing win probability
        return {"win_probability": 0.3 + (prediction_count[0] * 0.1)}

    predictor.predict_win_probability.side_effect = mock_predict

    # Generate plot
    buffer = await service.generate_win_probability_plot(
        match_id=match.match_id,
        puuid=sample_player.puuid,
        predictor=predictor,
    )

    # Verify buffer is not empty
    assert buffer is not None
    assert buffer.tell() == 0  # Buffer should be at start
    content = buffer.read()
    assert len(content) > 0
    assert content.startswith(b"\x89PNG")  # PNG file signature
