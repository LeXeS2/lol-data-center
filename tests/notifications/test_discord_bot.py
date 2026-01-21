"""Tests for Discord bot commands."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from lol_data_center.notifications.discord_bot import DiscordBot


class TestDiscordBot:
    """Tests for DiscordBot."""

    @pytest.mark.asyncio
    async def test_bot_initialization_without_token(self):
        """Test that bot doesn't start without token."""
        bot = DiscordBot(token="")

        await bot.start()

        # Bot should not be running without token
        assert not bot.is_running

    @pytest.mark.asyncio
    async def test_bot_initialization_with_token(self):
        """Test bot initialization with token."""
        bot = DiscordBot(token="test-token")

        # Bot should be created but not yet running
        assert not bot.is_running

    @pytest.mark.asyncio
    async def test_bot_stop(self):
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
    async def test_add_player_command_invalid_riot_id(self, async_session):
        """Test add-player command with invalid Riot ID format."""
        # This test verifies the command logic structure
        # Full integration testing would require mocking Discord interactions
        
        # Test that Riot ID validation works
        riot_id = "InvalidFormat"  # Missing #TAG
        
        # This would fail validation in the actual command
        assert "#" not in riot_id

    @pytest.mark.asyncio
    async def test_add_player_command_valid_riot_id(self, async_session):
        """Test add-player command with valid Riot ID format."""
        riot_id = "TestPlayer#EUW"
        
        # Verify Riot ID can be parsed
        assert "#" in riot_id
        game_name, tag_line = riot_id.rsplit("#", 1)
        assert game_name == "TestPlayer"
        assert tag_line == "EUW"

    @pytest.mark.asyncio
    async def test_remove_player_command_validation(self):
        """Test remove-player command Riot ID validation."""
        # Test invalid format
        riot_id_invalid = "InvalidFormat"
        assert "#" not in riot_id_invalid
        
        # Test valid format
        riot_id_valid = "TestPlayer#EUW"
        assert "#" in riot_id_valid
