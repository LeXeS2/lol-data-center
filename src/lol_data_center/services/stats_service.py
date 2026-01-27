"""Player statistics service for Discord commands."""

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import Match, MatchParticipant
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

# Ranked queue IDs
RANKED_SOLO_QUEUE_ID = 420  # Ranked Solo/Duo
RANKED_FLEX_QUEUE_ID = 440  # Ranked Flex


class PlayerStats:
    """Player statistics for current season."""

    def __init__(
        self,
        total_games: int,
        total_wins: int,
        win_rate: float,
        top_champions: list[tuple[str, int]],
    ) -> None:
        """Initialize player stats.

        Args:
            total_games: Total number of ranked games played
            total_wins: Total number of wins
            win_rate: Win rate as a percentage (0-100)
            top_champions: List of (champion_name, games_played) tuples
        """
        self.total_games = total_games
        self.total_wins = total_wins
        self.win_rate = win_rate
        self.top_champions = top_champions


class StatsService:
    """Service for generating player statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the stats service.

        Args:
            session: Database session
        """
        self._session = session

    def get_current_season(self) -> int:
        """Get the current season number based on the year.

        Returns:
            Current season number (e.g., 16 for 2026)
        """
        current_year = datetime.now(UTC).year
        # Season calculation: season = year - 2010
        # Examples: 2025 → Season 15, 2026 → Season 16
        return current_year - 2010

    async def get_player_stats(self, puuid: str) -> PlayerStats:
        """Get player statistics for the current season.

        Args:
            puuid: Player's PUUID

        Returns:
            PlayerStats object containing statistics

        Raises:
            ValueError: If player has no ranked games
        """
        current_season = self.get_current_season()
        season_prefix = f"{current_season}."

        # Query for ranked games in the current season
        query = (
            select(MatchParticipant, Match)
            .join(Match, MatchParticipant.match_id == Match.match_id)
            .where(
                MatchParticipant.puuid == puuid,
                Match.queue_id.in_([RANKED_SOLO_QUEUE_ID, RANKED_FLEX_QUEUE_ID]),
                Match.game_version.like(f"{season_prefix}%"),
            )
        )

        result = await self._session.execute(query)
        matches = result.all()

        if not matches:
            raise ValueError("No ranked games found for current season")

        # Calculate statistics
        total_games = len(matches)
        total_wins = sum(1 for participant, _ in matches if participant.win)
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

        # Count champion picks
        champion_counter: Counter[str] = Counter()
        for participant, _ in matches:
            champion_counter[participant.champion_name] += 1

        # Get top 3 champions
        top_champions = champion_counter.most_common(3)

        logger.info(
            "Generated player stats",
            puuid=puuid,
            total_games=total_games,
            win_rate=win_rate,
            top_champions_count=len(top_champions),
        )

        return PlayerStats(
            total_games=total_games,
            total_wins=total_wins,
            win_rate=win_rate,
            top_champions=top_champions,
        )
