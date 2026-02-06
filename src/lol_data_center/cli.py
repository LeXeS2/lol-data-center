"""CLI application for LoL Data Center."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from lol_data_center.api_client.riot_client import Platform, Region
from lol_data_center.config import get_settings
from lol_data_center.database.engine import get_async_session, init_db
from lol_data_center.logging_config import configure_logging, get_logger
from lol_data_center.services.backfill_service import BackfillService
from lol_data_center.services.player_service import PlayerService

app = typer.Typer(
    name="lol-data-center",
    help="League of Legends match data collection and achievement system",
)
console = Console()
logger = get_logger(__name__)
T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async function in the event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def run() -> None:
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
    region: str = typer.Option(
        "europe", "--region", "-r", help="Region (americas, asia, europe, sea)"
    ),
    platform: str = typer.Option("euw1", "--platform", "-p", help="Platform (euw1, na1, kr, etc.)"),
) -> None:
    """Add a player to track."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    try:
        region_enum = Region(region.lower())
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] Invalid region: {region}")
        console.print("Valid regions: americas, asia, europe, sea")
        raise typer.Exit(1) from exc

    try:
        platform_enum = Platform(platform.lower())
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] Invalid platform: {platform}")
        raise typer.Exit(1) from exc

    async def _add() -> None:
        await init_db()
        async with get_async_session() as session:
            service = PlayerService(session)
            try:
                # Step 1: Add player to database
                player = await service.add_player(game_name, tag_line, region_enum, platform_enum)
                console.print(f"[bold green]✓[/bold green] Added player: {player.riot_id}")
                console.print(f"  PUUID: {player.puuid}")
                console.print(f"  Region: {player.region}")

                # Step 2: Backfill historical matches
                console.print("\n[bold cyan]Fetching match history...[/bold cyan]")

                backfill_service = BackfillService(session)

                # Use rich progress bar
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Loading matches...", total=None)

                    # Progress callback to update the bar
                    def update_progress(current: int, total: int) -> None:
                        if progress.tasks[task].total is None:
                            progress.update(task, total=total)
                        progress.update(
                            task,
                            completed=current,
                            description=f"Loading matches ({current}/{total})",
                        )

                    saved_count = await backfill_service.backfill_player_history(
                        player=player,
                        region=region_enum,
                        progress_callback=update_progress,
                    )

                console.print("\n[bold green]✓[/bold green] Backfill complete!")
                console.print(f"  Total matches saved: {saved_count}")

                # Step 3: Enable polling and set last_polled_at
                if saved_count > 0:
                    await service.toggle_polling(player.puuid, True)
                    await service.update_last_polled(player)
                    console.print("  Set last polled timestamp to prevent re-polling")

            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                raise typer.Exit(1) from e
            except Exception as e:
                console.print(f"[bold red]Error during backfill:[/bold red] {e}")
                logger.exception("Backfill failed")
                raise typer.Exit(1) from e

    run_async(_add())


@app.command()
def remove_player(
    riot_id: str = typer.Argument(..., help="Player Riot ID (GameName#TagLine)"),
) -> None:
    """Remove a player from tracking."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    async def _remove() -> None:
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
def list_players() -> None:
    """List all tracked players."""
    configure_logging()

    async def _list() -> None:
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
) -> None:
    """Enable or disable polling for a player."""
    configure_logging()

    if "#" not in riot_id:
        console.print("[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine")
        raise typer.Exit(1)

    game_name, tag_line = riot_id.rsplit("#", 1)

    async def _toggle() -> None:
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
def migrate() -> None:
    """Run database migrations."""

    configure_logging()
    console.print("[bold]Running database migrations...[/bold]")

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            console.print(result.stdout)
        console.print("[bold green]✓[/bold green] Migrations complete")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error:[/bold red] Migration failed")
        if e.stderr:
            console.print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] Alembic not found. Install with: pip install alembic")
        sys.exit(1)


@app.command()
def poll_now(
    riot_id: str | None = typer.Argument(None, help="Player Riot ID to poll (optional)"),
) -> None:
    """Manually trigger polling for players."""
    from lol_data_center.services.polling_service import PollingService

    configure_logging()

    async def _poll() -> None:
        await init_db()
        service = PollingService()

        if riot_id:
            if "#" not in riot_id:
                console.print(
                    "[bold red]Error:[/bold red] Riot ID must be in format GameName#TagLine"
                )
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
            await service.poll_all_players_once()
            console.print("[bold green]✓[/bold green] Polling complete")

        await service._api_client.close()

    run_async(_poll())


@app.command()
def config() -> None:
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database URL", settings.database_url[:50] + "...")
    table.add_row(
        "Discord Webhook",
        settings.discord_webhook_url[:50] + "..."
        if len(settings.discord_webhook_url) > 50
        else settings.discord_webhook_url,
    )
    table.add_row("Polling Interval", f"{settings.polling_interval_seconds}s")
    table.add_row("Log Level", settings.log_level)
    table.add_row("Default Region", settings.default_region)
    table.add_row(
        "Rate Limit", f"{settings.rate_limit_requests} / {settings.rate_limit_window_seconds}s"
    )
    table.add_row("Invalid Responses Dir", str(settings.invalid_responses_dir))
    table.add_row("Achievements Config", str(settings.achievements_config_path))

    console.print(table)


if __name__ == "__main__":
    app()
