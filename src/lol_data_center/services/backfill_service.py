"""Backfill service for loading historical match data."""

from collections.abc import Callable

import sqlalchemy.exc
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Region, RiotApiClient
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.logging_config import get_logger
from lol_data_center.services.filters import is_allowed_queue
from lol_data_center.services.match_service import MatchService

logger = get_logger(__name__)


# Rate limit: 100 requests per 120 seconds = ~0.83 requests/sec
# Average time per match (with rate limiting): ~1.2 seconds
# This includes API calls for match details and timeline
SECONDS_PER_MATCH_ESTIMATE = 1.2


class BackfillService:
    """Service for backfilling historical match data without triggering events."""

    def __init__(
        self,
        session: AsyncSession,
        api_client: RiotApiClient | None = None,
    ) -> None:
        """Initialize the backfill service.

        Args:
            session: Database session
            api_client: Riot API client (creates new one if not provided)
        """
        self._session = session
        self._api_client = api_client
        self._match_service = MatchService(session)

    async def _get_client(self) -> RiotApiClient:
        """Get or create the API client."""
        if self._api_client is None:
            self._api_client = RiotApiClient()
        return self._api_client

    async def get_match_count_and_estimate(
        self,
        player: TrackedPlayer,
        region: Region = Region.EUROPE,
    ) -> tuple[int, int]:
        """Pre-fetch match IDs and estimate collection time.

        This method fetches all available match IDs for a player and estimates
        how long the full backfill process will take, based on rate limits.

        Args:
            player: The tracked player to estimate for
            region: Regional routing value

        Returns:
            Tuple of (total_matches, estimated_seconds)
        """
        client = await self._get_client()

        logger.info(
            "Pre-fetching match IDs for estimation",
            player_id=player.id,
            riot_id=player.riot_id,
            puuid=player.puuid,
        )

        # Fetch all match IDs
        match_ids = await client.fetch_all_match_ids(
            puuid=player.puuid,
            region=region,
        )

        total_matches = len(match_ids)

        # Estimate time based on rate limits and processing time
        # Each match requires 1-2 API calls (match details + timeline)
        estimated_seconds = int(total_matches * SECONDS_PER_MATCH_ESTIMATE)

        logger.info(
            "Match count and estimate calculated",
            player_id=player.id,
            total_matches=total_matches,
            estimated_seconds=estimated_seconds,
            estimated_minutes=estimated_seconds / 60,
        )

        return total_matches, estimated_seconds

    async def backfill_player_history(
        self,
        player: TrackedPlayer,
        region: Region = Region.EUROPE,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        """Backfill all historical matches for a player.

        This method fetches all available matches for the player and saves them
        to the database WITHOUT publishing NewMatchEvent. This prevents achievement
        evaluations and Discord notifications for historical data.

        Args:
            player: The tracked player to backfill
            region: Regional routing value
            progress_callback: Optional callback for progress updates (current, total)

        Returns:
            Number of new matches saved
        """
        client = await self._get_client()

        logger.info(
            "Starting backfill for player",
            player_id=player.id,
            riot_id=player.riot_id,
            puuid=player.puuid,
        )

        # Step 1: Fetch all match IDs
        match_ids = await client.fetch_all_match_ids(
            puuid=player.puuid,
            region=region,
        )

        total_matches = len(match_ids)
        logger.info(
            "Fetched match IDs",
            player_id=player.id,
            total_matches=total_matches,
        )

        if total_matches == 0:
            return 0

        # Step 2: Fetch and save each match (without events)
        saved_count = 0
        for i, match_id in enumerate(match_ids, 1):
            # Check if match already exists
            if await self._match_service.match_exists(match_id):
                logger.debug(
                    "Match already exists, loading from DB",
                    match_id=match_id,
                    progress=f"{i}/{total_matches}",
                )

                # Load match from database instead of querying Riot API
                match_data = await self._match_service.get_match_dto(match_id)

                if match_data is None:
                    logger.error(
                        "Match exists but failed to load from DB",
                        match_id=match_id,
                        progress=f"{i}/{total_matches}",
                    )
                    if progress_callback:
                        progress_callback(i, total_matches)
                    continue

                # Check for BOT participants
                if self._match_service.has_bot_participant(match_data):
                    logger.debug(
                        "Skipping match with BOT participant",
                        match_id=match_id,
                        progress=f"{i}/{total_matches}",
                    )
                    if progress_callback:
                        progress_callback(i, total_matches)
                    continue

                # Match already exists, just update progress
                if progress_callback:
                    progress_callback(i, total_matches)
                continue

            # Fetch full match data from Riot API
            logger.debug(
                "Fetching match details",
                match_id=match_id,
                progress=f"{i}/{total_matches}",
            )

            try:
                match_data = await client.get_match(match_id, region)

                # Filter: Only accept allowed queues
                if not is_allowed_queue(match_data.info.queue_id):
                    logger.debug(
                        "Skipping disallowed queue",
                        match_id=match_id,
                        queue_id=match_data.info.queue_id,
                        progress=f"{i}/{total_matches}",
                    )
                    continue

                # Filter: Skip matches with BOT participants
                if self._match_service.has_bot_participant(match_data):
                    logger.debug(
                        "Skipping match with BOT participant",
                        match_id=match_id,
                        progress=f"{i}/{total_matches}",
                    )
                    continue

                # Save match to database with timeline (only saves if doesn't exist)
                await self._match_service.save_match_with_timeline(
                    match_data, client, region, filter_events=True
                )
                saved_count += 1

                logger.debug(
                    "Saved match",
                    match_id=match_id,
                    progress=f"{i}/{total_matches}",
                )

            except Exception as e:
                logger.error(
                    "Failed to fetch/save match",
                    match_id=match_id,
                    error=str(e),
                    progress=f"{i}/{total_matches}",
                )
                # Only rollback if there's a database-related error that aborted the transaction
                if isinstance(e, sqlalchemy.exc.DBAPIError):
                    try:
                        await self._session.rollback()
                    except Exception as rollback_error:
                        logger.warning(
                            "Failed to rollback transaction",
                            error=str(rollback_error),
                        )
                # Continue with next match instead of failing entire backfill

            # Progress update
            if progress_callback:
                progress_callback(i, total_matches)

        logger.info(
            "Backfill complete",
            player_id=player.id,
            riot_id=player.riot_id,
            total_matches=total_matches,
            saved_matches=saved_count,
            skipped_matches=total_matches - saved_count,
        )

        return saved_count
