"""Service for generating map position visualizations."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import TimelineParticipantFrame
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

# League of Legends map dimensions in units
MAP_WIDTH = 15000
MAP_HEIGHT = 15000

# Heatmap configuration
HEATMAP_BINS = 75
HEATMAP_COLOR_MAP = "hot"


class MapVisualizationService:
    """Service for generating map position heatmaps."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the map visualization service.

        Args:
            session: AsyncSession for database operations
        """
        self._session = session

    async def generate_player_heatmap(
        self,
        player_puuid: str,
        max_samples: int = 50000,
    ) -> bytes:
        """Generate a heatmap of player positions on the map.

        Args:
            player_puuid: PUUID of the player
            max_samples: Maximum number of position samples to use (for performance)

        Returns:
            PNG image as bytes

        Raises:
            ValueError: If no position data found for player
        """
        # Query all position data for the player
        logger.info("Querying position data for player", puuid=player_puuid)

        result = await self._session.execute(
            select(
                TimelineParticipantFrame.position_x,
                TimelineParticipantFrame.position_y,
            ).where(TimelineParticipantFrame.puuid == player_puuid)
        )

        rows = result.fetchall()

        if not rows:
            raise ValueError(f"No position data found for player {player_puuid}")

        # Extract positions from tuples
        x_positions = np.array([row[0] for row in rows], dtype=np.int32)
        y_positions = np.array([row[1] for row in rows], dtype=np.int32)

        # Limit samples for performance
        if len(x_positions) > max_samples:
            logger.info(
                "Limiting samples for heatmap",
                total=len(x_positions),
                max_samples=max_samples,
            )
            indices = np.random.choice(len(x_positions), max_samples, replace=False)
            x_positions = x_positions[indices]
            y_positions = y_positions[indices]

        logger.info(
            "Generating heatmap",
            puuid=player_puuid,
            sample_count=len(x_positions),
        )

        # Create 2D histogram
        heatmap, xedges, yedges = np.histogram2d(
            x_positions,
            y_positions,
            bins=HEATMAP_BINS,
            range=[[0, MAP_WIDTH], [0, MAP_HEIGHT]],
        )

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 12), dpi=100)

        try:
            # Display heatmap with log normalization
            # (to handle varying frequency distribution)
            im = ax.imshow(
                heatmap.T,
                extent=[0, MAP_WIDTH, 0, MAP_HEIGHT],
                origin="lower",
                cmap=HEATMAP_COLOR_MAP,
                norm=LogNorm(),
                interpolation="bilinear",
            )

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, label="Position Frequency (log scale)")

            # Configure axes
            ax.set_xlabel("X Position")
            ax.set_ylabel("Y Position")
            ax.set_title(f"Player Position Heatmap\n{player_puuid}")

            # Add grid for reference
            ax.grid(True, alpha=0.3, linestyle="--")

            # Convert to bytes
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
            buf.seek(0)

            logger.info("Heatmap generated successfully", puuid=player_puuid)
            return buf.getvalue()

        finally:
            plt.close(fig)

    async def generate_player_heatmap_with_map_overlay(
        self,
        player_puuid: str,
        max_samples: int = 50000,
    ) -> bytes:
        """Generate a heatmap overlay on the League of Legends map.

        Args:
            player_puuid: PUUID of the player
            max_samples: Maximum number of position samples to use

        Returns:
            PNG image as bytes

        Raises:
            ValueError: If no position data found for player
            Exception: If map image cannot be downloaded
        """
        # Query all position data for the player
        logger.info(
            "Querying position data for map overlay",
            puuid=player_puuid,
        )

        result = await self._session.execute(
            select(
                TimelineParticipantFrame.position_x,
                TimelineParticipantFrame.position_y,
            ).where(TimelineParticipantFrame.puuid == player_puuid)
        )

        rows = result.fetchall()

        if not rows:
            raise ValueError(f"No position data found for player {player_puuid}")

        # Extract positions from tuples
        x_positions = np.array([row[0] for row in rows], dtype=np.int32)
        y_positions = np.array([row[1] for row in rows], dtype=np.int32)

        # Limit samples for performance
        if len(x_positions) > max_samples:
            logger.info(
                "Limiting samples for heatmap",
                total=len(x_positions),
                max_samples=max_samples,
            )
            indices = np.random.choice(len(x_positions), max_samples, replace=False)
            x_positions = x_positions[indices]
            y_positions = y_positions[indices]

        logger.info(
            "Generating heatmap with map overlay",
            puuid=player_puuid,
            sample_count=len(x_positions),
        )

        # Create 2D histogram
        heatmap, xedges, yedges = np.histogram2d(
            x_positions,
            y_positions,
            bins=HEATMAP_BINS,
            range=[[0, MAP_WIDTH], [0, MAP_HEIGHT]],
        )

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 12), dpi=100)

        try:
            # Download and display map image from Riot CDN
            import aiohttp

            try:
                map_url = (
                    "https://ddragon.leagueoflegends.com/cdn/15.7.1/img/map/map11.png"
                )

                async with aiohttp.ClientSession() as session:
                    async with session.get(map_url, timeout=aiohttp.ClientTimeout(10)) as resp:
                        if resp.status == 200:
                            map_image = plt.imread(BytesIO(await resp.read()))
                            ax.imshow(
                                map_image,
                                extent=[0, MAP_WIDTH, 0, MAP_HEIGHT],
                                origin="upper",
                                alpha=0.7,
                                zorder=1,
                            )
                            logger.info("Map overlay downloaded successfully")
                        else:
                            logger.warning(
                                "Failed to download map image",
                                status_code=resp.status,
                            )
            except Exception as e:
                logger.warning("Could not download map overlay", error=str(e))

            # Display heatmap overlay
            im = ax.imshow(
                heatmap.T,
                extent=[0, MAP_WIDTH, 0, MAP_HEIGHT],
                origin="lower",
                cmap=HEATMAP_COLOR_MAP,
                norm=LogNorm(),
                interpolation="bilinear",
                alpha=0.6,
                zorder=2,
            )

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, label="Position Frequency (log scale)")

            # Configure axes
            ax.set_xlabel("X Position")
            ax.set_ylabel("Y Position")
            ax.set_title(f"Player Position Heatmap\n{player_puuid}")

            # Convert to bytes
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
            buf.seek(0)

            logger.info("Heatmap with map overlay generated successfully", puuid=player_puuid)
            return buf.getvalue()

        finally:
            plt.close(fig)

