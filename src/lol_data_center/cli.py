"""CLI application for LoL Data Center."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from lol_data_center.api_client.riot_client import Platform, Region
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session, init_db
from lol_data_center.logging_config import configure_logging, get_logger
from lol_data_center.services.player_service import PlayerService

app = typer.Typer(
    name="lol-data-center",
    help="League of Legends match data collection and achievement system",
)
console = Console()
logger = get_logger(__name__)


def run_async(coro):
    """Run an async function in the event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def run():
    """Start the polling service and achievement evaluator."""
    from lol_data_center.main import main

    configure_logging()
    console.print("[bold green]Starting LoL Data Center...[/bold green]")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Shutting down...[/bold yellow]")


@app.command()
def add_player(
    riot_id: str = typer.Argument(..., help="Player Riot ID (GameName#TagLine)"),
    region: str = typer.Option("europe", "--region", "-r", help="Region (americas, asia, europe, sea)"),
    platform: str = typer.Option("euw1", "--platform", "-p", help="Platform (euw1, na1, kr, etc.)"),
):
    """Add a player to track."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    try:
        region_enum = Region(region.lower())
    except ValueError:
        console.print(f"[bold red]Error:[/bold red] Invalid region: {region}")
        console.print("Valid regions: americas, asia, europe, sea")
        raise typer.Exit(1)

    try:
        platform_enum = Platform(platform.lower())
    except ValueError:
        console.print(f"[bold red]Error:[/bold red] Invalid platform: {platform}")
        raise typer.Exit(1)

    async def _add():
        await init_db()
        async with get_async_session() as session:
            service = PlayerService(session)
            try:
                player = await service.add_player(game_name, tag_line, region_enum, platform_enum)
                console.print(f"[bold green]✓[/bold green] Added player: {player.riot_id}")
                console.print(f"  PUUID: {player.puuid}")
                console.print(f"  Region: {player.region}")
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                raise typer.Exit(1)

    run_async(_add())


@app.command()
def remove_player(
    riot_id: str = typer.Argument(..., help="Player Riot ID (GameName#TagLine)"),
):
    """Remove a player from tracking."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    async def _remove():
        async with get_async_session() as session:
            service = PlayerService(session)
            player = await service.get_player_by_riot_id(game_name, tag_line)

            if player is None:
                console.print(f"[bold red]Error:[/bold red] Player not found: {riot_id}")
                raise typer.Exit(1)

            await service.remove_player(player.puuid)
            console.print(f"[bold green]✓[/bold green] Removed player: {riot_id}")

    run_async(_remove())


@app.command()
def list_players():
    """List all tracked players."""
    configure_logging()

    async def _list():
        async with get_async_session() as session:
            service = PlayerService(session)
            players = await service.get_all_players()

            if not players:
                console.print("[yellow]No tracked players found.[/yellow]")
                return

            table = Table(title="Tracked Players")
            table.add_column("ID", style="dim")
            table.add_column("Riot ID", style="cyan")
            table.add_column("Region", style="green")
            table.add_column("Polling", style="yellow")
            table.add_column("Last Polled")

            for player in players:
                polling_status = "✅" if player.polling_enabled else "❌"
                last_polled = (
                    player.last_polled_at.strftime("%Y-%m-%d %H:%M")
                    if player.last_polled_at
                    else "Never"
                )
                table.add_row(
                    str(player.id),
                    player.riot_id,
                    player.region,
                    polling_status,
                    last_polled,
                )

            console.print(table)

    run_async(_list())


@app.command()
def toggle_polling(
    riot_id: str = typer.Argument(..., help="Player Riot ID (GameName#TagLine)"),
    enable: bool = typer.Option(True, "--enable/--disable", help="Enable or disable polling"),
):
    """Enable or disable polling for a player."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    async def _toggle():
        async with get_async_session() as session:
            service = PlayerService(session)
            player = await service.get_player_by_riot_id(game_name, tag_line)

            if player is None:
                console.print(f"[bold red]Error:[/bold red] Player not found: {riot_id}")
                raise typer.Exit(1)

            await service.toggle_polling(player.puuid, enable)
            status = "enabled" if enable else "disabled"
            console.print(f"[bold green]✓[/bold green] Polling {status} for: {riot_id}")

    run_async(_toggle())


@app.command()
def migrate():
    """Run database migrations."""
    configure_logging()
    console.print("[bold]Running database migrations...[/bold]")

    async def _migrate():
        await init_db()
        console.print("[bold green]✓[/bold green] Database initialized")

    run_async(_migrate())


@app.command()
def poll_now(
    riot_id: Optional[str] = typer.Argument(None, help="Player Riot ID to poll (optional)"),
):
    """Manually trigger polling for players."""
    from lol_data_center.services.polling_service import PollingService

    configure_logging()

    async def _poll():
        await init_db()
        service = PollingService()

        if riot_id:
            if "#" not in riot_id:
                console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
                raise typer.Exit(1)

            game_name, tag_line = riot_id.rsplit("#", 1)

            async with get_async_session() as session:
                player_service = PlayerService(session)
                player = await player_service.get_player_by_riot_id(game_name, tag_line)

                if player is None:
                    console.print(f"[bold red]Error:[/bold red] Player not found: {riot_id}")
                    raise typer.Exit(1)

                console.print(f"[bold]Polling player: {riot_id}[/bold]")
                new_matches = await service.poll_player_once(player.puuid)
                console.print(f"[bold green]✓[/bold green] Found {new_matches} new matches")
        else:
            console.print("[bold]Polling all players...[/bold]")
            await service._poll_all_players()
            console.print("[bold green]✓[/bold green] Polling complete")

        await service._api_client.close()

    run_async(_poll())


@app.command()
def config():
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database URL", settings.database_url[:50] + "...")
    table.add_row("Discord Webhook", settings.discord_webhook_url[:50] + "..." if len(settings.discord_webhook_url) > 50 else settings.discord_webhook_url)
    table.add_row("Polling Interval", f"{settings.polling_interval_seconds}s")
    table.add_row("Log Level", settings.log_level)
    table.add_row("Default Region", settings.default_region)
    table.add_row("Rate Limit", f"{settings.rate_limit_requests} / {settings.rate_limit_window_seconds}s")
    table.add_row("Invalid Responses Dir", str(settings.invalid_responses_dir))
    table.add_row("Achievements Config", str(settings.achievements_config_path))

    console.print(table)


if __name__ == "__main__":
    app()
