"""Discord bot integration for interactive commands."""

import asyncio
from io import BytesIO

import discord
from discord import app_commands
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.api_client.riot_client import Platform, Region
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import MatchParticipant, TrackedPlayer
from lol_data_center.logging_config import get_logger
from lol_data_center.services.backfill_service import BackfillService
from lol_data_center.services.map_visualization_service import MapVisualizationService
from lol_data_center.services.player_service import PlayerService

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for Discord bot validation errors."""

    pass


def parse_riot_id(riot_id: str) -> tuple[str, str]:
    """Parse and validate Riot ID format.

    Args:
        riot_id: Riot ID in format GameName#TAG

    Returns:
        Tuple of (game_name, tag_line)

    Raises:
        ValidationError: If format is invalid
    """
    if "#" not in riot_id:
        raise ValidationError("Riot ID must be in format GameName#TAG")
    return riot_id.rsplit("#", 1)


def parse_region(region_str: str) -> Region:
    """Parse and validate region string.

    Args:
        region_str: Region string (case-insensitive)

    Returns:
        Region enum value

    Raises:
        ValidationError: If region is invalid
    """
    try:
        return Region(region_str.lower())
    except ValueError:
        valid = ", ".join([r.value for r in Region])
        raise ValidationError(f"Invalid region: {region_str}\nValid regions: {valid}")


def parse_platform(platform_str: str) -> Platform:
    """Parse and validate platform string.

    Args:
        platform_str: Platform string (case-insensitive)

    Returns:
        Platform enum value

    Raises:
        ValidationError: If platform is invalid
    """
    try:
        return Platform(platform_str.lower())
    except ValueError:
        valid = ", ".join([p.value for p in Platform])
        raise ValidationError(f"Invalid platform: {platform_str}\nValid platforms: {valid}")


async def send_error_response(
    interaction: discord.Interaction,
    error: Exception,
    command_name: str | None = None,
) -> None:
    """Send formatted error response to user.

    Args:
        interaction: Discord interaction
        error: Exception that occurred
        command_name: Name of command for logging (optional)
    """
    if isinstance(error, ValidationError):
        await interaction.followup.send(f"❌ Error: {str(error)}", ephemeral=True)
    else:
        if command_name:
            logger.exception(f"Error {command_name} via Discord bot")
        else:
            logger.exception("Discord bot error")
        await interaction.followup.send(
            f"❌ An error occurred: {str(error)}",
            ephemeral=True,
        )


async def get_player_or_error(
    interaction: discord.Interaction,
    service: PlayerService,
    game_name: str,
    tag_line: str,
    riot_id: str,
) -> TrackedPlayer | None:
    """Get player by riot_id or send error response.

    Args:
        interaction: Discord interaction
        service: PlayerService instance
        game_name: Player's game name
        tag_line: Player's tag line
        riot_id: Full Riot ID (for error messages)

    Returns:
        TrackedPlayer if found, None if not found (error already sent to user)
    """
    player = await service.get_player_by_riot_id(game_name, tag_line)
    if player is None:
        await interaction.followup.send(
            f"❌ Error: Player not found: {riot_id}",
            ephemeral=True,
        )
    return player


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
                # Parse and validate inputs
                game_name, tag_line = parse_riot_id(riot_id)
                region_enum = parse_region(region)
                platform_enum = parse_platform(platform)

                # Add player to database and start backfill
                async with get_async_session() as session:
                    service = PlayerService(session)

                    # Check if player already exists
                    existing_player = await service.get_player_by_riot_id(
                        game_name, tag_line
                    )
                    if existing_player:
                        await interaction.followup.send(
                            f"⚠️ Player **{riot_id}** is already being tracked.",
                            ephemeral=True,
                        )
                        return

                    player = await service.add_player(
                        game_name, tag_line, region_enum, platform_enum
                    )

                    # Send initial response with estimated time
                    embed = discord.Embed(
                        title="⏳ Adding Player...",
                        description=f"**{player.riot_id}** is being added to tracking.",
                        color=discord.Color.blue(),
                    )
                    embed.add_field(name="Region", value=player.region, inline=True)
                    embed.add_field(name="Platform", value=platform, inline=True)
                    embed.add_field(
                        name="📊 Status",
                        value=(
                            "Fetching match history (this may take 10-15 minutes)\n"
                            "You will receive a notification when complete."
                        ),
                        inline=False,
                    )

                    await interaction.followup.send(embed=embed)

                    # Start background task for backfill
                    asyncio.create_task(
                        self._backfill_and_notify(
                            interaction, player, region_enum, session
                        )
                    )

                    logger.info(
                        "Player add initiated via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except (ValidationError, ValueError) as e:
                await send_error_response(interaction, e)
            except Exception as e:
                await send_error_response(interaction, e, "add-player")

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
                # Parse and validate Riot ID
                game_name, tag_line = parse_riot_id(riot_id)

                # Remove player from database
                async with get_async_session() as session:
                    service = PlayerService(session)
                    player = await get_player_or_error(
                        interaction, service, game_name, tag_line, riot_id
                    )

                    if player is None:
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

            except (ValidationError, ValueError) as e:
                await send_error_response(interaction, e)
            except Exception as e:
                await send_error_response(interaction, e, "remove-player")

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
                await send_error_response(interaction, e, "list-players")

        @self._tree.command(
            name="player-map-position",
            description="Generate a map position heatmap for a tracked player",
        )
        @app_commands.describe(
            riot_id="Player's Riot ID in format: GameName#TAG",
        )
        async def player_map_position_command(
            interaction: discord.Interaction,
            riot_id: str,
        ) -> None:
            """Generate player map position heatmap."""
            await interaction.response.defer(thinking=True)

            try:
                # Parse and validate Riot ID
                game_name, tag_line = parse_riot_id(riot_id)

                async with get_async_session() as session:
                    # Get player
                    service = PlayerService(session)
                    player = await get_player_or_error(
                        interaction, service, game_name, tag_line, riot_id
                    )

                    if player is None:
                        return

                    # Log operation
                    logger.info(
                        "Generating heatmap for player",
                        puuid=player.puuid,
                        riot_id=riot_id,
                    )

                    # Generate heatmap asynchronously
                    viz_service = MapVisualizationService(session)
                    try:
                        heatmap_image = await viz_service.generate_player_heatmap_with_map_overlay(
                            player.puuid
                        )
                    except ValueError:
                        await interaction.followup.send(
                            f"❌ No position data found for **{riot_id}**.\n"
                            "Make sure the player has tracked matches with timeline data.",
                            ephemeral=True,
                        )
                        return

                    # Send heatmap as file
                    await interaction.followup.send(
                        f"📍 Map Position Heatmap for **{riot_id}**",
                        file=discord.File(
                            BytesIO(heatmap_image),
                            filename=f"heatmap_{player.puuid}.png",
                        ),
                    )

                    logger.info(
                        "Heatmap sent via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except (ValidationError, ValueError) as e:
                await send_error_response(interaction, e)
            except Exception as e:
                await send_error_response(interaction, e, "player-map-position")

    async def _backfill_and_notify(
        self,
        interaction: discord.Interaction,
        player: TrackedPlayer,
        region: Region,
        session: AsyncSession,
    ) -> None:
        """Backfill player history and notify when complete.

        Args:
            interaction: Discord interaction for sending follow-up
            player: The tracked player
            region: Region for API calls
            session: Database session
        """
        try:
            backfill_service = BackfillService(session)

            # Perform backfill
            saved_count = await backfill_service.backfill_player_history(
                player=player,
                region=region,
            )

            # Update last_match_id to prevent re-processing
            if saved_count > 0:
                result = await session.execute(
                    select(MatchParticipant.match_id)
                    .where(MatchParticipant.puuid == player.puuid)
                    .order_by(desc(MatchParticipant.game_creation))
                    .limit(1)
                )
                latest_match_id = result.scalar_one_or_none()

                if latest_match_id:
                    player_service = PlayerService(session)
                    await player_service.update_last_polled(player, latest_match_id)

            # Send success notification
            embed = discord.Embed(
                title="✅ Player Added Successfully",
                description=f"**{player.riot_id}** is now being tracked!",
                color=discord.Color.green(),
            )
            embed.add_field(name="Region", value=player.region, inline=True)
            embed.add_field(
                name="Matches Loaded",
                value=f"{saved_count} historical matches",
                inline=True,
            )
            embed.add_field(
                name="📈 Status",
                value="Ready to track new matches!",
                inline=False,
            )

            await interaction.followup.send(embed=embed)

            logger.info(
                "Player backfill complete via Discord bot",
                riot_id=player.riot_id,
                saved_count=saved_count,
            )

        except Exception as e:
            logger.exception("Error during backfill via Discord bot")
            embed = discord.Embed(
                title="⚠️ Warning",
                description=f"**{player.riot_id}** was added but match history loading failed.",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Error",
                value=str(e)[:1024],  # Discord field value limit
                inline=False,
            )
            embed.add_field(
                name="Next Steps",
                value=(
                    "The player is tracked but historical matches were not loaded. "
                    "New matches will be tracked normally."
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)

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
