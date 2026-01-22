"""SQLAlchemy ORM models for League of Legends data."""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class JSONType(TypeDecorator[Any]):
    """Cross-database JSON type using Text for SQLite and JSON for PostgreSQL."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Use JSON type for PostgreSQL, Text for others (SQLite)."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Convert Python object to JSON string for SQLite."""
        if value is None:
            return None
        if dialect.name != "postgresql":
            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Convert JSON string back to Python object for SQLite."""
        if value is None:
            return None
        if dialect.name != "postgresql":
            return json.loads(value)
        return value


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TrackedPlayer(Base):
    """Players whose matches are being tracked."""

    __tablename__ = "tracked_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    puuid: Mapped[str] = mapped_column(String(78), unique=True, nullable=False, index=True)
    game_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(10), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    summoner_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_icon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summoner_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    polling_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    participations: Mapped[list["MatchParticipant"]] = relationship(
        "MatchParticipant", back_populates="player"
    )
    records: Mapped[Optional["PlayerRecord"]] = relationship(
        "PlayerRecord", back_populates="player", uselist=False
    )

    @property
    def riot_id(self) -> str:
        """Get the full Riot ID (GameName#TagLine)."""
        return f"{self.game_name}#{self.tag_line}"

    def __repr__(self) -> str:
        return f"<TrackedPlayer(id={self.id}, riot_id={self.riot_id}, region={self.region})>"


class Champion(Base):
    """Champion static data mapping."""

    __tablename__ = "champions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    champion_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(50), nullable=False)  # Internal name
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Champion(id={self.champion_id}, name={self.name})>"


class Match(Base):
    """League of Legends match data."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    data_version: Mapped[str] = mapped_column(String(10), nullable=False)
    game_creation: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    game_duration: Mapped[int] = mapped_column(Integer, nullable=False)  # seconds
    game_end_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    game_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    game_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    game_version: Mapped[str] = mapped_column(String(50), nullable=False)
    map_id: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_id: Mapped[str] = mapped_column(String(10), nullable=False)
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tournament_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timeline_data: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    participants: Mapped[list["MatchParticipant"]] = relationship(
        "MatchParticipant", back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, match_id={self.match_id}, mode={self.game_mode})>"


class MatchParticipant(Base):
    """Participant stats for a match."""

    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "puuid", name="uq_match_participant"),
        Index("ix_participant_puuid_game_creation", "puuid", "game_creation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_db_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    puuid: Mapped[str] = mapped_column(String(78), nullable=False, index=True)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tracked_players.id", ondelete="SET NULL"), nullable=True
    )
    game_creation: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Player info
    summoner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    summoner_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    riot_id_game_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    riot_id_tagline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    profile_icon: Mapped[int] = mapped_column(Integer, nullable=False)
    summoner_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Champion & Role
    champion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    champion_name: Mapped[str] = mapped_column(String(50), nullable=False)
    champion_level: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 100 = blue, 200 = red
    team_position: Mapped[str] = mapped_column(String(20), nullable=False)
    individual_position: Mapped[str] = mapped_column(String(20), nullable=False)
    lane: Mapped[str] = mapped_column(String(20), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Core Stats
    kills: Mapped[int] = mapped_column(Integer, nullable=False)
    deaths: Mapped[int] = mapped_column(Integer, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, nullable=False)
    kda: Mapped[float] = mapped_column(Float, nullable=False)  # Calculated (K+A)/D

    # Combat Stats
    total_damage_dealt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_damage_dealt_to_champions: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_damage_taken: Mapped[int] = mapped_column(BigInteger, nullable=False)
    damage_self_mitigated: Mapped[int] = mapped_column(BigInteger, nullable=False)
    largest_killing_spree: Mapped[int] = mapped_column(Integer, nullable=False)
    largest_multi_kill: Mapped[int] = mapped_column(Integer, nullable=False)
    killing_sprees: Mapped[int] = mapped_column(Integer, nullable=False)
    double_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    triple_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    quadra_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    penta_kills: Mapped[int] = mapped_column(Integer, nullable=False)

    # Economy
    gold_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    gold_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minions_killed: Mapped[int] = mapped_column(Integer, nullable=False)
    neutral_minions_killed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vision
    vision_score: Mapped[int] = mapped_column(Integer, nullable=False)
    wards_placed: Mapped[int] = mapped_column(Integer, nullable=False)
    wards_killed: Mapped[int] = mapped_column(Integer, nullable=False)
    vision_wards_bought_in_game: Mapped[int] = mapped_column(Integer, nullable=False)

    # Objectives
    turret_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    turret_takedowns: Mapped[int] = mapped_column(Integer, nullable=False)
    inhibitor_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    inhibitor_takedowns: Mapped[int] = mapped_column(Integer, nullable=False)
    baron_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    dragon_kills: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_stolen: Mapped[int] = mapped_column(Integer, nullable=False)

    # Utility
    total_heal: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_heals_on_teammates: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_damage_shielded_on_teammates: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_time_cc_dealt: Mapped[int] = mapped_column(Integer, nullable=False)
    time_ccing_others: Mapped[int] = mapped_column(Integer, nullable=False)

    # Game State
    win: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_blood_kill: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_blood_assist: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_tower_kill: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_tower_assist: Mapped[bool] = mapped_column(Boolean, nullable=False)
    game_ended_in_surrender: Mapped[bool] = mapped_column(Boolean, nullable=False)
    game_ended_in_early_surrender: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_played: Mapped[int] = mapped_column(Integer, nullable=False)  # seconds

    # Items (at game end)
    item0: Mapped[int] = mapped_column(Integer, nullable=False)
    item1: Mapped[int] = mapped_column(Integer, nullable=False)
    item2: Mapped[int] = mapped_column(Integer, nullable=False)
    item3: Mapped[int] = mapped_column(Integer, nullable=False)
    item4: Mapped[int] = mapped_column(Integer, nullable=False)
    item5: Mapped[int] = mapped_column(Integer, nullable=False)
    item6: Mapped[int] = mapped_column(Integer, nullable=False)  # Trinket

    # Spells & Runes
    summoner1_id: Mapped[int] = mapped_column(Integer, nullable=False)
    summoner2_id: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="participants")
    player: Mapped[Optional["TrackedPlayer"]] = relationship(
        "TrackedPlayer", back_populates="participations"
    )

    def __repr__(self) -> str:
        return (
            f"<MatchParticipant(match_id={self.match_id}, "
            f"champion={self.champion_name}, kda={self.kills}/{self.deaths}/{self.assists})>"
        )


class PlayerRecord(Base):
    """Personal records for tracked players."""

    __tablename__ = "player_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracked_players.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Maximum records
    max_kills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_kills_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_deaths: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_deaths_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_assists_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_kda: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_kda_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_cs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_cs_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_damage_to_champions: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    max_damage_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_vision_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_vision_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_gold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_gold_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Minimum records (for stats where lower is better, excluding 0 deaths)
    min_deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_deaths_match_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Game counts
    total_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    player: Mapped["TrackedPlayer"] = relationship("TrackedPlayer", back_populates="records")

    def __repr__(self) -> str:
        return f"<PlayerRecord(player_id={self.player_id}, games={self.total_games})>"


class InvalidApiResponse(Base):
    """Storage for invalid API responses for debugging."""

    __tablename__ = "invalid_api_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<InvalidApiResponse(id={self.id}, endpoint={self.endpoint})>"
