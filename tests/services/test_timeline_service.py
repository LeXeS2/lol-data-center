"""Tests for timeline service."""

import pytest
from sqlalchemy import select

from lol_data_center.database.models import MatchTimeline, TimelineParticipantFrame
from lol_data_center.schemas.riot_api import (
    EventDto,
    FrameDto,
    ParticipantFrameDto,
    TimelineDto,
    TimelineInfoDto,
    TimelineMetadataDto,
)
from lol_data_center.services.timeline_service import TimelineService


@pytest.fixture
def sample_timeline_dto() -> TimelineDto:
    """Create a sample timeline DTO for testing."""
    return TimelineDto(
        metadata=TimelineMetadataDto(
            dataVersion="2",
            matchId="EUW1_1234567890",
            participants=[
                "tracked-player-1-puuid",  # Participant 1
                "other-player-puuid",  # Participant 2
                "tracked-player-2-puuid",  # Participant 3
                "another-player-puuid",  # Participant 4
                "yet-another-puuid",  # Participant 5
                "bot-player-puuid",  # Participant 6
                "random-puuid-1",  # Participant 7
                "random-puuid-2",  # Participant 8
                "random-puuid-3",  # Participant 9
                "random-puuid-4",  # Participant 10
            ],
        ),
        info=TimelineInfoDto(
            frameInterval=60000,
            gameId=1234567890,
            participants=[
                {"participantId": 1, "puuid": "tracked-player-1-puuid"},
                {"participantId": 2, "puuid": "other-player-puuid"},
                {"participantId": 3, "puuid": "tracked-player-2-puuid"},
            ],
            frames=[
                FrameDto(
                    timestamp=0,
                    participantFrames={
                        "1": ParticipantFrameDto(
                            participantId=1,
                            level=1,
                            currentGold=500,
                            totalGold=500,
                            goldPerSecond=0,
                            xp=0,
                            minionsKilled=0,
                            jungleMinionsKilled=0,
                            x=100,
                            y=100,
                            timeEnemySpentControlled=0,
                        ),
                        "2": ParticipantFrameDto(
                            participantId=2,
                            level=1,
                            currentGold=500,
                            totalGold=500,
                            goldPerSecond=0,
                            xp=0,
                            minionsKilled=0,
                            jungleMinionsKilled=0,
                            x=200,
                            y=200,
                            timeEnemySpentControlled=0,
                        ),
                        "3": ParticipantFrameDto(
                            participantId=3,
                            level=1,
                            currentGold=500,
                            totalGold=500,
                            goldPerSecond=0,
                            xp=0,
                            minionsKilled=0,
                            jungleMinionsKilled=0,
                            x=300,
                            y=300,
                            timeEnemySpentControlled=0,
                        ),
                    },
                    events=[
                        EventDto(type="PAUSE_END", timestamp=0),
                        EventDto(
                            type="CHAMPION_KILL",
                            timestamp=30000,
                            killerId=1,
                            victimId=2,
                            assistingParticipantIds=[3],
                        ),
                    ],
                ),
                FrameDto(
                    timestamp=60000,
                    participantFrames={
                        "1": ParticipantFrameDto(
                            participantId=1,
                            level=3,
                            currentGold=800,
                            totalGold=1200,
                            goldPerSecond=10,
                            xp=558,
                            minionsKilled=15,
                            jungleMinionsKilled=0,
                            x=150,
                            y=150,
                            timeEnemySpentControlled=500,
                        ),
                        "3": ParticipantFrameDto(
                            participantId=3,
                            level=2,
                            currentGold=700,
                            totalGold=1100,
                            goldPerSecond=9,
                            xp=400,
                            minionsKilled=12,
                            jungleMinionsKilled=2,
                            x=350,
                            y=350,
                            timeEnemySpentControlled=0,
                        ),
                    },
                    events=[
                        EventDto(type="LEVEL_UP", timestamp=60100, participantId=1),
                        EventDto(
                            type="ITEM_PURCHASED",
                            timestamp=60200,
                            participantId=3,
                            itemId=1001,
                        ),
                    ],
                ),
            ],
        ),
    )


