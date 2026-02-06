"""Service for generating win probability over time plots."""

from io import BytesIO
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lol_data_center.database.models import (
    Match,
    MatchParticipant,
    TimelineParticipantFrame,
)
from lol_data_center.logging_config import get_logger
from lol_data_center.ml.win_probability import WinProbabilityPredictor

# Use non-interactive backend for server environments
matplotlib.use("Agg")

logger = get_logger(__name__)


class WinProbabilityPlotService:
    """Service for generating win probability plots from timeline data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self._session = session

    async def get_player_nth_last_match(
        self, puuid: str, n: int = 1
    ) -> tuple[Match, MatchParticipant] | None:
        """Get the nth last match for a player (1 = most recent).

        Args:
            puuid: Player's PUUID
            n: Which match to get (1 = most recent, 2 = second most recent, etc.)

        Returns:
            Tuple of (Match, MatchParticipant) or None if not found
        """
        if n < 1:
            raise ValueError("n must be >= 1")

        # Get recent match participations
        result = await self._session.execute(
            select(MatchParticipant)
            .options(selectinload(MatchParticipant.match))
            .where(MatchParticipant.puuid == puuid)
            .order_by(MatchParticipant.game_creation.desc())
            .limit(n)
        )
        participants = list(result.scalars().all())

        if len(participants) < n:
            return None

        participant = participants[n - 1]
        return (participant.match, participant)

    def _extract_features_from_frame(
        self, frame: TimelineParticipantFrame, game_duration_ms: int
    ) -> dict[str, float]:
        """Extract features from a timeline frame for win probability prediction.

        Note: This is a simplified version that uses available timeline data.
        The full model expects end-of-game statistics which are not available
        in timeline frames, so we use approximations.

        Args:
            frame: Timeline participant frame
            game_duration_ms: Current timestamp in the game (milliseconds)

        Returns:
            Dictionary of features for prediction
        """
        game_duration_minutes = game_duration_ms / 60000.0

        # Approximate features from timeline data
        # Many end-game stats like kills, deaths, etc. are not available in frames
        # We use what we have and set others to 0
        features = {
            # Game context
            "game_duration_minutes": game_duration_minutes,
            "champion_level": frame.level,
            # Economy (available in frames)
            "gold_per_min": frame.total_gold / game_duration_minutes if game_duration_minutes > 0 else 0,
            "cs_per_min": (frame.minions_killed + frame.jungle_minions_killed) / game_duration_minutes
            if game_duration_minutes > 0
            else 0,
            # Damage (available in frames but nullable)
            "damage_per_min": (frame.total_damage_done_to_champions or 0) / game_duration_minutes
            if game_duration_minutes > 0
            else 0,
            "damage_taken_per_min": (frame.total_damage_taken or 0) / game_duration_minutes
            if game_duration_minutes > 0
            else 0,
            # Stats not available in timeline frames - set to 0
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "kda": 0,
            "damage_mitigated_per_min": 0,
            "vision_score": 0,
            "vision_score_per_min": 0,
            "wards_placed": 0,
            "wards_killed": 0,
            "turret_takedowns": 0,
            "inhibitor_takedowns": 0,
            "baron_kills": 0,
            "dragon_kills": 0,
            "heal_per_min": 0,
            "heals_on_teammates_per_min": 0,
            "shield_on_teammates_per_min": 0,
            "cc_time_dealt": 0,
            "double_kills": 0,
            "triple_kills": 0,
            "quadra_kills": 0,
            "penta_kills": 0,
            "first_blood_kill": 0,
            "first_tower_kill": 0,
        }

        return features

    async def generate_win_probability_plot(
        self,
        match_id: str,
        puuid: str,
        predictor: WinProbabilityPredictor | None = None,
    ) -> BytesIO:
        """Generate a win probability plot for a player's match.

        Args:
            match_id: Match ID
            puuid: Player's PUUID
            predictor: Optional WinProbabilityPredictor instance

        Returns:
            BytesIO buffer containing the PNG image

        Raises:
            ValueError: If no timeline data found or predictor not available
        """
        # Get participant frames for this player in this match
        result = await self._session.execute(
            select(TimelineParticipantFrame)
            .where(
                TimelineParticipantFrame.match_id == match_id,
                TimelineParticipantFrame.puuid == puuid,
            )
            .order_by(TimelineParticipantFrame.timestamp)
        )
        frames = list(result.scalars().all())

        if not frames:
            raise ValueError(f"No timeline data found for match {match_id} and player {puuid}")

        # Check if predictor is available
        if predictor is None or predictor.model is None:
            raise ValueError(
                "Win probability model not available. "
                "Please train a model first using the ML notebook."
            )

        # Calculate win probability for each frame
        timestamps_minutes = []
        win_probabilities = []

        for frame in frames:
            timestamp_minutes = frame.timestamp / 60000.0  # Convert ms to minutes
            timestamps_minutes.append(timestamp_minutes)

            # Extract features
            features = self._extract_features_from_frame(frame, frame.timestamp)

            # Predict win probability
            try:
                prediction = predictor.predict_win_probability(features)
                win_probabilities.append(prediction["win_probability"] * 100)  # Convert to percentage
            except Exception as e:
                logger.warning(
                    "Failed to predict win probability for frame",
                    timestamp=frame.timestamp,
                    error=str(e),
                )
                # Use 50% as fallback
                win_probabilities.append(50.0)

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot win probability over time
        ax.plot(
            timestamps_minutes,
            win_probabilities,
            marker="o",
            linestyle="-",
            linewidth=2,
            markersize=4,
            color="#1f77b4",
        )

        # Formatting
        ax.set_xlabel("Game Time (minutes)", fontsize=12)
        ax.set_ylabel("Win Probability (%)", fontsize=12)
        ax.set_title("Win Probability Over Time", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)

        # Set y-axis limits
        ax.set_ylim(0, 100)

        # Add horizontal line at 50%
        ax.axhline(y=50, color="gray", linestyle="--", alpha=0.5, linewidth=1)

        # Add annotation for final probability
        if win_probabilities:
            final_prob = win_probabilities[-1]
            ax.annotate(
                f"{final_prob:.1f}%",
                xy=(timestamps_minutes[-1], final_prob),
                xytext=(10, 10),
                textcoords="offset points",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "yellow", "alpha": 0.7},
                arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0"},
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
            "Generated win probability plot",
            match_id=match_id,
            puuid=puuid,
            data_points=len(frames),
        )

        return buffer
