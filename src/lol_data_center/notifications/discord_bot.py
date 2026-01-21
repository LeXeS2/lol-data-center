"""Discord bot integration for interactive commands."""

import asyncio

import discord
from discord import app_commands

from lol_data_center.api_client.riot_client import Platform, Region
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session
from lol_data_center.logging_config import get_logger
from lol_data_center.services.player_service import PlayerService
from lol_data_center.services.polling_service import PollingService

logger = get_logger(__name__)


class DiscordBot:
    """Discord bot with slash commands for interacting with the application."""

    def __init__(self, token: str | None = None) -> None:
        """Initialize the Discord bot.

        Args:
            token: Discord bot token (defaults to settings)
        """
        settings = get_settings()
        self._token = token or settings.discord_bot_token
        self._client: discord.Client | None = None
        self._tree: app_commands.CommandTree | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start the Discord bot."""
        if not self._token:
            logger.warning("Discord bot token not configured, bot will not start")
            return

        # Initialize Discord client with required intents
        intents = discord.Intents.default()
        intents.message_content = False  # We don't need message content for slash commands

        self._client = discord.Client(intents=intents)
        self._tree = app_commands.CommandTree(self._client)

        # Register commands
        self._register_commands()

        # Register event handlers
        @self._client.event
        async def on_ready() -> None:
            if self._client and self._client.user:
                logger.info("Discord bot connected", user=self._client.user.name)
                # Sync commands with Discord
                if self._tree:
                    try:
                        synced = await self._tree.sync()
                        logger.info("Synced slash commands", count=len(synced))
                    except Exception as e:
                        logger.error("Failed to sync commands", error=str(e))

        self._is_running = True

        # Start the bot in the background
        asyncio.create_task(self._run_bot())
        logger.info("Discord bot starting...")

    async def _run_bot(self) -> None:
        """Run the Discord bot (internal task)."""
        if self._client and self._token:
            try:
                await self._client.start(self._token)
            except Exception as e:
                logger.error("Discord bot error", error=str(e))
                self._is_running = False

    def _register_commands(self) -> None:
        """Register all slash commands."""
        if not self._tree:
            return

        @self._tree.command(
            name="add-player",
            description="Add a player to track for match data and achievements",
        )
        @app_commands.describe(
            riot_id="Player's Riot ID in format: GameName#TAG",
            region="Routing region (americas, asia, europe, sea)",
            platform="Platform (euw1, na1, kr, etc.)",
        )
        async def add_player_command(
            interaction: discord.Interaction,
            riot_id: str,
            region: str = "europe",
            platform: str = "euw1",
        ) -> None:
            """Add a player to track."""
            await interaction.response.defer(thinking=True)

            try:
                # Parse Riot ID
                if "#" not in riot_id:
                    await interaction.followup.send(
                        "❌ Error: Riot ID must be in format GameName#TAG",
                        ephemeral=True,
                    )
                    return

                game_name, tag_line = riot_id.rsplit("#", 1)

                # Validate region
                try:
                    region_enum = Region(region.lower())
                except ValueError:
                    await interaction.followup.send(
                        f"❌ Error: Invalid region: {region}\n"
                        "Valid regions: americas, asia, europe, sea",
                        ephemeral=True,
                    )
                    return

                # Validate platform
                try:
                    platform_enum = Platform(platform.lower())
                except ValueError:
                    await interaction.followup.send(
                        f"❌ Error: Invalid platform: {platform}",
                        ephemeral=True,
                    )
                    return

                # Add player to database
                async with get_async_session() as session:
                    service = PlayerService(session)
                    player = await service.add_player(
                        game_name, tag_line, region_enum, platform_enum
                    )

                    # Send success response
                    embed = discord.Embed(
                        title="✅ Player Added Successfully",
                        description=f"Now tracking **{player.riot_id}**",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Region", value=player.region, inline=True)
                    embed.add_field(name="PUUID", value=player.puuid[:20] + "...", inline=True)

                    await interaction.followup.send(embed=embed)
                    logger.info(
                        "Player added via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except ValueError as e:
                await interaction.followup.send(
                    f"❌ Error: {str(e)}",
                    ephemeral=True,
                )
            except Exception as e:
                logger.exception("Error adding player via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

        @self._tree.command(
            name="remove-player",
            description="Remove a player from tracking",
        )
        @app_commands.describe(riot_id="Player's Riot ID in format: GameName#TAG")
        async def remove_player_command(
            interaction: discord.Interaction,
            riot_id: str,
        ) -> None:
            """Remove a player from tracking."""
            await interaction.response.defer(thinking=True)

            try:
                # Parse Riot ID
                if "#" not in riot_id:
                    await interaction.followup.send(
                        "❌ Error: Riot ID must be in format GameName#TAG",
                        ephemeral=True,
                    )
                    return

                game_name, tag_line = riot_id.rsplit("#", 1)

                # Remove player from database
                async with get_async_session() as session:
                    service = PlayerService(session)
                    player = await service.get_player_by_riot_id(game_name, tag_line)

                    if player is None:
                        await interaction.followup.send(
                            f"❌ Error: Player not found: {riot_id}",
                            ephemeral=True,
                        )
                        return

                    await service.remove_player(player.puuid)

                    await interaction.followup.send(
                        f"✅ Removed player: **{riot_id}**",
                    )
                    logger.info(
                        "Player removed via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except Exception as e:
                logger.exception("Error removing player via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

        @self._tree.command(
            name="list-players",
            description="List all tracked players",
        )
        async def list_players_command(interaction: discord.Interaction) -> None:
            """List all tracked players."""
            await interaction.response.defer(thinking=True)

            try:
                async with get_async_session() as session:
                    service = PlayerService(session)
                    players = await service.get_all_players()

                    if not players:
                        await interaction.followup.send(
                            "ℹ️ No tracked players found.",
                            ephemeral=True,
                        )
                        return

                    # Create embed with player list
                    embed = discord.Embed(
                        title="📋 Tracked Players",
                        color=discord.Color.blue(),
                    )

                    # Group players by region
                    regions: dict[str, list[str]] = {}
                    for player in players:
                        if player.region not in regions:
                            regions[player.region] = []
                        polling_status = "✅" if player.polling_enabled else "❌"
                        regions[player.region].append(f"{polling_status} {player.riot_id}")

                    # Add fields for each region
                    for region, player_list in sorted(regions.items()):
                        embed.add_field(
                            name=f"{region.upper()} ({len(player_list)})",
                            value="\n".join(player_list[:10]),  # Limit to 10 per region
                            inline=False,
                        )

                    embed.set_footer(text=f"Total: {len(players)} players")

                    await interaction.followup.send(embed=embed)

            except Exception as e:
                logger.exception("Error listing players via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

        @self._tree.command(
            name="poll-now",
            description="Manually trigger polling for a player or all players",
        )
        @app_commands.describe(riot_id="Optional: Player's Riot ID to poll (leave empty for all)")
        async def poll_now_command(
            interaction: discord.Interaction,
            riot_id: str = "",
        ) -> None:
            """Manually trigger polling."""
            await interaction.response.defer(thinking=True)

            try:
                polling_service = PollingService()

                if riot_id:
                    # Poll specific player
                    if "#" not in riot_id:
                        await interaction.followup.send(
                            "❌ Error: Riot ID must be in format GameName#TAG",
                            ephemeral=True,
                        )
                        return

                    game_name, tag_line = riot_id.rsplit("#", 1)

                    async with get_async_session() as session:
                        player_service = PlayerService(session)
                        player = await player_service.get_player_by_riot_id(
                            game_name, tag_line
                        )

                        if player is None:
                            await interaction.followup.send(
                                f"❌ Error: Player not found: {riot_id}",
                                ephemeral=True,
                            )
                            return

                        new_matches = await polling_service.poll_player_once(player.puuid)

                        await interaction.followup.send(
                            f"✅ Poll complete for **{riot_id}**\n"
                            f"Found {new_matches} new matches",
                        )
                else:
                    # Poll all players
                    await polling_service.poll_all_players_once()
                    await interaction.followup.send(
                        "✅ Polling complete for all players",
                    )

                logger.info(
                    "Manual poll triggered via Discord bot",
                    riot_id=riot_id or "all",
                    user=str(interaction.user),
                )

            except Exception as e:
                logger.exception("Error polling via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._client and self._is_running:
            logger.info("Stopping Discord bot...")
            await self._client.close()
            self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if the bot is running."""
        return self._is_running
