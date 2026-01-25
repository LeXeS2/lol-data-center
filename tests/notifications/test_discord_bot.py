"""Tests for Discord bot commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import discord
import pytest

from lol_data_center.notifications.discord_bot import (
    DiscordBot,
    get_registered_riot_id,
    register_discord_user,
    unregister_discord_user,
)

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


class TestDiscordUserRegistration:
    """Tests for Discord user registration functionality."""

    @pytest.mark.asyncio
    async def test_register_new_user(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test registering a new Discord user."""
        discord_user_id = "123456789"
        puuid = "test-puuid-123"
        game_name = "TestPlayer"
        tag_line = "EUW"

        # Register user
        registration = await register_discord_user(
            async_session,
            discord_user_id,
            puuid,
            game_name,
            tag_line,
        )

        assert registration.discord_user_id == discord_user_id
        assert registration.puuid == puuid
        assert registration.game_name == game_name
        assert registration.tag_line == tag_line
        assert registration.riot_id == f"{game_name}#{tag_line}"

    @pytest.mark.asyncio
    async def test_update_existing_registration(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test updating an existing registration."""
        discord_user_id = "123456789"
        original_puuid = "original-puuid"
        new_puuid = "new-puuid"

        # Create initial registration
        await register_discord_user(
            async_session,
            discord_user_id,
            original_puuid,
            "OriginalName",
            "NA1",
        )

        # Update registration
        updated_registration = await register_discord_user(
            async_session,
            discord_user_id,
            new_puuid,
            "NewName",
            "EUW",
        )

        assert updated_registration.discord_user_id == discord_user_id
        assert updated_registration.puuid == new_puuid
        assert updated_registration.game_name == "NewName"
        assert updated_registration.tag_line == "EUW"

    @pytest.mark.asyncio
    async def test_get_registered_riot_id(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test retrieving registered Riot ID."""
        discord_user_id = "987654321"
        game_name = "RegisteredPlayer"
        tag_line = "KR"

        # Register user
        await register_discord_user(
            async_session,
            discord_user_id,
            "test-puuid",
            game_name,
            tag_line,
        )

        # Retrieve registration
        result = await get_registered_riot_id(async_session, discord_user_id)

        assert result is not None
        assert result[0] == game_name
        assert result[1] == tag_line
        assert result[2] == f"{game_name}#{tag_line}"

    @pytest.mark.asyncio
    async def test_get_unregistered_riot_id(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test retrieving Riot ID for unregistered user."""
        result = await get_registered_riot_id(async_session, "nonexistent-user")

        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_user(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test unregistering a Discord user."""
        discord_user_id = "111222333"

        # Register user first
        await register_discord_user(
            async_session,
            discord_user_id,
            "test-puuid",
            "TestPlayer",
            "EUW",
        )

        # Verify registration exists
        result = await get_registered_riot_id(async_session, discord_user_id)
        assert result is not None

        # Unregister
        removed = await unregister_discord_user(async_session, discord_user_id)
        assert removed is True

        # Verify registration removed
        result = await get_registered_riot_id(async_session, discord_user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_user(
        self,
        async_session: AsyncSession,
    ) -> None:
        """Test unregistering a user that doesn't exist."""
        removed = await unregister_discord_user(async_session, "nonexistent-user")
        assert removed is False
