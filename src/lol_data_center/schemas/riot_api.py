"""Pydantic schemas for Riot API responses.

These schemas validate and type the JSON responses from the Riot API.
Fields are based on the official Riot API documentation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class AccountDto(BaseModel):
    """Riot Account information from account-v1 API."""

    puuid: str = Field(..., description="Player Universal Unique Identifier")
    game_name: str = Field(..., alias="gameName", description="Game name part of Riot ID")
    tag_line: str = Field(..., alias="tagLine", description="Tag line part of Riot ID")

    model_config = {"populate_by_name": True}


class SummonerDto(BaseModel):
    """Summoner information from summoner-v4 API."""

    account_id: str = Field(..., alias="accountId")
    profile_icon_id: int = Field(..., alias="profileIconId")
    revision_date: int = Field(..., alias="revisionDate")
    id: str = Field(..., description="Encrypted summoner ID")
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
    summoner_id: str = Field(..., alias="summonerId")
    riot_id_game_name: Optional[str] = Field(None, alias="riotIdGameName")
    riot_id_tagline: Optional[str] = Field(None, alias="riotIdTagline")
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
    game_end_timestamp: Optional[int] = Field(None, alias="gameEndTimestamp")
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
    tournament_code: Optional[str] = Field(None, alias="tournamentCode")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def game_creation_datetime(self) -> datetime:
        """Convert game creation timestamp to datetime."""
        return datetime.fromtimestamp(self.game_creation / 1000)

    @property
    def game_end_datetime(self) -> Optional[datetime]:
        """Convert game end timestamp to datetime."""
        if self.game_end_timestamp:
            return datetime.fromtimestamp(self.game_end_timestamp / 1000)
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

    def get_participant_by_puuid(self, puuid: str) -> Optional[ParticipantDto]:
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
