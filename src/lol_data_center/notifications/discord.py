"""Discord webhook integration for notifications."""

from datetime import datetime
from typing import Any

import aiohttp

from lol_data_center.config import get_settings
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


class DiscordNotifier:
    """Sends notifications to Discord via webhooks."""

    def __init__(self, webhook_url: str | None = None) -> None:
        """Initialize the Discord notifier.

        Args:
            webhook_url: Discord webhook URL (defaults to settings)
        """
        settings = get_settings()
        self._webhook_url = webhook_url or settings.discord_webhook_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def send_message(
        self,
        content: str,
        title: str | None = None,
        color: int = 0x00FF00,  # Green
        thumbnail_url: str | None = None,
        fields: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send a message to Discord.

        Args:
            content: Main message content
            title: Optional embed title
            color: Embed color (hex)
            thumbnail_url: Optional thumbnail image URL
            fields: Optional embed fields

        Returns:
            True if message was sent successfully
        """
        session = await self._get_session()

        # Build the payload
        if title:
            # Use embed format
            embed: dict[str, Any] = {
                "title": title,
                "description": content,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if thumbnail_url:
                embed["thumbnail"] = {"url": thumbnail_url}

            if fields:
                embed["fields"] = fields

            payload = {"embeds": [embed]}
        else:
            # Simple message
            payload = {"content": content}

        try:
            async with session.post(self._webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.debug("Discord message sent successfully")
                    return True
                elif response.status == 429:
                    # Rate limited
                    retry_after = (await response.json()).get("retry_after", 1)
                    logger.warning(
                        "Discord rate limited",
                        retry_after=retry_after,
                    )
                    return False
                else:
                    text = await response.text()
                    logger.error(
                        "Failed to send Discord message",
                        status_code=response.status,
                        response=text,
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error(
                "Error sending Discord message",
                error=str(e),
            )
            return False

    async def send_achievement(
        self,
        player_name: str,
        achievement_name: str,
        description: str,
        champion_name: str | None = None,
        kda: str | None = None,
        win: bool | None = None,
    ) -> bool:
        """Send an achievement notification.

        Args:
            player_name: Name of the player
            achievement_name: Name of the achievement
            description: Achievement description
            champion_name: Champion played
            kda: KDA string (e.g., "10/2/5")
            win: Whether the game was won

        Returns:
            True if message was sent successfully
        """
        fields = []

        if champion_name:
            fields.append({
                "name": "Champion",
                "value": champion_name,
                "inline": True,
            })

        if kda:
            fields.append({
                "name": "KDA",
                "value": kda,
                "inline": True,
            })

        if win is not None:
            fields.append({
                "name": "Result",
                "value": "✅ Victory" if win else "❌ Defeat",
                "inline": True,
            })

        return await self.send_message(
            content=description,
            title=f"🏆 {player_name}: {achievement_name}",
            color=0xFFD700 if win else 0xFFA500,  # Gold or orange
            fields=fields if fields else None,
        )