@pytest.mark.asyncio
async def test_save_timeline_filters_events_by_tracked_players(
    async_session, tracked_player, tracked_player_2, match, sample_timeline_dto
):
    """Test that timeline service filters events to tracked players only."""
    service = TimelineService(async_session)

    # Save timeline with event filtering enabled
    timeline = await service.save_timeline(
        sample_timeline_dto,
        match.id,
        filter_events=True,
    )

    assert timeline.match_id == "EUW1_1234567890"
    assert timeline.events_filtered is True

    # Check that only events involving tracked players are saved
    events = timeline.events["events"]
    assert len(events) == 3  # CHAMPION_KILL, LEVEL_UP, ITEM_PURCHASED

    # Verify events
    event_types = [e["type"] for e in events]
    assert "CHAMPION_KILL" in event_types  # Involves participants 1, 2, 3
    assert "LEVEL_UP" in event_types  # Participant 1
    assert "ITEM_PURCHASED" in event_types  # Participant 3
    assert "PAUSE_END" not in event_types  # No participant involved


@pytest.mark.asyncio
async def test_save_timeline_saves_only_tracked_player_frames(
    async_session, tracked_player, tracked_player_2, match, sample_timeline_dto
):
    """Test that only tracked player frames are saved."""
    service = TimelineService(async_session)

    await service.save_timeline(
        sample_timeline_dto,
        match.id,
        filter_events=True,
    )

    # Check participant frames in database
    result = await async_session.execute(
        select(TimelineParticipantFrame).order_by(
            TimelineParticipantFrame.timestamp, TimelineParticipantFrame.participant_id
        )
    )
    frames = list(result.scalars().all())

    # Should have 3 frames (2 tracked players across 2 timestamps, but participant 2 missing in frame 2)
    # Frame 0: participant 1, 3
    # Frame 60000: participant 1, 3
    assert len(frames) == 4

    # Verify frame data
    frame_1_0 = frames[0]
    assert frame_1_0.timestamp == 0
    assert frame_1_0.participant_id == 1
    assert frame_1_0.level == 1
    assert frame_1_0.current_gold == 500
    assert frame_1_0.minions_killed == 0

    frame_3_0 = frames[1]
    assert frame_3_0.timestamp == 0
    assert frame_3_0.participant_id == 3
    assert frame_3_0.level == 1

    frame_1_60 = frames[2]
    assert frame_1_60.timestamp == 60000
    assert frame_1_60.participant_id == 1
    assert frame_1_60.level == 3
    assert frame_1_60.minions_killed == 15

    frame_3_60 = frames[3]
    assert frame_3_60.timestamp == 60000
    assert frame_3_60.participant_id == 3
    assert frame_3_60.level == 2
    assert frame_3_60.jungle_minions_killed == 2


@pytest.mark.asyncio
async def test_save_timeline_without_filtering_saves_all_events(
    async_session, tracked_player, tracked_player_2, match, sample_timeline_dto
):
    """Test that timeline service saves all events when filtering is disabled."""
    service = TimelineService(async_session)

    timeline = await service.save_timeline(
        sample_timeline_dto,
        match.id,
        filter_events=False,
    )

    assert timeline.events_filtered is False

    # All events should be saved
    events = timeline.events["events"]
    assert len(events) == 4  # All events from both frames

    event_types = [e["type"] for e in events]
    assert "PAUSE_END" in event_types
    assert "CHAMPION_KILL" in event_types
    assert "LEVEL_UP" in event_types
    assert "ITEM_PURCHASED" in event_types


@pytest.mark.asyncio
async def test_timeline_exists(
    async_session, tracked_player, tracked_player_2, match, sample_timeline_dto
):
    """Test timeline_exists check."""
    service = TimelineService(async_session)

    # Should not exist initially
    assert await service.timeline_exists("EUW1_1234567890") is False

    # Save timeline
    await service.save_timeline(sample_timeline_dto, match.id, filter_events=True)

    # Should exist now
    assert await service.timeline_exists("EUW1_1234567890") is True


@pytest.mark.asyncio
async def test_get_participant_frames(
    async_session, tracked_player, tracked_player_2, match, sample_timeline_dto
):
    """Test getting participant frames by match and player."""
    service = TimelineService(async_session)

    await service.save_timeline(sample_timeline_dto, match.id, filter_events=True)

    # Get all frames for match
    all_frames = await service.get_participant_frames("EUW1_1234567890")
    assert len(all_frames) == 4  # 2 tracked players × 2 timestamps (but participant 2 missing in frame 2)

    # Get frames for specific player
    player_1_frames = await service.get_participant_frames(
        "EUW1_1234567890", tracked_player.puuid
    )
    assert len(player_1_frames) == 2  # 2 timestamps
    assert all(f.participant_id == 1 for f in player_1_frames)
    assert player_1_frames[0].timestamp == 0
    assert player_1_frames[1].timestamp == 60000
