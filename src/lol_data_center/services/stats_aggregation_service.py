"""Service for aggregating player statistics."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import MatchParticipant
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


class StatsAggregationService:
    """Service for computing aggregated player statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the stats aggregation service.

        Args:
            session: Database session
        """
        self._session = session

    async def get_player_stats_by_role(
        self,
        puuid: str,
        role: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """Get aggregated stats for a player, optionally grouped by role.

        Args:
            puuid: Player PUUID
            role: Optional role filter (e.g., "MIDDLE", "JUNGLE")

        Returns:
            Dictionary mapping stat names to aggregations (avg, min, max, stddev)
        """
        # Build base query
        query = select(MatchParticipant).where(MatchParticipant.puuid == puuid)

        if role:
            query = query.where(MatchParticipant.individual_position == role)

        result = await self._session.execute(query)
        participants = list(result.scalars().all())

        if not participants:
            return {}

        # Define stats to aggregate
        stat_fields = [
            "kills",
            "deaths",
            "assists",
            "kda",
            "total_damage_dealt_to_champions",
            "total_minions_killed",
            "neutral_minions_killed",
            "vision_score",
            "gold_earned",
        ]

        stats: dict[str, dict[str, float]] = {}

        for stat_name in stat_fields:
            values = [getattr(p, stat_name) for p in participants]

            # Calculate aggregations
            count = len(values)
            avg = sum(values) / count if count > 0 else 0.0
            min_val = float(min(values)) if values else 0.0
            max_val = float(max(values)) if values else 0.0

            # Calculate standard deviation
            if count > 1:
                variance = sum((x - avg) ** 2 for x in values) / (count - 1)
                stddev = variance**0.5
            else:
                stddev = 0.0

            stats[stat_name] = {
                "avg": avg,
                "min": min_val,
                "max": max_val,
                "stddev": stddev,
                "count": float(count),
            }

        return stats

    async def get_player_stats_by_champion(
        self,
        puuid: str,
        champion_id: int | None = None,
    ) -> dict[str, dict[str, float]]:
        """Get aggregated stats for a player, optionally filtered by champion.

        Args:
            puuid: Player PUUID
            champion_id: Optional champion ID filter

        Returns:
            Dictionary mapping stat names to aggregations (avg, min, max, stddev)
        """
        # Build base query
        query = select(MatchParticipant).where(MatchParticipant.puuid == puuid)

        if champion_id:
            query = query.where(MatchParticipant.champion_id == champion_id)

        result = await self._session.execute(query)
        participants = list(result.scalars().all())

        if not participants:
            return {}

        # Define stats to aggregate
        stat_fields = [
            "kills",
            "deaths",
            "assists",
            "kda",
            "total_damage_dealt_to_champions",
            "total_minions_killed",
            "neutral_minions_killed",
            "vision_score",
            "gold_earned",
        ]

        stats: dict[str, dict[str, float]] = {}

        for stat_name in stat_fields:
            values = [getattr(p, stat_name) for p in participants]

            # Calculate aggregations
            count = len(values)
            avg = sum(values) / count if count > 0 else 0.0
            min_val = float(min(values)) if values else 0.0
            max_val = float(max(values)) if values else 0.0

            # Calculate standard deviation
            if count > 1:
                variance = sum((x - avg) ** 2 for x in values) / (count - 1)
                stddev = variance**0.5
            else:
                stddev = 0.0

            stats[stat_name] = {
                "avg": avg,
                "min": min_val,
                "max": max_val,
                "stddev": stddev,
                "count": float(count),
            }

        return stats

    async def get_all_roles_stats(
        self,
        puuid: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Get aggregated stats for a player grouped by all roles they've played.

        Args:
            puuid: Player PUUID

        Returns:
            Dictionary mapping role names to stat aggregations
        """
        # Get all unique roles for this player
        result = await self._session.execute(
            select(MatchParticipant.individual_position)
            .where(MatchParticipant.puuid == puuid)
            .distinct()
        )
        roles = [r[0] for r in result.fetchall() if r[0]]  # Filter out empty strings

        role_stats: dict[str, dict[str, dict[str, float]]] = {}
        for role in roles:
            role_stats[role] = await self.get_player_stats_by_role(puuid, role)

        return role_stats

    async def get_all_champions_stats(
        self,
        puuid: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Get aggregated stats for a player grouped by all champions they've played.

        Args:
            puuid: Player PUUID

        Returns:
            Dictionary mapping champion names to stat aggregations
        """
        # Get all unique champions for this player
        result = await self._session.execute(
            select(
                MatchParticipant.champion_id,
                MatchParticipant.champion_name,
            )
            .where(MatchParticipant.puuid == puuid)
            .distinct()
        )
        champions = result.fetchall()

        champion_stats: dict[str, dict[str, dict[str, float]]] = {}
        for champion_id, champion_name in champions:
            stats = await self.get_player_stats_by_champion(puuid, champion_id)
            champion_stats[champion_name] = stats

        return champion_stats

    async def get_nth_most_recent_game(
        self,
        puuid: str,
        n: int = 1,
    ) -> MatchParticipant | None:
        """Get the nth most recent game for a player.

        Args:
            puuid: Player PUUID
            n: Which game to retrieve (1 = most recent, 2 = second most recent, etc.)

        Returns:
            MatchParticipant record or None if not found
        """
        if n < 1:
            logger.warning("Invalid n value for nth_most_recent_game", n=n)
            return None

        result = await self._session.execute(
            select(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
            .order_by(MatchParticipant.game_creation.desc())
            .offset(n - 1)
            .limit(1)
        )
        return result.scalar_one_or_none()
