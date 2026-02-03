"""Data extraction service for ML model training."""

from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import Match, MatchParticipant
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

# Ranked queue IDs
RANKED_SOLO_QUEUE_ID = 420  # Ranked Solo/Duo
RANKED_FLEX_QUEUE_ID = 440  # Ranked Flex


class MatchDataExtractor:
    """Service for extracting match data for ML training."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the data extractor.

        Args:
            session: Database session
        """
        self._session = session

    async def extract_match_features(
        self,
        queue_ids: list[int] | None = None,
        min_game_duration: int = 300,  # 5 minutes
    ) -> pd.DataFrame:
        """Extract match participant features for ML training.

        Args:
            queue_ids: List of queue IDs to filter (default: ranked queues)
            min_game_duration: Minimum game duration in seconds to include

        Returns:
            DataFrame with participant features and win outcome
        """
        if queue_ids is None:
            queue_ids = [RANKED_SOLO_QUEUE_ID, RANKED_FLEX_QUEUE_ID]

        logger.info(
            "Extracting match features",
            queue_ids=queue_ids,
            min_game_duration=min_game_duration,
        )

        # Query for match participants with their match data
        query = (
            select(MatchParticipant, Match)
            .join(Match, MatchParticipant.match_id == Match.match_id)
            .where(
                Match.queue_id.in_(queue_ids),
                Match.game_duration >= min_game_duration,
            )
        )

        result = await self._session.execute(query)
        matches = result.all()

        if not matches:
            logger.warning("No matches found for the given criteria")
            return pd.DataFrame()

        logger.info("Extracting features from matches", count=len(matches))

        # Extract features from each participant
        records: list[dict[str, Any]] = []
        for participant, match in matches:
            record = self._extract_participant_features(participant, match)
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(
            "Feature extraction complete",
            total_records=len(df),
            features=len(df.columns),
        )

        return df

    def _extract_participant_features(
        self, participant: MatchParticipant, match: Match
    ) -> dict[str, Any]:
        """Extract features from a single participant.

        Args:
            participant: MatchParticipant instance
            match: Match instance

        Returns:
            Dictionary of features
        """
        # Calculate per-minute statistics (normalized by game duration)
        game_duration_minutes = match.game_duration / 60.0

        # Core features
        features: dict[str, Any] = {
            # Identifiers for tracking
            "match_id": participant.match_id,
            "puuid": participant.puuid,
            "champion_id": participant.champion_id,
            "champion_name": participant.champion_name,
            "team_position": participant.team_position,
            "individual_position": participant.individual_position,
            # Target variable
            "win": participant.win,
            # KDA features
            "kills": participant.kills,
            "deaths": participant.deaths,
            "assists": participant.assists,
            "kda": participant.kda,
            # Combat features (per minute)
            "damage_per_min": participant.total_damage_dealt_to_champions / game_duration_minutes,
            "damage_taken_per_min": participant.total_damage_taken / game_duration_minutes,
            "damage_mitigated_per_min": participant.damage_self_mitigated / game_duration_minutes,
            # Economy (per minute)
            "gold_per_min": participant.gold_earned / game_duration_minutes,
            "cs_per_min": (participant.total_minions_killed + participant.neutral_minions_killed)
            / game_duration_minutes,
            # Vision
            "vision_score": participant.vision_score,
            "vision_score_per_min": participant.vision_score / game_duration_minutes,
            "wards_placed": participant.wards_placed,
            "wards_killed": participant.wards_killed,
            # Objectives
            "turret_takedowns": participant.turret_takedowns,
            "inhibitor_takedowns": participant.inhibitor_takedowns,
            "baron_kills": participant.baron_kills,
            "dragon_kills": participant.dragon_kills,
            # Utility
            "heal_per_min": participant.total_heal / game_duration_minutes,
            "heals_on_teammates_per_min": participant.total_heals_on_teammates
            / game_duration_minutes,
            "shield_on_teammates_per_min": participant.total_damage_shielded_on_teammates
            / game_duration_minutes,
            "cc_time_dealt": participant.total_time_cc_dealt,
            # Multi-kills
            "double_kills": participant.double_kills,
            "triple_kills": participant.triple_kills,
            "quadra_kills": participant.quadra_kills,
            "penta_kills": participant.penta_kills,
            # Early game indicators
            "first_blood_kill": participant.first_blood_kill,
            "first_tower_kill": participant.first_tower_kill,
            # Game context
            "game_duration_minutes": game_duration_minutes,
            "champion_level": participant.champion_level,
        }

        return features

    async def get_champion_stats(self) -> pd.DataFrame:
        """Get aggregate statistics per champion for context.

        Returns:
            DataFrame with champion-level statistics
        """
        query = select(MatchParticipant)

        result = await self._session.execute(query)
        participants = result.scalars().all()

        if not participants:
            return pd.DataFrame()

        # Group by champion
        champion_data: dict[str, list[float]] = {}
        for p in participants:
            if p.champion_name not in champion_data:
                champion_data[p.champion_name] = []

            champion_data[p.champion_name].append(float(p.win))

        # Calculate win rates
        stats = []
        for champion, wins in champion_data.items():
            stats.append(
                {
                    "champion_name": champion,
                    "total_games": len(wins),
                    "win_rate": sum(wins) / len(wins) if wins else 0.0,
                }
            )

        return pd.DataFrame(stats)

    async def get_role_stats(self) -> pd.DataFrame:
        """Get aggregate statistics per role for context.

        Returns:
            DataFrame with role-level statistics
        """
        query = select(MatchParticipant)

        result = await self._session.execute(query)
        participants = result.scalars().all()

        if not participants:
            return pd.DataFrame()

        # Group by position
        role_data: dict[str, list[float]] = {}
        for p in participants:
            position = p.team_position or p.individual_position
            if position not in role_data:
                role_data[position] = []

            role_data[position].append(float(p.win))

        # Calculate win rates
        stats = []
        for role, wins in role_data.items():
            stats.append(
                {
                    "role": role,
                    "total_games": len(wins),
                    "win_rate": sum(wins) / len(wins) if wins else 0.0,
                }
            )

        return pd.DataFrame(stats)
