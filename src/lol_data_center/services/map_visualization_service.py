"""Service for generating map position visualizations."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import (
    MatchParticipant,
    TimelineParticipantFrame,
    TrackedPlayer,
)
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

# League of Legends map dimensions in units
MAP_WIDTH = 15000
MAP_HEIGHT = 15000

# Heatmap configuration
HEATMAP_BINS = 75
HEATMAP_COLOR_MAP = "hot"

# Allowed role filters (team_position values)
ALLOWED_ROLES = {"top", "jungle", "middle", "bottom", "utility"}


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
        role: str | None = None,
        champion: str | None = None,
        max_samples: int = 50000,
    ) -> bytes:
        """Generate a heatmap of player positions on the map.

        Args:
            player_puuid: PUUID of the player
            role: Optional role filter (uses team_position field)
            champion: Optional champion name filter
            max_samples: Maximum number of position samples to use (for performance)

        Returns:
            PNG image as bytes

        Raises:
            ValueError: If no position data found for player
        """
        riot_id = await self._get_player_riot_id(player_puuid)

        await self.validate_filters(player_puuid, role=role, champion=champion)

        x_positions, y_positions = await self._load_positions(
            player_puuid,
            role=role,
            champion=champion,
        )

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
            plt.colorbar(im, ax=ax, label="Position Frequency (log scale)")

            # Configure axes
            ax.set_xlabel("X Position")
            ax.set_ylabel("Y Position")
            ax.set_title(self._build_title(riot_id, champion, role))

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
        role: str | None = None,
        champion: str | None = None,
        max_samples: int = 50000,
    ) -> bytes:
        """Generate a heatmap overlay on the League of Legends map.

        Args:
            player_puuid: PUUID of the player
            role: Optional role filter (uses team_position field)
            champion: Optional champion name filter
            max_samples: Maximum number of position samples to use

        Returns:
            PNG image as bytes

        Raises:
            ValueError: If no position data found for player
            Exception: If map image cannot be downloaded
        """
        riot_id = await self._get_player_riot_id(player_puuid)

        await self.validate_filters(player_puuid, role=role, champion=champion)

        x_positions, y_positions = await self._load_positions(
            player_puuid,
            role=role,
            champion=champion,
        )

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
                map_url = "https://ddragon.leagueoflegends.com/cdn/15.7.1/img/map/map11.png"

                async with (
                    aiohttp.ClientSession() as session,
                    session.get(map_url, timeout=aiohttp.ClientTimeout(10)) as resp,
                ):
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
            plt.colorbar(im, ax=ax, label="Position Frequency (log scale)")

            # Configure axes
            ax.set_xlabel("X Position")
            ax.set_ylabel("Y Position")
            ax.set_title(self._build_title(riot_id, champion, role))

            # Convert to bytes
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
            buf.seek(0)

            logger.info("Heatmap with map overlay generated successfully", puuid=player_puuid)
            return buf.getvalue()

        finally:
            plt.close(fig)

    async def _get_player_riot_id(self, player_puuid: str) -> str:
        """Fetch the player's Riot ID string for display purposes."""
        player_result = await self._session.execute(
            select(TrackedPlayer.game_name, TrackedPlayer.tag_line).where(
                TrackedPlayer.puuid == player_puuid
            )
        )
        player_row = player_result.first()
        return f"{player_row[0]}#{player_row[1]}" if player_row else player_puuid

    async def _load_positions(
        self,
        player_puuid: str,
        role: str | None,
        champion: str | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Load and normalize player positions with optional filters.

        positions from the red side are mirrored across the anti-diagonal so
        that all games are represented from the bottom-side perspective.
        """

        logger.info(
            "Querying position data for player",
            puuid=player_puuid,
            role=role,
            champion=champion,
        )

        conditions = [TimelineParticipantFrame.puuid == player_puuid]

        if role:
            normalized_role = role.lower()
            conditions.append(func.lower(MatchParticipant.team_position) == normalized_role)

        if champion:
            normalized_champion = champion.lower()
            conditions.append(func.lower(MatchParticipant.champion_name) == normalized_champion)

        result = await self._session.execute(
            select(
                TimelineParticipantFrame.position_x,
                TimelineParticipantFrame.position_y,
                MatchParticipant.team_id,
            )
            .join(
                MatchParticipant,
                (MatchParticipant.match_id == TimelineParticipantFrame.match_id)
                & (MatchParticipant.puuid == TimelineParticipantFrame.puuid),
            )
            .where(*conditions)
        )

        rows = result.fetchall()

        if not rows:
            raise ValueError(f"No position data found for player {player_puuid}")

        mirrored_positions = [self._mirror_position(x, y, team_id) for x, y, team_id in rows]

        x_positions = np.array([pos[0] for pos in mirrored_positions], dtype=np.int32)
        y_positions = np.array([pos[1] for pos in mirrored_positions], dtype=np.int32)

        return x_positions, y_positions

    async def validate_filters(
        self,
        player_puuid: str,
        role: str | None = None,
        champion: str | None = None,
    ) -> None:
        """Validate role and champion filters before querying positions."""

        normalized_role = role.lower() if role else None
        normalized_champion = champion.lower() if champion else None

        if normalized_role and normalized_role not in ALLOWED_ROLES:
            valid_roles = ", ".join(sorted(ALLOWED_ROLES))
            raise ValueError(f"Invalid role '{role}'. Valid roles: {valid_roles}")

        # Validate role usage for this player
        if normalized_role:
            role_result = await self._session.execute(
                select(func.count())
                .select_from(MatchParticipant)
                .where(
                    MatchParticipant.puuid == player_puuid,
                    func.lower(MatchParticipant.team_position) == normalized_role,
                )
            )
            if role_result.scalar_one() == 0:
                raise ValueError(f"No games found for role '{role}' for this player")

        # Validate champion usage for this player
        if normalized_champion:
            champ_result = await self._session.execute(
                select(func.count())
                .select_from(MatchParticipant)
                .where(
                    MatchParticipant.puuid == player_puuid,
                    func.lower(MatchParticipant.champion_name) == normalized_champion,
                )
            )
            if champ_result.scalar_one() == 0:
                raise ValueError(f"Champion '{champion}' not found for this player")

        # Validate combined filter if both provided
        if normalized_role and normalized_champion:
            combo_result = await self._session.execute(
                select(func.count())
                .select_from(MatchParticipant)
                .where(
                    MatchParticipant.puuid == player_puuid,
                    func.lower(MatchParticipant.team_position) == normalized_role,
                    func.lower(MatchParticipant.champion_name) == normalized_champion,
                )
            )
            if combo_result.scalar_one() == 0:
                raise ValueError(
                    f"No games found for champion '{champion}' in role '{role}' for this player"
                )

    @staticmethod
    def _build_title(riot_id: str, champion: str | None, role: str | None) -> str:
        """Build the title for the heatmap based on available information.

        Args:
            riot_id: Player's Riot ID
            champion: Optional champion name filter
            role: Optional role filter

        Returns:
            Formatted title string
        """
        title_parts = ["Player Position Heatmap"]

        # Add champion and role information if available
        filter_info = []
        if champion:
            # Use title case for consistent display formatting
            # Note: For champions with internal capitals (e.g., "LeeSin"),
            # users should provide the name with proper casing
            filter_info.append(champion.title())
        if role:
            filter_info.append(role.upper())

        if filter_info:
            title_parts.append(" - ".join(filter_info))

        title_parts.append(riot_id)

        return "\n".join(title_parts)

    @staticmethod
    def _mirror_position(x: int, y: int, team_id: int) -> tuple[int, int]:
        """Mirror red-side coordinates across the anti-diagonal.

        This transforms top-side (team 200) positions so that the resulting
        heatmap treats every game as if played from the bottom side.
        """

        if team_id == 200:
            return MAP_WIDTH - y, MAP_HEIGHT - x
        return x, y
