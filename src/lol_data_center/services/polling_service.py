"""Background polling service for fetching new matches."""

import asyncio
from contextlib import suppress

import aiohttp
import sqlalchemy.exc
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Region, RiotApiClient, RiotApiError
from lol_data_center.api_client.validation import ValidationError
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.events.event_bus import NewMatchEvent, get_event_bus
from lol_data_center.logging_config import get_logger
from lol_data_center.services.filters import is_allowed_queue
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

    async def _retry_with_backoff(
        self,
        coro_func,
        *args,
        max_retries: int = 3,
        base_delay: float = 1.0,
        **kwargs,
    ):
        """Retry a coroutine function with exponential backoff on network errors.

        Args:
            coro_func: Async function to retry
            *args: Positional arguments for coro_func
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            **kwargs: Keyword arguments for coro_func

        Returns:
            Result of coro_func if successful

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await coro_func(*args, **kwargs)
            except (
                aiohttp.ClientConnectorError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError,
            ) as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Network error, retrying",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                        retry_delay=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Network error after max retries",
                        error=str(e),
                        max_retries=max_retries,
                    )
            except RiotApiError:
                # Don't retry on API errors (rate limits, auth, etc.)
                raise

        raise last_exception

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
                    # Capture player info before potential session rollback
                    player_id = player.id if hasattr(player, 'id') else None
                    riot_id = player.riot_id if hasattr(player, 'riot_id') else None
                    
                    logger.error(
                        "Error polling player",
                        player_id=player_id,
                        riot_id=riot_id,
                        error=str(e),
                        exc_info=True,
                    )
                    # Only rollback if there's a database-related error that aborted the transaction
                    if isinstance(e, sqlalchemy.exc.DBAPIError):
                        try:
                            await session.rollback()
                        except Exception as rollback_error:
                            logger.warning(
                                "Failed to rollback transaction",
                                error=str(rollback_error),
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
            # Get recent match IDs, using last_polled_at as start_time filter
            start_time = None
            if player.last_polled_at is not None:
                # Convert datetime to epoch seconds for Riot API
                start_time = int(player.last_polled_at.timestamp())

            # Retry with exponential backoff on network errors
            match_ids = await self._retry_with_backoff(
                self._api_client.get_match_ids,
                puuid=player.puuid,
                region=region,
                count=20,
                start_time=start_time,
            )
        except RiotApiError as e:
            logger.warning(
                "Failed to get match IDs",
                player_id=player.id,
                riot_id=player.riot_id,
                error=str(e),
            )
            return
        except (
            aiohttp.ClientConnectorError,
            aiohttp.ClientOSError,
            asyncio.TimeoutError,
        ) as e:
            logger.warning(
                "Network error getting match IDs after retries",
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
            # Check if match already exists in database
            # If it does, skip it - it was already processed (e.g., during backfill)
            if await match_service.match_exists(match_id):
                logger.debug(
                    "Match already exists, skipping",
                    match_id=match_id,
                    player_id=player.id,
                )
                continue

            try:
                # Fetch match details from Riot API with retry logic
                match_data = await self._retry_with_backoff(
                    self._api_client.get_match,
                    match_id,
                    region,
                )

                # Filter: only process matches from allowed queues
                if not is_allowed_queue(match_data.info.queue_id):
                    logger.debug(
                        "Skipping disallowed queue",
                        match_id=match_id,
                        queue_id=match_data.info.queue_id,
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

                # Save match to database with timeline (only saves if doesn't exist)
                await match_service.save_match_with_timeline(
                    match_data, self._api_client, region, filter_events=True
                )

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
            except (
                aiohttp.ClientConnectorError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError,
            ) as e:
                logger.warning(
                    "Network error fetching match after retries",
                    match_id=match_id,
                    player_id=player.id,
                    error=str(e),
                )
                continue

        # Update last polled timestamp
        await player_service.update_last_polled(player)

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
