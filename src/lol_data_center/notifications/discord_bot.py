"""Discord bot integration for interactive commands."""

import asyncio

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
from lol_data_center.services.player_service import PlayerService
from lol_data_center.services.stats_service import StatsService

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

    @staticmethod
    def _format_damage(damage: int | float) -> str:
        """Format damage value to 'k' notation.

        Args:
            damage: Damage amount

        Returns:
            Formatted damage string (e.g., "25.4k")
        """
        return f"{damage / 1000:.1f}k"

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

                # Add player to database and start backfill
                async with get_async_session() as session:
                    service = PlayerService(session)

                    # Check if player already exists
                    existing_player = await service.get_player_by_riot_id(game_name, tag_line)
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
                        self._backfill_and_notify(interaction, player, region_enum, session)
                    )

                    logger.info(
                        "Player add initiated via Discord bot",
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
            name="stats-by-champion",
            description="View aggregated statistics for a player by champion",
        )
        @app_commands.describe(
            riot_id="Player's Riot ID in format: GameName#TAG",
            min_games="Minimum number of games required (default: 1)",
        )
        async def stats_by_champion_command(
            interaction: discord.Interaction,
            riot_id: str,
            min_games: int = 1,
        ) -> None:
            """View aggregated statistics for a player by champion."""
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

                # Get player and stats
                async with get_async_session() as session:
                    player_service = PlayerService(session)
                    player = await player_service.get_player_by_riot_id(game_name, tag_line)

                    if player is None:
                        await interaction.followup.send(
                            f"❌ Error: Player not found: {riot_id}",
                            ephemeral=True,
                        )
                        return

                    stats_service = StatsService(session)
                    stats = await stats_service.get_stats_by_champion(player.puuid, min_games)

                    if not stats:
                        await interaction.followup.send(
                            f"ℹ️ No stats found for **{riot_id}** "
                            f"(minimum {min_games} game{'s' if min_games > 1 else ''} "
                            "per champion).",
                            ephemeral=True,
                        )
                        return

                    # Create embed with champion stats
                    embed = discord.Embed(
                        title=f"📊 Champion Stats: {riot_id}",
                        description=f"Aggregated statistics by champion (min {min_games} games)",
                        color=discord.Color.blue(),
                    )

                    # Add fields for top champions (limit to 10)
                    for champion_stat in stats[:10]:
                        kda_str = f"{champion_stat.avg_kda:.2f}"
                        cs_str = f"{champion_stat.avg_cs:.1f}"
                        dmg_str = self._format_damage(champion_stat.avg_damage)

                        field_value = (
                            f"**Games:** {champion_stat.game_count} | "
                            f"**WR:** {champion_stat.win_rate:.1f}%\n"
                            f"**KDA:** {champion_stat.avg_kills:.1f}/"
                            f"{champion_stat.avg_deaths:.1f}/"
                            f"{champion_stat.avg_assists:.1f} ({kda_str})\n"
                            f"**CS:** {cs_str} | **Damage:** {dmg_str} | "
                            f"**Vision:** {champion_stat.avg_vision_score:.1f}"
                        )

                        embed.add_field(
                            name=f"🎮 {champion_stat.group_key}",
                            value=field_value,
                            inline=False,
                        )

                    total_games = sum(s.game_count for s in stats)
                    embed.set_footer(
                        text=f"Total: {total_games} games across {len(stats)} champions"
                    )

                    await interaction.followup.send(embed=embed)

                    logger.info(
                        "Stats by champion requested via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except Exception as e:
                logger.exception("Error getting stats by champion via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

        @self._tree.command(
            name="stats-by-role",
            description="View aggregated statistics for a player by role",
        )
        @app_commands.describe(
            riot_id="Player's Riot ID in format: GameName#TAG",
            min_games="Minimum number of games required (default: 1)",
        )
        async def stats_by_role_command(
            interaction: discord.Interaction,
            riot_id: str,
            min_games: int = 1,
        ) -> None:
            """View aggregated statistics for a player by role."""
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

                # Get player and stats
                async with get_async_session() as session:
                    player_service = PlayerService(session)
                    player = await player_service.get_player_by_riot_id(game_name, tag_line)

                    if player is None:
                        await interaction.followup.send(
                            f"❌ Error: Player not found: {riot_id}",
                            ephemeral=True,
                        )
                        return

                    stats_service = StatsService(session)
                    stats = await stats_service.get_stats_by_role(player.puuid, min_games)

                    if not stats:
                        await interaction.followup.send(
                            f"ℹ️ No stats found for **{riot_id}** "
                            f"(minimum {min_games} game{'s' if min_games > 1 else ''} per role).",
                            ephemeral=True,
                        )
                        return

                    # Create embed with role stats
                    embed = discord.Embed(
                        title=f"📊 Role Stats: {riot_id}",
                        description=f"Aggregated statistics by role (min {min_games} games)",
                        color=discord.Color.blue(),
                    )

                    # Role emoji mapping
                    role_emojis = {
                        "TOP": "⚔️",
                        "JUNGLE": "🌲",
                        "MIDDLE": "🔮",
                        "BOTTOM": "🏹",
                        "UTILITY": "🛡️",
                    }

                    # Add fields for all roles
                    for role_stat in stats:
                        role_emoji = role_emojis.get(role_stat.group_key, "❓")
                        kda_str = f"{role_stat.avg_kda:.2f}"
                        cs_str = f"{role_stat.avg_cs:.1f}"
                        dmg_str = self._format_damage(role_stat.avg_damage)

                        field_value = (
                            f"**Games:** {role_stat.game_count} | "
                            f"**WR:** {role_stat.win_rate:.1f}%\n"
                            f"**KDA:** {role_stat.avg_kills:.1f}/"
                            f"{role_stat.avg_deaths:.1f}/"
                            f"{role_stat.avg_assists:.1f} ({kda_str})\n"
                            f"**CS:** {cs_str} | **Damage:** {dmg_str} | "
                            f"**Vision:** {role_stat.avg_vision_score:.1f}"
                        )

                        embed.add_field(
                            name=f"{role_emoji} {role_stat.group_key}",
                            value=field_value,
                            inline=False,
                        )

                    total_games = sum(s.game_count for s in stats)
                    embed.set_footer(text=f"Total: {total_games} games across {len(stats)} roles")

                    await interaction.followup.send(embed=embed)

                    logger.info(
                        "Stats by role requested via Discord bot",
                        riot_id=riot_id,
                        user=str(interaction.user),
                    )

            except Exception as e:
                logger.exception("Error getting stats by role via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

        @self._tree.command(
            name="recent-game",
            description="View details for a player's n-th most recent game",
        )
        @app_commands.describe(
            riot_id="Player's Riot ID in format: GameName#TAG",
            n="Game index (1 = most recent, 2 = second most recent, etc.)",
        )
        async def recent_game_command(
            interaction: discord.Interaction,
            riot_id: str,
            n: int = 1,
        ) -> None:
            """View details for a player's n-th most recent game."""
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

                # Get player and game
                async with get_async_session() as session:
                    player_service = PlayerService(session)
                    player = await player_service.get_player_by_riot_id(game_name, tag_line)

                    if player is None:
                        await interaction.followup.send(
                            f"❌ Error: Player not found: {riot_id}",
                            ephemeral=True,
                        )
                        return

                    stats_service = StatsService(session)
                    game = await stats_service.get_nth_recent_game(player.puuid, n)

                    if game is None:
                        await interaction.followup.send(
                            f"ℹ️ No game found at index {n} for **{riot_id}**.",
                            ephemeral=True,
                        )
                        return

                    # Create embed with game details
                    result_emoji = "✅" if game.win else "❌"
                    result_text = "Victory" if game.win else "Defeat"
                    result_color = discord.Color.green() if game.win else discord.Color.red()

                    embed = discord.Embed(
                        title=f"{result_emoji} Game #{n}: {riot_id}",
                        description=f"{game.champion_name} - {game.individual_position}",
                        color=result_color,
                    )

                    # Game info
                    game_duration = f"{game.time_played // 60}:{game.time_played % 60:02d}"
                    embed.add_field(
                        name="📅 Game Info",
                        value=(
                            f"**Result:** {result_text}\n"
                            f"**Duration:** {game_duration}\n"
                            f"**Date:** {game.game_creation.strftime('%Y-%m-%d %H:%M')}"
                        ),
                        inline=True,
                    )

                    # KDA
                    kda_str = f"{game.kda:.2f}"
                    embed.add_field(
                        name="⚔️ KDA",
                        value=(f"**{game.kills}/{game.deaths}/{game.assists}**\nKDA: {kda_str}"),
                        inline=True,
                    )

                    # Farm & Gold
                    cs_per_min = game.total_minions_killed / (game.time_played / 60)
                    embed.add_field(
                        name="💰 Farm & Gold",
                        value=(
                            f"**CS:** {game.total_minions_killed} ({cs_per_min:.1f}/min)\n"
                            f"**Gold:** {game.gold_earned:,}"
                        ),
                        inline=True,
                    )

                    # Damage & Vision
                    dmg_per_min = game.total_damage_dealt_to_champions / (game.time_played / 60)
                    embed.add_field(
                        name="🎯 Damage & Vision",
                        value=(
                            f"**Damage:** {game.total_damage_dealt_to_champions:,} "
                            f"({dmg_per_min:.0f}/min)\n"
                            f"**Vision Score:** {game.vision_score}"
                        ),
                        inline=True,
                    )

                    # Multi-kills
                    multi_kills = []
                    if game.penta_kills > 0:
                        multi_kills.append(f"🏆 {game.penta_kills} Pentakill")
                    if game.quadra_kills > 0:
                        multi_kills.append(f"💎 {game.quadra_kills} Quadrakill")
                    if game.triple_kills > 0:
                        multi_kills.append(f"💠 {game.triple_kills} Triple")

                    if multi_kills:
                        embed.add_field(
                            name="🌟 Highlights",
                            value="\n".join(multi_kills),
                            inline=True,
                        )

                    # Objectives
                    objectives = []
                    if game.baron_kills > 0:
                        objectives.append(f"Baron: {game.baron_kills}")
                    if game.dragon_kills > 0:
                        objectives.append(f"Dragons: {game.dragon_kills}")
                    if game.turret_kills > 0:
                        objectives.append(f"Turrets: {game.turret_kills}")

                    if objectives:
                        embed.add_field(
                            name="🏰 Objectives",
                            value=" | ".join(objectives),
                            inline=True,
                        )

                    embed.set_footer(text=f"Match ID: {game.match_id}")

                    await interaction.followup.send(embed=embed)

                    logger.info(
                        "Recent game requested via Discord bot",
                        riot_id=riot_id,
                        n=n,
                        match_id=game.match_id,
                        user=str(interaction.user),
                    )

            except Exception as e:
                logger.exception("Error getting recent game via Discord bot")
                await interaction.followup.send(
                    f"❌ An error occurred: {str(e)}",
                    ephemeral=True,
                )

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
