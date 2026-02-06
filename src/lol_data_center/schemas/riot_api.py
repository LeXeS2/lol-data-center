"""Pydantic schemas for Riot API responses.

These schemas validate and type the JSON responses from the Riot API.
Fields are based on the official Riot API documentation.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class AccountDto(BaseModel):
    """Riot Account information from account-v1 API."""

    puuid: str = Field(..., description="Player Universal Unique Identifier")
    game_name: str = Field(..., alias="gameName", description="Game name part of Riot ID")
    tag_line: str = Field(..., alias="tagLine", description="Tag line part of Riot ID")

    model_config = {"populate_by_name": True}


class SummonerDto(BaseModel):
    """Summoner information from summoner-v4 API.

    Note: As of recent API changes, accountId and id are no longer returned.
    """

    account_id: str | None = Field(None, alias="accountId")
    profile_icon_id: int = Field(..., alias="profileIconId")
    revision_date: int = Field(..., alias="revisionDate")
    id: str | None = Field(None, description="Encrypted summoner ID (deprecated)")
    puuid: str
    summoner_level: int = Field(..., alias="summonerLevel")

    model_config = {"populate_by_name": True}


class ParticipantDto(BaseModel):
    """Participant data from match-v5 API.

    This contains all the stats for a single player in a match.
    Note: The Riot API has many more fields, we capture the most important ones.
    """

    # Player identification
    puuid: str
    summoner_name: str = Field(..., alias="summonerName")
    summoner_id: str | None = Field(None, alias="summonerId")
    riot_id_game_name: str | None = Field(None, alias="riotIdGameName")
    riot_id_tagline: str | None = Field(None, alias="riotIdTagline")
    profile_icon: int = Field(..., alias="profileIcon")
    summoner_level: int = Field(..., alias="summonerLevel")

    # Champion & Role
    champion_id: int = Field(..., alias="championId")
    champion_name: str = Field(..., alias="championName")
    champ_level: int = Field(..., alias="champLevel")
    team_id: int = Field(..., alias="teamId")
    team_position: str = Field("", alias="teamPosition")
    individual_position: str = Field("", alias="individualPosition")
    lane: str = Field("")
    role: str = Field("")

    # Core Stats
    kills: int
    deaths: int
    assists: int

    # Combat Stats
    total_damage_dealt: int = Field(..., alias="totalDamageDealt")
    total_damage_dealt_to_champions: int = Field(..., alias="totalDamageDealtToChampions")
    total_damage_taken: int = Field(..., alias="totalDamageTaken")
    damage_self_mitigated: int = Field(..., alias="damageSelfMitigated")
    largest_killing_spree: int = Field(0, alias="largestKillingSpree")
    largest_multi_kill: int = Field(0, alias="largestMultiKill")
    killing_sprees: int = Field(0, alias="killingSprees")
    double_kills: int = Field(0, alias="doubleKills")
    triple_kills: int = Field(0, alias="tripleKills")
    quadra_kills: int = Field(0, alias="quadraKills")
    penta_kills: int = Field(0, alias="pentaKills")

    # Economy
    gold_earned: int = Field(..., alias="goldEarned")
    gold_spent: int = Field(..., alias="goldSpent")
    total_minions_killed: int = Field(..., alias="totalMinionsKilled")
    neutral_minions_killed: int = Field(..., alias="neutralMinionsKilled")

    # Vision
    vision_score: int = Field(0, alias="visionScore")
    wards_placed: int = Field(0, alias="wardsPlaced")
    wards_killed: int = Field(0, alias="wardsKilled")
    vision_wards_bought_in_game: int = Field(0, alias="visionWardsBoughtInGame")

    # Objectives
    turret_kills: int = Field(0, alias="turretKills")
    turret_takedowns: int = Field(0, alias="turretTakedowns")
    inhibitor_kills: int = Field(0, alias="inhibitorKills")
    inhibitor_takedowns: int = Field(0, alias="inhibitorTakedowns")
    baron_kills: int = Field(0, alias="baronKills")
    dragon_kills: int = Field(0, alias="dragonKills")
    objectives_stolen: int = Field(0, alias="objectivesStolen")

    # Utility
    total_heal: int = Field(0, alias="totalHeal")
    total_heals_on_teammates: int = Field(0, alias="totalHealsOnTeammates")
    total_damage_shielded_on_teammates: int = Field(0, alias="totalDamageShieldedOnTeammates")
    total_time_cc_dealt: int = Field(0, alias="totalTimeCCDealt")
    time_ccing_others: int = Field(0, alias="timeCCingOthers")

    # Game State
    win: bool
    first_blood_kill: bool = Field(False, alias="firstBloodKill")
    first_blood_assist: bool = Field(False, alias="firstBloodAssist")
    first_tower_kill: bool = Field(False, alias="firstTowerKill")
    first_tower_assist: bool = Field(False, alias="firstTowerAssist")
    game_ended_in_surrender: bool = Field(False, alias="gameEndedInSurrender")
    game_ended_in_early_surrender: bool = Field(False, alias="gameEndedInEarlySurrender")
    time_played: int = Field(0, alias="timePlayed")

    # Items
    item0: int = 0
    item1: int = 0
    item2: int = 0
    item3: int = 0
    item4: int = 0
    item5: int = 0
    item6: int = 0

    # Spells
    summoner1_id: int = Field(..., alias="summoner1Id")
    summoner2_id: int = Field(..., alias="summoner2Id")

    # ML Predictions (not from Riot API, added by our system)
    predicted_win_probability: float | None = Field(
        None, description="Win probability predicted by ML model (0.0-1.0)"
    )

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def kda(self) -> float:
        """Calculate KDA ratio."""
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths


class TeamDto(BaseModel):
    """Team data from match-v5 API."""

    team_id: int = Field(..., alias="teamId")
    win: bool

    model_config = {"populate_by_name": True, "extra": "ignore"}


class MatchInfoDto(BaseModel):
    """Match info data from match-v5 API."""

    game_creation: int = Field(..., alias="gameCreation")
    game_duration: int = Field(..., alias="gameDuration")
    game_end_timestamp: int | None = Field(None, alias="gameEndTimestamp")
    game_id: int = Field(..., alias="gameId")
    game_mode: str = Field(..., alias="gameMode")
    game_name: str = Field("", alias="gameName")
    game_type: str = Field(..., alias="gameType")
    game_version: str = Field(..., alias="gameVersion")
    map_id: int = Field(..., alias="mapId")
    participants: list[ParticipantDto]
    platform_id: str = Field(..., alias="platformId")
    queue_id: int = Field(..., alias="queueId")
    teams: list[TeamDto]
    tournament_code: str | None = Field(None, alias="tournamentCode")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def game_creation_datetime(self) -> datetime:
        """Convert game creation timestamp to datetime."""
        return datetime.fromtimestamp(self.game_creation / 1000, tz=UTC)

    @property
    def game_end_datetime(self) -> datetime | None:
        """Convert game end timestamp to datetime."""
        if self.game_end_timestamp:
            return datetime.fromtimestamp(self.game_end_timestamp / 1000, tz=UTC)
        return None


class MatchMetadataDto(BaseModel):
    """Match metadata from match-v5 API."""

    data_version: str = Field(..., alias="dataVersion")
    match_id: str = Field(..., alias="matchId")
    participants: list[str]  # List of PUUIDs

    model_config = {"populate_by_name": True}


class MatchDto(BaseModel):
    """Complete match data from match-v5 API."""

    metadata: MatchMetadataDto
    info: MatchInfoDto

    def get_participant_by_puuid(self, puuid: str) -> ParticipantDto | None:
        """Get participant data by PUUID."""
        for participant in self.info.participants:
            if participant.puuid == puuid:
                return participant
        return None


class MatchIdsResponse(BaseModel):
    """Response from match-v5 matchlist endpoint.

    The API returns a simple list of match IDs, not an object.
    This is a wrapper for type safety.
    """

    match_ids: list[str]

    @classmethod
    def from_list(cls, match_ids: list[str]) -> "MatchIdsResponse":
        """Create from a list of match IDs."""
        return cls(match_ids=match_ids)


# Timeline DTOs


class PositionDto(BaseModel):
    """Two-dimensional position on the game map."""

    x: int = 0
    y: int = 0

    model_config = {"populate_by_name": True}


class ParticipantFrameDto(BaseModel):
    """Per-participant stats at a specific timestamp in the timeline.

    Contains all stats like gold, xp, position, damage stats, etc. for a single
    participant at a specific frame interval (typically 1 minute).
    """

    participant_id: int = Field(..., alias="participantId")
    level: int = 0
    current_gold: int = Field(0, alias="currentGold")
    total_gold: int = Field(0, alias="totalGold")
    gold_per_second: int = Field(0, alias="goldPerSecond")
    xp: int = 0
    minions_killed: int = Field(0, alias="minionsKilled")
    jungle_minions_killed: int = Field(0, alias="jungleMinionsKilled")
    position: PositionDto | None = Field(None, alias="position")
    time_enemy_spent_controlled: int = Field(0, alias="timeEnemySpentControlled")

    # Damage stats (may not be present in all frames)
    damage_stats: dict[str, int] | None = Field(None, alias="damageStats")
    champion_stats: dict[str, int] | None = Field(None, alias="championStats")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class EventDto(BaseModel):
    """Timeline event (kills, items, level ups, etc).

    Events have highly variable structures depending on type.
    We store the full event as-is since each type has different fields.
    Common fields are extracted here, the rest goes into the raw JSON.
    """

    type: str
    timestamp: int
    participant_id: int | None = Field(None, alias="participantId")

    # Optional fields that appear in various event types
    killer_id: int | None = Field(None, alias="killerId")
    victim_id: int | None = Field(None, alias="victimId")
    assisting_participant_ids: list[int] | None = Field(None, alias="assistingParticipantIds")
    item_id: int | None = Field(None, alias="itemId")
    skill_slot: int | None = Field(None, alias="skillSlot")
    level_up_type: str | None = Field(None, alias="levelUpType")
    creator_id: int | None = Field(None, alias="creatorId")
    ward_type: str | None = Field(None, alias="wardType")

    model_config = {"populate_by_name": True, "extra": "allow"}  # Allow extra fields


class FrameDto(BaseModel):
    """Single timeline frame (snapshot at a specific time).

    Contains participant stats and events that occurred during this frame interval.
    """

    timestamp: int
    participant_frames: dict[str, ParticipantFrameDto] = Field(..., alias="participantFrames")
    events: list[EventDto] = []

    model_config = {"populate_by_name": True, "extra": "ignore"}


class TimelineInfoDto(BaseModel):
    """Timeline info section containing frames and metadata."""

    frame_interval: int = Field(..., alias="frameInterval")  # Typically 60000 (1 minute)
    frames: list[FrameDto]
    game_id: int = Field(..., alias="gameId")
    participants: list[dict[str, object]] = []  # participantId to puuid mapping

    model_config = {"populate_by_name": True, "extra": "ignore"}


class TimelineMetadataDto(BaseModel):
    """Timeline metadata."""

    data_version: str = Field(..., alias="dataVersion")
    match_id: str = Field(..., alias="matchId")
    participants: list[str]  # List of PUUIDs

    model_config = {"populate_by_name": True}


class TimelineDto(BaseModel):
    """Complete timeline data from match-v5 timeline endpoint."""

    metadata: TimelineMetadataDto
    info: TimelineInfoDto

    model_config = {"populate_by_name": True}


# League/Rank DTOs


class MiniSeriesDto(BaseModel):
    """Mini-series progress information (for promotion series)."""

    losses: int
    progress: str  # Example: "WLNNN" (W=win, L=loss, N=not played)
    target: int  # Number of wins needed
    wins: int

    model_config = {"populate_by_name": True}


class LeagueEntryDto(BaseModel):
    """League entry information from league-v4 API.

    Contains player's rank information for a specific queue type.
    Note: Different endpoints return different identifiers:
    - /by-summoner/{summonerId} returns summonerId
    - /by-puuid/{puuid} returns puuid
    """

    league_id: str = Field(..., alias="leagueId")
    summoner_id: str | None = Field(None, alias="summonerId")
    puuid: str | None = None
    queue_type: str = Field(..., alias="queueType")  # RANKED_SOLO_5x5, RANKED_FLEX_SR, etc.
    # Tier: IRON, BRONZE, SILVER, GOLD, PLATINUM, EMERALD, DIAMOND, MASTER, GRANDMASTER, CHALLENGER
    tier: str
    rank: str  # I, II, III, IV (Roman numerals, not used in Master+)
    league_points: int = Field(..., alias="leaguePoints")
    wins: int
    losses: int
    veteran: bool = False
    inactive: bool = False
    fresh_blood: bool = Field(False, alias="freshBlood")
    hot_streak: bool = Field(False, alias="hotStreak")
    mini_series: MiniSeriesDto | None = Field(None, alias="miniSeries")

    model_config = {"populate_by_name": True}
