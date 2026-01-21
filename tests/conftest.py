"""Pytest fixtures for LoL Data Center tests."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lol_data_center.database.models import Base, PlayerRecord, TrackedPlayer
from lol_data_center.schemas.riot_api import (
    AccountDto,
    MatchDto,
    MatchInfoDto,
    MatchMetadataDto,
    ParticipantDto,
    SummonerDto,
    TeamDto,
)

# Set environment variables for testing
os.environ.setdefault("RIOT_API_KEY", "test-api-key")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def sample_player(async_session: AsyncSession) -> TrackedPlayer:
    """Create a sample tracked player."""
    player = TrackedPlayer(
        puuid="test-puuid-12345",
        game_name="TestPlayer",
        tag_line="EUW",
        region="europe",
        summoner_id=None,  # No longer returned by API
        account_id=None,  # No longer returned by API
        profile_icon_id=1,
        summoner_level=100,
        polling_enabled=True,
    )
    async_session.add(player)
    await async_session.flush()

    records = PlayerRecord(
        player_id=player.id,
        max_kills=15,
        max_deaths=12,
        max_assists=25,
        max_kda=8.0,
        max_cs=300,
        max_damage_to_champions=50000,
        max_vision_score=60,
        max_gold=18000,
        min_deaths=2,
        total_games=50,
        total_wins=28,
        total_losses=22,
    )
    async_session.add(records)
    await async_session.commit()

    return player


@pytest.fixture
def sample_account_dto() -> AccountDto:
    """Create a sample AccountDto."""
    return AccountDto(
        puuid="test-puuid-12345",
        gameName="TestPlayer",
        tagLine="EUW",
    )


@pytest.fixture
def sample_summoner_dto() -> SummonerDto:
    """Create a sample SummonerDto."""
    return SummonerDto(
        accountId=None,  # No longer returned by API
        profileIconId=123,
        revisionDate=1234567890,
        id=None,  # No longer returned by API
        puuid="test-puuid-12345",
        summonerLevel=100,
    )


@pytest.fixture
def sample_participant_dto() -> ParticipantDto:
    """Create a sample ParticipantDto."""
    return ParticipantDto(
        puuid="test-puuid-12345",
        summonerName="TestPlayer",
        summonerId=None,  # No longer returned by API
        riotIdGameName="TestPlayer",
        riotIdTagline="EUW",
        profileIcon=1,
        summonerLevel=100,
        championId=1,
        championName="Annie",
        champLevel=18,
        teamId=100,
        teamPosition="MIDDLE",
        individualPosition="MIDDLE",
        lane="MIDDLE",
        role="SOLO",
        kills=10,
        deaths=3,
        assists=15,
        totalDamageDealt=150000,
        totalDamageDealtToChampions=45000,
        totalDamageTaken=25000,
        damageSelfMitigated=10000,
        largestKillingSpree=5,
        largestMultiKill=2,
        killingSprees=2,
        doubleKills=1,
        tripleKills=0,
        quadraKills=0,
        pentaKills=0,
        goldEarned=15000,
        goldSpent=14500,
        totalMinionsKilled=200,
        neutralMinionsKilled=30,
        visionScore=40,
        wardsPlaced=15,
        wardsKilled=5,
        visionWardsBoughtInGame=3,
        turretKills=2,
        turretTakedowns=3,
        inhibitorKills=1,
        inhibitorTakedowns=1,
        baronKills=0,
        dragonKills=0,
        objectivesStolen=0,
        totalHeal=5000,
        totalHealsOnTeammates=0,
        totalDamageShieldedOnTeammates=0,
        totalTimeCCDealt=150,
        timeCCingOthers=30,
        win=True,
        firstBloodKill=True,
        firstBloodAssist=False,
        firstTowerKill=False,
        firstTowerAssist=True,
        gameEndedInSurrender=False,
        gameEndedInEarlySurrender=False,
        timePlayed=1800,
        item0=3089,
        item1=3157,
        item2=3020,
        item3=3135,
        item4=3165,
        item5=3102,
        item6=3364,
        summoner1Id=4,
        summoner2Id=12,
    )


@pytest.fixture
def sample_match_dto(sample_participant_dto: ParticipantDto) -> MatchDto:
    """Create a sample MatchDto."""
    # Create 9 more participants for a full match
    other_participants = []
    for i in range(9):
        p = ParticipantDto(
            puuid=f"other-puuid-{i}",
            summonerName=f"Player{i}",
            summonerId=None,  # No longer returned by API
            riotIdGameName=f"Player{i}",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=50 + i,
            championId=10 + i,
            championName=f"Champion{i}",
            champLevel=18,
            teamId=100 if i < 4 else 200,
            teamPosition="",
            individualPosition="",
            lane="",
            role="",
            kills=5,
            deaths=5,
            assists=5,
            totalDamageDealt=100000,
            totalDamageDealtToChampions=30000,
            totalDamageTaken=20000,
            damageSelfMitigated=8000,
            goldEarned=12000,
            goldSpent=11000,
            totalMinionsKilled=150,
            neutralMinionsKilled=20,
            win=i < 4,  # First 4 win (same team as sample)
            summoner1Id=4,
            summoner2Id=12,
        )
        other_participants.append(p)

    return MatchDto(
        metadata=MatchMetadataDto(
            dataVersion="2",
            matchId="EUW1_12345678",
            participants=["test-puuid-12345"] + [f"other-puuid-{i}" for i in range(9)],
        ),
        info=MatchInfoDto(
            gameCreation=1704067200000,
            gameDuration=1800,
            gameEndTimestamp=1704069000000,
            gameId=12345678,
            gameMode="CLASSIC",
            gameName="",
            gameType="MATCHED_GAME",
            gameVersion="14.1.123.456",
            mapId=11,
            participants=[sample_participant_dto] + other_participants,
            platformId="EUW1",
            queueId=420,
            teams=[
                TeamDto(teamId=100, win=True),
                TeamDto(teamId=200, win=False),
            ],
            tournamentCode=None,
        ),
    )


@pytest.fixture
def mock_riot_client() -> MagicMock:
    """Create a mock Riot API client."""
    client = MagicMock()
    client.get_account_by_riot_id = AsyncMock()
    client.get_account_by_puuid = AsyncMock()
    client.get_summoner_by_puuid = AsyncMock()
    client.get_match_ids = AsyncMock()
    client.get_match = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_discord_notifier() -> MagicMock:
    """Create a mock Discord notifier."""
    notifier = MagicMock()
    notifier.send_message = AsyncMock(return_value=True)
    notifier.send_achievement = AsyncMock(return_value=True)
    notifier.close = AsyncMock()
    return notifier
