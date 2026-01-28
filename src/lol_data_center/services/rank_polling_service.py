"""Rank polling service for tracking player rank changes."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Platform, RiotApiClient, RiotApiError
from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import RankHistory, TrackedPlayer
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.riot_api import LeagueEntryDto
from lol_data_center.services.player_service import PlayerService

logger = get_logger(__name__)

# Default platform mapping (can be extended based on region)
REGION_TO_PLATFORM = {
    "americas": Platform.NA1,
    "asia": Platform.KR,
    "europe": Platform.EUW1,
    "sea": Platform.SG2,
}


class RankPollingService:
    """Background service that polls for rank changes for tracked players."""

    def __init__(
        self,
        api_client: RiotApiClient | None = None,
        polling_interval: int = 1800,  # 30 minutes in seconds
    ) -> None:
        """Initialize the rank polling service.

        Args:
            api_client: Riot API client (creates new one if not provided)
            polling_interval: Override polling interval in seconds (default 30 minutes)
        """
        self._api_client = api_client or RiotApiClient()
        self._polling_interval = polling_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the rank polling service."""
        if self._running:
            logger.warning("Rank polling service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        logger.info(
            "Rank polling service started",
            polling_interval=self._polling_interval,
        )

    async def stop(self) -> None:
        """Stop the rank polling service."""
        self._running = False
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Rank polling service stopped")

    async def _polling_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_all_players()
            except Exception as e:
                logger.error(
                    "Error in rank polling loop",
                    error=str(e),
                    exc_info=True,
                )

            # Wait for next polling cycle
            if self._running:
                logger.debug(
                    "Waiting for next rank polling cycle",
                    seconds=self._polling_interval,
                )
                await asyncio.sleep(self._polling_interval)

    async def _poll_all_players(self) -> None:
        """Poll all active players for rank changes."""
        async with get_async_session() as session:
            player_service = PlayerService(session, self._api_client)
            players = await player_service.get_all_active_players()

            if not players:
                logger.debug("No active players to poll for rank")
                return

            logger.info(
                "Polling players for rank changes",
                player_count=len(players),
            )

            for player in players:
                try:
                    await self._poll_player_rank(player, session)
                except Exception as e:
                    logger.error(
                        "Error polling player rank",
                        player_id=player.id,
                        riot_id=player.riot_id,
                        error=str(e),
                        exc_info=True,
                    )

    async def _poll_player_rank(
        self,
        player: TrackedPlayer,
        session: AsyncSession,
    ) -> None:
        """Poll a single player for rank changes.

        Args:
            player: The player to poll
            session: Database session
        """
        logger.debug(
            "Polling player rank",
            player_id=player.id,
            riot_id=player.riot_id,
        )

        # Get summoner data first to obtain summoner_id (needed for league endpoint)
        # If player doesn't have summoner_id, fetch it
        if not player.summoner_id:
            try:
                # Determine platform from region
                platform = REGION_TO_PLATFORM.get(player.region, Platform.EUW1)
                summoner = await self._api_client.get_summoner_by_puuid(player.puuid, platform)

                if summoner.id:
                    player.summoner_id = summoner.id
                    await session.commit()
                    logger.info(
                        "Updated player summoner_id",
                        player_id=player.id,
                        summoner_id=summoner.id,
                    )
                else:
                    logger.warning(
                        "Summoner ID not available from API",
                        player_id=player.id,
                        riot_id=player.riot_id,
                    )
                    return
            except RiotApiError as e:
                logger.warning(
                    "Failed to get summoner data",
                    player_id=player.id,
                    riot_id=player.riot_id,
                    error=str(e),
                )
                return

        # Now get league entries
        try:
            platform = REGION_TO_PLATFORM.get(player.region, Platform.EUW1)
            league_entries = await self._api_client.get_summoner_league(
                player.summoner_id, platform
            )
        except RiotApiError as e:
            logger.warning(
                "Failed to get league entries",
                player_id=player.id,
                riot_id=player.riot_id,
                error=str(e),
            )
            return

        if not league_entries:
            logger.debug(
                "No ranked data found for player",
                player_id=player.id,
                riot_id=player.riot_id,
            )
            return

        # Process each queue type (RANKED_SOLO_5x5, RANKED_FLEX_SR, etc.)
        for entry in league_entries:
            await self._save_rank_if_changed(player, entry, session)

    async def _save_rank_if_changed(
        self,
        player: TrackedPlayer,
        league_entry: LeagueEntryDto,
        session: AsyncSession,
    ) -> None:
        """Save rank data if it has changed since last record.

        Args:
            player: The player
            league_entry: League entry DTO from API
            session: Database session
        """
        # Get the most recent rank entry for this player and queue
        result = await session.execute(
            select(RankHistory)
            .where(
                RankHistory.player_id == player.id,
                RankHistory.queue_type == league_entry.queue_type,
            )
            .order_by(RankHistory.recorded_at.desc())
            .limit(1)
        )
        last_rank = result.scalar_one_or_none()

        # Check if rank has changed
        rank_changed = False
        if last_rank is None:
            rank_changed = True  # First time tracking this queue
        else:
            # Check if any rank component changed
            if (
                last_rank.tier != league_entry.tier
                or last_rank.rank != league_entry.rank
                or last_rank.league_points != league_entry.league_points
            ):
                rank_changed = True

        if not rank_changed:
            logger.debug(
                "No rank change detected",
                player_id=player.id,
                queue_type=league_entry.queue_type,
            )
            return

        # Create new rank history entry
        new_rank = RankHistory(
            player_id=player.id,
            queue_type=league_entry.queue_type,
            tier=league_entry.tier,
            rank=league_entry.rank,
            league_points=league_entry.league_points,
            wins=league_entry.wins,
            losses=league_entry.losses,
            league_id=league_entry.league_id,
            veteran=league_entry.veteran,
            inactive=league_entry.inactive,
            fresh_blood=league_entry.fresh_blood,
            hot_streak=league_entry.hot_streak,
            recorded_at=datetime.now(UTC),
        )

        session.add(new_rank)
        await session.commit()

        logger.info(
            "Rank change detected and saved",
            player_id=player.id,
            riot_id=player.riot_id,
            queue_type=league_entry.queue_type,
            tier=league_entry.tier,
            rank=league_entry.rank,
            lp=league_entry.league_points,
        )
