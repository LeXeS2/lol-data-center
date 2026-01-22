"""Tests for ChampionService."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lol_data_center.database.models import Champion
from lol_data_center.services.champion_service import ChampionService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestChampionService:
    """Tests for ChampionService."""

    @pytest.mark.asyncio
    async def test_get_champion_by_id_not_found(self, async_session: AsyncSession) -> None:
        """Test get_champion_by_id returns None for non-existent champion."""
        service = ChampionService(async_session)

        champion = await service.get_champion_by_id(999)

        assert champion is None

    @pytest.mark.asyncio
    async def test_upsert_champion_creates_new(self, async_session: AsyncSession) -> None:
        """Test upserting a new champion."""
        from sqlalchemy import select

        service = ChampionService(async_session)

        champion = await service.upsert_champion(
            champion_id=1,
            name="Annie",
            key="Annie",
            title="the Dark Child",
        )

        assert champion.champion_id == 1
        assert champion.name == "Annie"
        assert champion.key == "Annie"
        assert champion.title == "the Dark Child"

        # Verify it was saved to database
        result = await async_session.execute(
            select(Champion).where(Champion.champion_id == 1)
        )
        saved_champion = result.scalar_one_or_none()
        assert saved_champion is not None
        assert saved_champion.name == "Annie"

    @pytest.mark.asyncio
    async def test_upsert_champion_updates_existing(self, async_session: AsyncSession) -> None:
        """Test upserting updates an existing champion."""
        service = ChampionService(async_session)

        # Create initial champion
        champion1 = await service.upsert_champion(
            champion_id=2,
            name="Ahri",
            key="Ahri",
            title="the Nine-Tailed Fox",
        )
        initial_id = champion1.id

        # Update the champion
        champion2 = await service.upsert_champion(
            champion_id=2,
            name="Ahri Updated",
            key="AhriNew",
            title="the Updated Fox",
        )

        assert champion2.id == initial_id  # Same database row
        assert champion2.name == "Ahri Updated"
        assert champion2.key == "AhriNew"
        assert champion2.title == "the Updated Fox"

    @pytest.mark.asyncio
    async def test_get_all_champions(self, async_session: AsyncSession) -> None:
        """Test getting all champions."""
        service = ChampionService(async_session)

        # Create multiple champions
        await service.upsert_champion(1, "Annie", "Annie", "the Dark Child")
        await service.upsert_champion(2, "Ahri", "Ahri", "the Nine-Tailed Fox")
        await service.upsert_champion(3, "Ashe", "Ashe", "the Frost Archer")

        champions = await service.get_all_champions()

        assert len(champions) == 3
        # Should be ordered by name
        assert champions[0].name == "Ahri"
        assert champions[1].name == "Annie"
        assert champions[2].name == "Ashe"

    @pytest.mark.asyncio
    async def test_bulk_upsert_champions(self, async_session: AsyncSession) -> None:
        """Test bulk upserting champions."""
        service = ChampionService(async_session)

        champions_data = [
            {"champion_id": 1, "name": "Annie", "key": "Annie", "title": "the Dark Child"},
            {"champion_id": 2, "name": "Ahri", "key": "Ahri", "title": "the Nine-Tailed Fox"},
            {"champion_id": 3, "name": "Ashe", "key": "Ashe", "title": "the Frost Archer"},
        ]

        count = await service.bulk_upsert_champions(champions_data)

        assert count == 3

        # Verify all were created
        all_champions = await service.get_all_champions()
        assert len(all_champions) == 3
