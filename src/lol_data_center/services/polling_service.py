"""Background polling service for fetching new matches."""

import asyncio
from contextlib import suppress

from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Region, RiotApiClient, RiotApiError
from lol_data_center.api_client.validation import ValidationError
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.events.event_bus import NewMatchEvent, get_event_bus
from lol_data_center.logging_config import get_logger
from lol_data_center.services.match_service import MatchService
from lol_data_center.services.player_service import PlayerService

logger = get_logger(__name__)


class PollingService:
    """Background service that polls for new matches for tracked players."""

    def __init__(
        self,
        api_client: RiotApiClient | None = None,
        polling_interval: int | None = None,
    ) -> None:
        """Initialize the polling service.

        Args:
            api_client: Riot API client (creates new one if not provided)
            polling_interval: Override polling interval in seconds
        """
        settings = get_settings()
        self._api_client = api_client or RiotApiClient()
        self._polling_interval = polling_interval or settings.polling_interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the polling service."""
        if self._running:
            logger.warning("Polling service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        logger.info(
            "Polling service started",
            polling_interval=self._polling_interval,
        )

    async def stop(self) -> None:
        """Stop the polling service."""
        self._running = False
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._api_client.close()
        logger.info("Polling service stopped")

    async def _polling_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_all_players()
            except Exception as e:
                logger.error(
                    "Error in polling loop",
                    error=str(e),
                    exc_info=True,
                )

            # Wait for next polling cycle
            if self._running:
                logger.debug(
                    "Waiting for next polling cycle",
                    seconds=self._polling_interval,
                )
                await asyncio.sleep(self._polling_interval)

    async def _poll_all_players(self) -> None:
        """Poll all active players for new matches."""
        async with get_async_session() as session:
            player_service = PlayerService(session, self._api_client)
            players = await player_service.get_all_active_players()

            if not players:
                logger.debug("No active players to poll")
                return

            logger.info(
                "Polling players for new matches",
                player_count=len(players),
            )

            for player in players:
                try:
                    await self._poll_player(player, session)
                except Exception as e:
                    logger.error(
                        "Error polling player",
                        player_id=player.id,
                        riot_id=player.riot_id,
                        error=str(e),
                        exc_info=True,
                    )

    async def _poll_player(
        self,
        player: TrackedPlayer,
        session: AsyncSession,
    ) -> None:
        """Poll a single player for new matches.

        Args:
            player: The player to poll
            session: Database session
        """
        region = Region(player.region)
        event_bus = get_event_bus()
        match_service = MatchService(session)
        player_service = PlayerService(session, self._api_client)

        logger.debug(
            "Polling player",
            player_id=player.id,
            riot_id=player.riot_id,
        )

        try:
            # Get recent match IDs
            match_ids = await self._api_client.get_match_ids(
                puuid=player.puuid,
                region=region,
                count=20,
            )
        except RiotApiError as e:
            logger.warning(
                "Failed to get match IDs",
                player_id=player.id,
                riot_id=player.riot_id,
                error=str(e),
            )
            return

        if not match_ids:
            logger.debug(
                "No matches found",
                player_id=player.id,
                riot_id=player.riot_id,
            )
            return

        # Find new matches (ones we haven't seen yet)
        new_match_count = 0

        for match_id in match_ids:
            # Stop if we've reached a match we've already processed
            if match_id == player.last_match_id:
                break

            # Check if match already exists in database
            match_data = None
            if await match_service.match_exists(match_id):
                logger.debug(
                    "Match exists, loading from DB",
                    match_id=match_id,
                    player_id=player.id,
                )

                # Load match from database instead of querying Riot API
                match_data = await match_service.get_match_dto(match_id)

                if match_data is None:
                    logger.error(
                        "Match exists but failed to load from DB",
                        match_id=match_id,
                        player_id=player.id,
                    )
                    continue

            try:
                # Fetch match details from Riot API if not loaded from DB
                if match_data is None:
                    match_data = await self._api_client.get_match(match_id, region)

                # Filter: process only CLASSIC game mode
                if match_data.info.game_mode != "CLASSIC":
                    logger.debug(
                        "Skipping non-CLASSIC game mode",
                        match_id=match_id,
                        game_mode=match_data.info.game_mode,
                    )
                    continue

                # Filter: Skip matches with BOT participants
                if match_service.has_bot_participant(match_data):
                    logger.debug(
                        "Skipping match with BOT participant",
                        match_id=match_id,
                        player_id=player.id,
                    )
                    continue

                # Save match to database (only saves if doesn't exist)
                await match_service.save_match(match_data)

                # Get participant data for this player
                participant = match_data.get_participant_by_puuid(player.puuid)
                if participant is None:
                    logger.warning(
                        "Player not found in match participants",
                        player_id=player.id,
                        match_id=match_id,
                    )
                    continue

                # Update player records
                await match_service.update_player_records(player, participant, match_id)

                # Publish new match event
                event = NewMatchEvent(
                    player_puuid=player.puuid,
                    player_name=player.riot_id,
                    match_id=match_id,
                    match_data=match_data,
                    participant_data=participant,
                )
                await event_bus.publish(event)

                new_match_count += 1

                logger.info(
                    "Processed new match",
                    player_id=player.id,
                    riot_id=player.riot_id,
                    match_id=match_id,
                    win=participant.win,
                    kda=f"{participant.kills}/{participant.deaths}/{participant.assists}",
                )

            except (RiotApiError, ValidationError) as e:
                logger.error(
                    "Failed to process match",
                    match_id=match_id,
                    player_id=player.id,
                    error=str(e),
                )
                continue

        # Update last polled timestamp
        if match_ids:
            await player_service.update_last_polled(player, match_ids[0])

        if new_match_count > 0:
            logger.info(
                "Finished polling player",
                player_id=player.id,
                riot_id=player.riot_id,
                new_matches=new_match_count,
            )

    async def poll_player_once(self, puuid: str) -> int:
        """Poll a specific player once (useful for testing or manual triggers).

        Args:
            puuid: Player PUUID

        Returns:
            Number of new matches found
        """
        async with get_async_session() as session:
            player_service = PlayerService(session, self._api_client)
            player = await player_service.get_player_by_puuid(puuid)

            if player is None:
                raise ValueError(f"Player not found: {puuid}")

            # Count events to return
            event_count = 0

            async def count_events(event: NewMatchEvent) -> None:
                nonlocal event_count
                event_count += 1

            event_bus = get_event_bus()
            event_bus.subscribe(NewMatchEvent, count_events)

            try:
                await self._poll_player(player, session)
            finally:
                event_bus.unsubscribe(NewMatchEvent, count_events)

            return event_count

    async def poll_all_players_once(self) -> None:
        """Poll all active players once (useful for manual triggers).

        This is a public method that can be used to trigger polling
        without starting the background service.
        """
        await self._poll_all_players()
