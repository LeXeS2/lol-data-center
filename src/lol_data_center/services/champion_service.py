"""Champion data management service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import Champion
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


class ChampionService:
    """Service for managing champion static data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the champion service.

        Args:
            session: Database session
        """
        self._session = session

    async def get_champion_by_id(self, champion_id: int) -> Champion | None:
        """Get champion by champion_id.

        Args:
            champion_id: The champion ID to lookup

        Returns:
            Champion if found, None otherwise
        """
        result = await self._session.execute(
            select(Champion).where(Champion.champion_id == champion_id)
        )
        return result.scalar_one_or_none()

    async def get_all_champions(self) -> list[Champion]:
        """Get all champions.

        Returns:
            List of all champions
        """
        result = await self._session.execute(select(Champion).order_by(Champion.name))
        return list(result.scalars().all())

    async def upsert_champion(
        self,
        champion_id: int,
        name: str,
        key: str,
        title: str,
    ) -> Champion:
        """Create or update a champion.

        Args:
            champion_id: The champion ID
            name: Champion display name
            key: Champion internal key
            title: Champion title

        Returns:
            The created or updated Champion
        """
        # Check if champion exists
        champion = await self.get_champion_by_id(champion_id)

        if champion is None:
            # Create new champion
            champion = Champion(
                champion_id=champion_id,
                name=name,
                key=key,
                title=title,
            )
            self._session.add(champion)
            logger.info("Created new champion", champion_id=champion_id, name=name)
        else:
            # Update existing champion
            champion.name = name
            champion.key = key
            champion.title = title
            logger.debug("Updated champion", champion_id=champion_id, name=name)

        await self._session.commit()
        return champion

    async def bulk_upsert_champions(
        self,
        champions_data: list[dict[str, int | str]],
    ) -> int:
        """Bulk create or update champions.

        Args:
            champions_data: List of champion data dicts with keys:
                champion_id, name, key, title

        Returns:
            Number of champions upserted
        """
        count = 0
        for data in champions_data:
            await self.upsert_champion(
                champion_id=int(data["champion_id"]),
                name=str(data["name"]),
                key=str(data["key"]),
                title=str(data["title"]),
            )
            count += 1

        logger.info("Bulk upserted champions", count=count)
        return count
