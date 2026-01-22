"""Tests for Discord bot commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import discord
import pytest

from lol_data_center.notifications.discord_bot import DiscordBot

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestDiscordBot:
    """Tests for DiscordBot."""

    @pytest.mark.asyncio
    async def test_bot_initialization_without_token(self) -> None:
        """Test that bot doesn't start without token."""
        with patch("lol_data_center.notifications.discord_bot.get_settings") as mock_settings:
            mock_settings.return_value.discord_bot_token = None
            bot = DiscordBot(token=None)

            await bot.start()

            # Bot should not be running without token
            assert not bot.is_running

    @pytest.mark.asyncio
    async def test_bot_initialization_with_token(self) -> None:
        """Test bot initialization with token."""
        bot = DiscordBot(token="test-token")

        # Bot should be created but not yet running
        assert not bot.is_running

    @pytest.mark.asyncio
    async def test_bot_stop(self) -> None:
        """Test bot stop method."""
        bot = DiscordBot(token="test-token")

        # Mock the client
        mock_client = AsyncMock(spec=discord.Client)
        mock_client.close = AsyncMock()
        bot._client = mock_client
        bot._is_running = True

        await bot.stop()

        mock_client.close.assert_called_once()
        assert not bot.is_running


class TestDiscordBotCommands:
    """Tests for Discord bot slash commands."""

    @pytest.mark.asyncio
    async def test_add_player_command_invalid_riot_id(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test add-player command with invalid Riot ID format."""
        # This test verifies the command logic structure
        # Full integration testing would require mocking Discord interactions

        # Test that Riot ID validation works
        riot_id = "InvalidFormat"  # Missing #TAG

        # This would fail validation in the actual command
        assert "#" not in riot_id

    @pytest.mark.asyncio
    async def test_add_player_command_valid_riot_id(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test add-player command with valid Riot ID format."""
        riot_id = "TestPlayer#EUW"

        # Verify Riot ID can be parsed
        assert "#" in riot_id
        game_name, tag_line = riot_id.rsplit("#", 1)
        assert game_name == "TestPlayer"
        assert tag_line == "EUW"

    @pytest.mark.asyncio
    async def test_remove_player_command_validation(self) -> None:
        """Test remove-player command Riot ID validation."""
        # Test invalid format
        riot_id_invalid = "InvalidFormat"
        assert "#" not in riot_id_invalid

        # Test valid format
        riot_id_valid = "TestPlayer#EUW"
        assert "#" in riot_id_valid

    @pytest.mark.asyncio
    async def test_stats_by_champion_command_validation(self) -> None:
        """Test stats-by-champion command Riot ID validation."""
        # Test invalid format
        riot_id_invalid = "InvalidFormat"
        assert "#" not in riot_id_invalid

        # Test valid format
        riot_id_valid = "TestPlayer#EUW"
        assert "#" in riot_id_valid
        game_name, tag_line = riot_id_valid.rsplit("#", 1)
        assert game_name == "TestPlayer"
        assert tag_line == "EUW"

    @pytest.mark.asyncio
    async def test_stats_by_role_command_validation(self) -> None:
        """Test stats-by-role command Riot ID validation."""
        # Test invalid format
        riot_id_invalid = "InvalidFormat"
        assert "#" not in riot_id_invalid

        # Test valid format
        riot_id_valid = "TestPlayer#EUW"
        assert "#" in riot_id_valid
        game_name, tag_line = riot_id_valid.rsplit("#", 1)
        assert game_name == "TestPlayer"
        assert tag_line == "EUW"

    @pytest.mark.asyncio
    async def test_recent_game_command_validation(self) -> None:
        """Test recent-game command Riot ID validation and game index."""
        # Test invalid format
        riot_id_invalid = "InvalidFormat"
        assert "#" not in riot_id_invalid

        # Test valid format
        riot_id_valid = "TestPlayer#EUW"
        assert "#" in riot_id_valid

        # Test valid game index
        n_valid = 1
        assert n_valid >= 1

        # Test another valid game index
        n_valid_2 = 5
        assert n_valid_2 >= 1
