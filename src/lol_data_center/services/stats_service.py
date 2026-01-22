"""Statistics aggregation service for player performance data."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import MatchParticipant
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedStats:
    """Aggregated statistics for a set of matches.

    Attributes:
        group_key: The grouping identifier (e.g., champion name or role)
        game_count: Number of games in the aggregation
        avg_kills: Average kills
        avg_deaths: Average deaths
        avg_assists: Average assists
        avg_kda: Average KDA
        avg_cs: Average CS (total minions killed)
        avg_gold: Average gold earned
        avg_damage: Average damage to champions
        avg_vision_score: Average vision score
        max_kills: Maximum kills in a single game
        max_deaths: Maximum deaths in a single game
        max_assists: Maximum assists in a single game
        max_kda: Maximum KDA in a single game
        max_cs: Maximum CS in a single game
        max_gold: Maximum gold in a single game
        max_damage: Maximum damage to champions in a single game
        max_vision_score: Maximum vision score in a single game
        min_kills: Minimum kills in a single game
        min_deaths: Minimum deaths in a single game
        min_assists: Minimum assists in a single game
        min_kda: Minimum KDA in a single game
        min_cs: Minimum CS in a single game
        min_gold: Minimum gold in a single game
        min_damage: Minimum damage to champions in a single game
        min_vision_score: Minimum vision score in a single game
        stddev_kills: Standard deviation of kills
        stddev_deaths: Standard deviation of deaths
        stddev_assists: Standard deviation of assists
        stddev_kda: Standard deviation of KDA
        stddev_cs: Standard deviation of CS
        stddev_gold: Standard deviation of gold
        stddev_damage: Standard deviation of damage
        stddev_vision_score: Standard deviation of vision score
        win_rate: Win rate percentage (0-100)
    """

    group_key: str
    game_count: int
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_kda: float
    avg_cs: float
    avg_gold: float
    avg_damage: float
    avg_vision_score: float
    max_kills: int
    max_deaths: int
    max_assists: int
    max_kda: float
    max_cs: int
    max_gold: int
    max_damage: int
    max_vision_score: int
    min_kills: int
    min_deaths: int
    min_assists: int
    min_kda: float
    min_cs: int
    min_gold: int
    min_damage: int
    min_vision_score: int
    stddev_kills: float
    stddev_deaths: float
    stddev_assists: float
    stddev_kda: float
    stddev_cs: float
    stddev_gold: float
    stddev_damage: float
    stddev_vision_score: float
    win_rate: float


class StatsService:
    """Service for aggregating and retrieving player statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the stats service.

        Args:
            session: Database session
        """
        self._session = session

    async def get_stats_by_champion(
        self,
        puuid: str,
        min_games: int = 1,
    ) -> list[AggregatedStats]:
        """Get aggregated statistics grouped by champion for a player.

        Args:
            puuid: Player PUUID
            min_games: Minimum number of games required to include a champion (default: 1)

        Returns:
            List of AggregatedStats, one per champion (sorted by game count desc)
        """
        # Query to get all match participations and aggregate by champion
        result = await self._session.execute(
            select(MatchParticipant).where(MatchParticipant.puuid == puuid)
        )
        matches = list(result.scalars().all())

        # Group by champion name
        champion_groups: dict[str, list[MatchParticipant]] = {}
        for match in matches:
            champion_name = match.champion_name
            if champion_name not in champion_groups:
                champion_groups[champion_name] = []
            champion_groups[champion_name].append(match)

        # Calculate aggregated stats for each champion
        aggregated_stats: list[AggregatedStats] = []
        for champion_name, champion_matches in champion_groups.items():
            if len(champion_matches) < min_games:
                continue

            stats = self._calculate_aggregated_stats(champion_name, champion_matches)
            aggregated_stats.append(stats)

        # Sort by game count (descending)
        aggregated_stats.sort(key=lambda x: x.game_count, reverse=True)

        logger.info(
            "Retrieved stats by champion",
            puuid=puuid,
            champion_count=len(aggregated_stats),
            total_matches=len(matches),
        )

        return aggregated_stats

    async def get_stats_by_role(
        self,
        puuid: str,
        min_games: int = 1,
    ) -> list[AggregatedStats]:
        """Get aggregated statistics grouped by role for a player.

        Args:
            puuid: Player PUUID
            min_games: Minimum number of games required to include a role (default: 1)

        Returns:
            List of AggregatedStats, one per role (sorted by game count desc)
        """
        # Query to get all match participations and aggregate by role
        result = await self._session.execute(
            select(MatchParticipant).where(MatchParticipant.puuid == puuid)
        )
        matches = list(result.scalars().all())

        # Group by individual_position (role)
        role_groups: dict[str, list[MatchParticipant]] = {}
        for match in matches:
            role = match.individual_position
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(match)

        # Calculate aggregated stats for each role
        aggregated_stats: list[AggregatedStats] = []
        for role, role_matches in role_groups.items():
            if len(role_matches) < min_games:
                continue

            stats = self._calculate_aggregated_stats(role, role_matches)
            aggregated_stats.append(stats)

        # Sort by game count (descending)
        aggregated_stats.sort(key=lambda x: x.game_count, reverse=True)

        logger.info(
            "Retrieved stats by role",
            puuid=puuid,
            role_count=len(aggregated_stats),
            total_matches=len(matches),
        )

        return aggregated_stats

    async def get_nth_recent_game(
        self,
        puuid: str,
        n: int = 1,
    ) -> MatchParticipant | None:
        """Get the n-th most recent game for a player.

        Args:
            puuid: Player PUUID
            n: Game index (1 = most recent, 2 = second most recent, etc.)

        Returns:
            MatchParticipant if found, None if index out of bounds
        """
        if n < 1:
            logger.warning("Invalid game index", n=n)
            return None

        # Query for n-th most recent game
        result = await self._session.execute(
            select(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
            .order_by(desc(MatchParticipant.game_creation))
            .limit(1)
            .offset(n - 1)
        )

        game = result.scalar_one_or_none()

        if game:
            logger.info(
                "Retrieved nth recent game",
                puuid=puuid,
                n=n,
                match_id=game.match_id,
            )
        else:
            logger.info("No game found at index", puuid=puuid, n=n)

        return game

    def _calculate_aggregated_stats(
        self,
        group_key: str,
        matches: list[MatchParticipant],
    ) -> AggregatedStats:
        """Calculate aggregated statistics from a list of match participations.

        Args:
            group_key: The grouping identifier (champion name or role)
            matches: List of match participations to aggregate

        Returns:
            AggregatedStats with calculated values
        """
        if not matches:
            # Return zero stats for empty list
            return AggregatedStats(
                group_key=group_key,
                game_count=0,
                avg_kills=0.0,
                avg_deaths=0.0,
                avg_assists=0.0,
                avg_kda=0.0,
                avg_cs=0.0,
                avg_gold=0.0,
                avg_damage=0.0,
                avg_vision_score=0.0,
                max_kills=0,
                max_deaths=0,
                max_assists=0,
                max_kda=0.0,
                max_cs=0,
                max_gold=0,
                max_damage=0,
                max_vision_score=0,
                min_kills=0,
                min_deaths=0,
                min_assists=0,
                min_kda=0.0,
                min_cs=0,
                min_gold=0,
                min_damage=0,
                min_vision_score=0,
                stddev_kills=0.0,
                stddev_deaths=0.0,
                stddev_assists=0.0,
                stddev_kda=0.0,
                stddev_cs=0.0,
                stddev_gold=0.0,
                stddev_damage=0.0,
                stddev_vision_score=0.0,
                win_rate=0.0,
            )

        # Extract values
        kills = [m.kills for m in matches]
        deaths = [m.deaths for m in matches]
        assists = [m.assists for m in matches]
        kdas = [m.kda for m in matches]
        cs = [m.total_minions_killed for m in matches]
        gold = [m.gold_earned for m in matches]
        damage = [m.total_damage_dealt_to_champions for m in matches]
        vision_scores = [m.vision_score for m in matches]
        wins = sum(1 for m in matches if m.win)

        game_count = len(matches)

        # Calculate averages
        avg_kills = sum(kills) / game_count
        avg_deaths = sum(deaths) / game_count
        avg_assists = sum(assists) / game_count
        avg_kda = sum(kdas) / game_count
        avg_cs = sum(cs) / game_count
        avg_gold = sum(gold) / game_count
        avg_damage = sum(damage) / game_count
        avg_vision_score = sum(vision_scores) / game_count

        # Calculate standard deviations
        stddev_kills = self._calculate_stddev(kills, avg_kills)
        stddev_deaths = self._calculate_stddev(deaths, avg_deaths)
        stddev_assists = self._calculate_stddev(assists, avg_assists)
        stddev_kda = self._calculate_stddev(kdas, avg_kda)
        stddev_cs = self._calculate_stddev(cs, avg_cs)
        stddev_gold = self._calculate_stddev(gold, avg_gold)
        stddev_damage = self._calculate_stddev(damage, avg_damage)
        stddev_vision_score = self._calculate_stddev(vision_scores, avg_vision_score)

        # Calculate win rate
        win_rate = (wins / game_count) * 100 if game_count > 0 else 0.0

        return AggregatedStats(
            group_key=group_key,
            game_count=game_count,
            avg_kills=avg_kills,
            avg_deaths=avg_deaths,
            avg_assists=avg_assists,
            avg_kda=avg_kda,
            avg_cs=avg_cs,
            avg_gold=avg_gold,
            avg_damage=avg_damage,
            avg_vision_score=avg_vision_score,
            max_kills=max(kills),
            max_deaths=max(deaths),
            max_assists=max(assists),
            max_kda=max(kdas),
            max_cs=max(cs),
            max_gold=max(gold),
            max_damage=max(damage),
            max_vision_score=max(vision_scores),
            min_kills=min(kills),
            min_deaths=min(deaths),
            min_assists=min(assists),
            min_kda=min(kdas),
            min_cs=min(cs),
            min_gold=min(gold),
            min_damage=min(damage),
            min_vision_score=min(vision_scores),
            stddev_kills=stddev_kills,
            stddev_deaths=stddev_deaths,
            stddev_assists=stddev_assists,
            stddev_kda=stddev_kda,
            stddev_cs=stddev_cs,
            stddev_gold=stddev_gold,
            stddev_damage=stddev_damage,
            stddev_vision_score=stddev_vision_score,
            win_rate=win_rate,
        )

    def _calculate_stddev(self, values: Sequence[int | float], mean: float) -> float:
        """Calculate sample standard deviation.

        Sample standard deviation uses Bessel's correction (dividing by n-1 instead of n)
        to provide an unbiased estimate. This is undefined for n<2, so we return 0.0 in
        those cases.

        Args:
            values: Sequence of values
            mean: Pre-calculated mean

        Returns:
            Standard deviation, or 0.0 if fewer than 2 values (undefined)
        """
        if len(values) < 2:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return float(variance**0.5)
