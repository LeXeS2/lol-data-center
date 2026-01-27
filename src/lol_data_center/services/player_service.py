"""Player/Summoner management service."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Platform, Region, RiotApiClient
from lol_data_center.database.models import PlayerRecord, TrackedPlayer
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


class PlayerService:
    """Service for managing tracked players."""

    def __init__(
        self,
        session: AsyncSession,
        api_client: RiotApiClient | None = None,
    ) -> None:
        """Initialize the player service.

        Args:
            session: Database session
            api_client: Riot API client (creates new one if not provided)
        """
        self._session = session
        self._api_client = api_client

    async def _get_client(self) -> RiotApiClient:
        """Get or create the API client."""
        if self._api_client is None:
            self._api_client = RiotApiClient()
        return self._api_client

    async def add_player(
        self,
        game_name: str,
        tag_line: str,
        region: Region = Region.EUROPE,
        platform: Platform = Platform.EUW1,
    ) -> TrackedPlayer:
        """Add a new player to track.

        Args:
            game_name: Game name part of Riot ID
            tag_line: Tag line part of Riot ID
            region: Regional routing value
            platform: Platform routing value

        Returns:
            The created TrackedPlayer

        Raises:
            ValueError: If player already exists
        """
        client = await self._get_client()

        # Check if player already exists
        existing = await self.get_player_by_riot_id(game_name, tag_line)
        if existing:
            raise ValueError(f"Player {game_name}#{tag_line} is already tracked")

        # Get account info from Riot API
        logger.info(
            "Fetching account info",
            game_name=game_name,
            tag_line=tag_line,
            region=region.value,
        )
        account = await client.get_account_by_riot_id(game_name, tag_line, region)

        # Get summoner info
        logger.info(
            "Fetching summoner info",
            puuid=account.puuid,
            platform=platform.value,
        )
        summoner = await client.get_summoner_by_puuid(account.puuid, platform)

        # Create tracked player
        player = TrackedPlayer(
            puuid=account.puuid,
            game_name=account.game_name,
            tag_line=account.tag_line,
            region=region.value,
            summoner_id=summoner.id,  # May be None if API no longer provides it
            account_id=summoner.account_id,  # May be None if API no longer provides it
            profile_icon_id=summoner.profile_icon_id,
            summoner_level=summoner.summoner_level,
            polling_enabled=False,
        )

        self._session.add(player)
        await self._session.flush()

        # Create empty player records
        records = PlayerRecord(player_id=player.id)
        self._session.add(records)

        await self._session.commit()

        logger.info(
            "Added tracked player",
            player_id=player.id,
            riot_id=player.riot_id,
            puuid=player.puuid,
        )

        return player

    async def get_player_by_puuid(self, puuid: str) -> TrackedPlayer | None:
        """Get a tracked player by PUUID.

        Args:
            puuid: Player Universal Unique Identifier

        Returns:
            TrackedPlayer if found, None otherwise
        """
        result = await self._session.execute(
            select(TrackedPlayer).where(TrackedPlayer.puuid == puuid)
        )
        return result.scalar_one_or_none()

    async def get_player_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> TrackedPlayer | None:
        """Get a tracked player by Riot ID.

        Args:
            game_name: Game name part of Riot ID
            tag_line: Tag line part of Riot ID

        Returns:
            TrackedPlayer if found, None otherwise
        """
        result = await self._session.execute(
            select(TrackedPlayer).where(
                TrackedPlayer.game_name == game_name,
                TrackedPlayer.tag_line == tag_line,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_active_players(self) -> list[TrackedPlayer]:
        """Get all players with polling enabled.

        Returns:
            List of active TrackedPlayer instances
        """
        result = await self._session.execute(
            select(TrackedPlayer).where(TrackedPlayer.polling_enabled.is_(True))
        )
        return list(result.scalars().all())

    async def get_all_players(self) -> list[TrackedPlayer]:
        """Get all tracked players.

        Returns:
            List of all TrackedPlayer instances
        """
        result = await self._session.execute(select(TrackedPlayer))
        return list(result.scalars().all())

    async def remove_player(self, puuid: str) -> bool:
        """Remove a player from tracking.

        Args:
            puuid: Player Universal Unique Identifier

        Returns:
            True if player was removed, False if not found
        """
        player = await self.get_player_by_puuid(puuid)
        if player is None:
            return False

        await self._session.delete(player)
        await self._session.commit()

        logger.info(
            "Removed tracked player",
            riot_id=player.riot_id,
            puuid=puuid,
        )

        return True

    async def update_last_polled(
        self,
        player: TrackedPlayer,
    ) -> None:
        """Update the last polled timestamp for a player.

        Args:
            player: The player to update
        """
        player.last_polled_at = datetime.now(UTC)
        await self._session.commit()

    async def toggle_polling(self, puuid: str, enabled: bool) -> bool:
        """Enable or disable polling for a player.

        Args:
            puuid: Player Universal Unique Identifier
            enabled: Whether to enable polling

        Returns:
            True if player was updated, False if not found
        """
        player = await self.get_player_by_puuid(puuid)
        if player is None:
            return False

        player.polling_enabled = enabled
        await self._session.commit()

        logger.info(
            "Updated player polling status",
            riot_id=player.riot_id,
            polling_enabled=enabled,
        )

        return True
