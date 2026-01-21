"""Tests for Discord notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from lol_data_center.notifications.discord import DiscordNotifier


class TestDiscordNotifier:
    """Tests for DiscordNotifier."""

    @pytest.mark.asyncio
    async def test_send_message_success(self) -> None:
        """Test sending a message successfully."""
        webhook_url = "https://discord.com/api/webhooks/test"
        notifier = DiscordNotifier(webhook_url=webhook_url)

        # Mock the session and post context manager
        mock_response = AsyncMock()
        mock_response.status = 204

        mock_post = AsyncMock()
        mock_post.__aenter__.return_value = mock_response

        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.return_value = mock_post
        mock_session.closed = False

        # Inject the mock session
        notifier._session = mock_session

        success = await notifier.send_message("Test message")

        assert success is True
        mock_session.post.assert_called_once()
        args, kwargs = mock_session.post.call_args
        assert args[0] == webhook_url
        assert kwargs["json"] == {"content": "Test message"}

        await notifier.close()

    @pytest.mark.asyncio
    async def test_send_achievement(self) -> None:
        """Test sending an achievement notification."""
        notifier = DiscordNotifier(webhook_url="test")
        notifier.send_message = AsyncMock(return_value=True)

        success = await notifier.send_achievement(
            player_name="TestPlayer",
            achievement_name="High Kills",
            description="Got 20 kills",
            champion_name="Annie",
            kda="20/5/10",
            win=True,
        )

        assert success is True
        notifier.send_message.assert_called_once()
        _, kwargs = notifier.send_message.call_args
        assert kwargs["title"] == "🏆 TestPlayer: High Kills"
        assert kwargs["content"] == "Got 20 kills"
        assert len(kwargs["fields"]) == 3
