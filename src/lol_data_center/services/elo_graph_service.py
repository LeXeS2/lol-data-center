"""Service for generating ELO progression graphs."""

from datetime import UTC, datetime, timedelta
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import RankHistory
from lol_data_center.logging_config import get_logger
from lol_data_center.services.rank_utils import calculate_elo, format_rank

# Use non-interactive backend for server environments
matplotlib.use("Agg")

logger = get_logger(__name__)


class EloGraphService:
    """Service for generating ELO progression graphs from rank history."""

    @staticmethod
    async def generate_elo_graph(
        session: AsyncSession,
        player_id: int,
        queue_type: str = "RANKED_SOLO_5x5",
        last_weeks: int | None = None,
        season_start: datetime | None = None,
    ) -> BytesIO:
        """Generate an ELO progression graph for a player.

        Args:
            session: Database session
            player_id: Player's database ID
            queue_type: Queue type to graph (default: RANKED_SOLO_5x5)
            last_weeks: Number of weeks to show (default: from season start)
            season_start: Season start date (default: current season start)

        Returns:
            BytesIO buffer containing the PNG image

        Raises:
            ValueError: If no rank data is found for the player
        """
        # Determine time range
        if last_weeks is not None:
            start_time = datetime.now(UTC) - timedelta(weeks=last_weeks)
        elif season_start is not None:
            start_time = season_start
        else:
            # Default to Season 2026 Split 1 start (approximate - January 1, 2026)
            start_time = datetime(2026, 1, 1, tzinfo=UTC)

        # Query rank history
        query = (
            select(RankHistory)
            .where(
                RankHistory.player_id == player_id,
                RankHistory.queue_type == queue_type,
                RankHistory.recorded_at >= start_time,
            )
            .order_by(RankHistory.recorded_at)
        )

        result = await session.execute(query)
        rank_history = result.scalars().all()

        if not rank_history:
            raise ValueError(
                f"No rank data found for player {player_id} in queue {queue_type} "
                f"since {start_time.strftime('%Y-%m-%d')}"
            )

        # Extract data for plotting
        timestamps = [record.recorded_at for record in rank_history]
        elos = [
            calculate_elo(record.tier, record.rank, record.league_points)
            for record in rank_history
        ]

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot ELO progression
        ax.plot(timestamps, elos, marker="o", linestyle="-", linewidth=2, markersize=6)

        # Formatting
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("ELO", fontsize=12)
        ax.set_title(f"ELO Progression - {queue_type}", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        date_formatter = DateFormatter("%Y-%m-%d")
        ax.xaxis.set_major_formatter(date_formatter)
        plt.xticks(rotation=45, ha="right")

        # Add horizontal lines for tier boundaries
        tier_lines = {
            "Iron": 0,
            "Bronze": 400,
            "Silver": 800,
            "Gold": 1200,
            "Platinum": 1600,
            "Emerald": 2000,
            "Diamond": 2400,
            "Master": 2800,
        }

        for tier_name, elo_value in tier_lines.items():
            if min(elos) <= elo_value <= max(elos):
                ax.axhline(
                    y=elo_value,
                    color="gray",
                    linestyle="--",
                    alpha=0.5,
                    linewidth=0.8,
                )
                # Add tier label
                ax.text(
                    timestamps[0],
                    elo_value,
                    f" {tier_name}",
                    verticalalignment="bottom",
                    fontsize=9,
                    alpha=0.7,
                )

        # Add current rank annotation
        latest_record = rank_history[-1]
        latest_rank_str = format_rank(
            latest_record.tier, latest_record.rank, latest_record.league_points
        )
        ax.annotate(
            latest_rank_str,
            xy=(timestamps[-1], elos[-1]),
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )

        # Tight layout to prevent label cutoff
        plt.tight_layout()

        # Save to BytesIO buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Reset buffer position to beginning
        buffer.seek(0)

        logger.info(
            "Generated ELO graph",
            player_id=player_id,
            queue_type=queue_type,
            data_points=len(rank_history),
        )

        return buffer
