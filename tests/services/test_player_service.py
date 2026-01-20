"""Tests for PlayerService."""

import pytest
from unittest.mock import AsyncMock

from lol_data_center.services.player_service import PlayerService


class TestPlayerService:
    """Tests for PlayerService."""

    @pytest.mark.asyncio
    async def test_get_player_by_puuid(self, async_session, sample_player):
        """Test getting a player by PUUID."""
        service = PlayerService(async_session)

        player = await service.get_player_by_puuid(sample_player.puuid)

        assert player is not None
        assert player.puuid == sample_player.puuid
        assert player.riot_id == f"{sample_player.game_name}#{sample_player.tag_line}"

    @pytest.mark.asyncio
    async def test_get_player_by_puuid_not_found(self, async_session):
        """Test getting a player by PUUID when not found."""
        service = PlayerService(async_session)

        player = await service.get_player_by_puuid("nonexistent-puuid")

        assert player is None

    @pytest.mark.asyncio
    async def test_get_player_by_riot_id(self, async_session, sample_player):
        """Test getting a player by Riot ID."""
        service = PlayerService(async_session)

        player = await service.get_player_by_riot_id(
            sample_player.game_name,
            sample_player.tag_line,
        )

        assert player is not None
        assert player.id == sample_player.id

    @pytest.mark.asyncio
    async def test_get_all_active_players(self, async_session, sample_player):
        """Test getting all active players."""
        service = PlayerService(async_session)

        players = await service.get_all_active_players()

        assert len(players) == 1
        assert players[0].puuid == sample_player.puuid

    @pytest.mark.asyncio
    async def test_toggle_polling(self, async_session, sample_player):
        """Test toggling polling for a player."""
        service = PlayerService(async_session)

        # Disable polling
        result = await service.toggle_polling(sample_player.puuid, False)
        assert result is True

        # Verify
        player = await service.get_player_by_puuid(sample_player.puuid)
        assert player.polling_enabled is False

        # Re-enable
        await service.toggle_polling(sample_player.puuid, True)
        player = await service.get_player_by_puuid(sample_player.puuid)
        assert player.polling_enabled is True
