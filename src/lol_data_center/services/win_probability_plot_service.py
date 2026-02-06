"""Service for generating win probability over time plots."""

from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lol_data_center.database.models import (
    Match,
    MatchParticipant,
    MatchTimeline,
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

    def _extract_stats_from_events(
        self,
        events: list[dict[str, object]],
        participant_id: int,
        timestamp_ms: int,
    ) -> dict[str, int | float | bool]:
        """Extract statistics from timeline events up to a given timestamp.

        Args:
            events: List of timeline events
            participant_id: Participant ID to track (1-10)
            timestamp_ms: Only count events up to this timestamp (milliseconds)

        Returns:
            Dictionary of calculated statistics
        """
        stats: dict[str, int | float | bool] = {
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "wards_placed": 0,
            "wards_killed": 0,
            "turret_takedowns": 0,
            "inhibitor_takedowns": 0,
            "baron_kills": 0,
            "dragon_kills": 0,
            "double_kills": 0,
            "triple_kills": 0,
            "quadra_kills": 0,
            "penta_kills": 0,
            "first_blood_kill": False,
            "first_tower_kill": False,
        }

        # Track kill streaks for multi-kills
        recent_kills: list[int] = []  # timestamps of recent kills
        multi_kill_window = 10000  # 10 seconds for multi-kill detection

        first_blood_occurred = False
        first_tower_occurred = False

        for event in events:
            event_timestamp_obj = event.get("timestamp", 0)
            if not isinstance(event_timestamp_obj, int):
                continue
            event_timestamp: int = event_timestamp_obj
            if event_timestamp > timestamp_ms:
                break

            event_type = event.get("type")

            # Champion kills
            if event_type == "CHAMPION_KILL":
                killer_id = event.get("killerId")
                victim_id = event.get("victimId")
                assisting_ids = event.get("assistingParticipantIds", [])

                if killer_id == participant_id:
                    stats["kills"] = int(stats["kills"]) + 1
                    recent_kills.append(event_timestamp)

                    # Check for first blood
                    if not first_blood_occurred:
                        stats["first_blood_kill"] = True
                        first_blood_occurred = True

                    # Clean old kills outside multi-kill window
                    recent_kills = [
                        t for t in recent_kills if event_timestamp - t <= multi_kill_window
                    ]

                    # Count multi-kills
                    kill_count = len(recent_kills)
                    if kill_count >= 5:
                        stats["penta_kills"] = int(stats["penta_kills"]) + 1
                    elif kill_count >= 4:
                        stats["quadra_kills"] = int(stats["quadra_kills"]) + 1
                    elif kill_count >= 3:
                        stats["triple_kills"] = int(stats["triple_kills"]) + 1
                    elif kill_count >= 2:
                        stats["double_kills"] = int(stats["double_kills"]) + 1

                if victim_id == participant_id:
                    stats["deaths"] = int(stats["deaths"]) + 1
                    # Clear recent kills on death
                    recent_kills.clear()

                if isinstance(assisting_ids, list) and participant_id in assisting_ids:
                    stats["assists"] = int(stats["assists"]) + 1

            # Ward placement
            elif event_type == "WARD_PLACED":
                creator_id = event.get("creatorId")
                if creator_id == participant_id:
                    stats["wards_placed"] = int(stats["wards_placed"]) + 1

            # Ward kills
            elif event_type == "WARD_KILL":
                killer_id = event.get("killerId")
                if killer_id == participant_id:
                    stats["wards_killed"] = int(stats["wards_killed"]) + 1

            # Building kills (turrets and inhibitors)
            elif event_type == "BUILDING_KILL":
                killer_id = event.get("killerId")
                building_type = event.get("buildingType")

                if killer_id == participant_id:
                    if building_type == "TURRET":
                        stats["turret_takedowns"] = int(stats["turret_takedowns"]) + 1
                        # Check for first tower
                        if not first_tower_occurred:
                            stats["first_tower_kill"] = True
                            first_tower_occurred = True
                    elif building_type == "INHIBITOR":
                        stats["inhibitor_takedowns"] = int(stats["inhibitor_takedowns"]) + 1

            # Elite monster kills (Baron, Dragon)
            elif event_type == "ELITE_MONSTER_KILL":
                killer_id = event.get("killerId")
                monster_type = event.get("monsterType")

                if killer_id == participant_id:
                    if monster_type == "BARON_NASHOR":
                        stats["baron_kills"] = int(stats["baron_kills"]) + 1
                    elif monster_type == "DRAGON":
                        stats["dragon_kills"] = int(stats["dragon_kills"]) + 1

        # Calculate KDA
        kills = int(stats["kills"])
        deaths = int(stats["deaths"])
        assists = int(stats["assists"])
        if deaths > 0:
            stats["kda"] = (kills + assists) / deaths
        else:
            stats["kda"] = kills + assists

        return stats

    def _extract_features_from_frame(
        self,
        frame: TimelineParticipantFrame,
        game_duration_ms: int,
        event_stats: dict[str, int | float | bool],
    ) -> dict[str, float]:
        """Extract features from a timeline frame for win probability prediction.

        Combines frame data (economy, damage) with event-derived stats (kills, objectives).

        Args:
            frame: Timeline participant frame
            game_duration_ms: Current timestamp in the game (milliseconds)
            event_stats: Statistics extracted from events up to this timestamp

        Returns:
            Dictionary of features for prediction
        """
        game_duration_minutes = game_duration_ms / 60000.0

        # Start with event-derived stats
        features = {
            # KDA from events
            "kills": event_stats.get("kills", 0),
            "deaths": event_stats.get("deaths", 0),
            "assists": event_stats.get("assists", 0),
            "kda": event_stats.get("kda", 0),
            # Game context
            "game_duration_minutes": game_duration_minutes,
            "champion_level": frame.level,
            # Economy (available in frames)
            "gold_per_min": (
                frame.total_gold / game_duration_minutes if game_duration_minutes > 0 else 0
            ),
            "cs_per_min": (
                (frame.minions_killed + frame.jungle_minions_killed) / game_duration_minutes
                if game_duration_minutes > 0
                else 0
            ),
            # Damage (available in frames but nullable)
            "damage_per_min": (
                (frame.total_damage_done_to_champions or 0) / game_duration_minutes
                if game_duration_minutes > 0
                else 0
            ),
            "damage_taken_per_min": (
                (frame.total_damage_taken or 0) / game_duration_minutes
                if game_duration_minutes > 0
                else 0
            ),
            # Vision from events
            "wards_placed": event_stats.get("wards_placed", 0),
            "wards_killed": event_stats.get("wards_killed", 0),
            # Objectives from events
            "turret_takedowns": event_stats.get("turret_takedowns", 0),
            "inhibitor_takedowns": event_stats.get("inhibitor_takedowns", 0),
            "baron_kills": event_stats.get("baron_kills", 0),
            "dragon_kills": event_stats.get("dragon_kills", 0),
            # Multi-kills from events
            "double_kills": event_stats.get("double_kills", 0),
            "triple_kills": event_stats.get("triple_kills", 0),
            "quadra_kills": event_stats.get("quadra_kills", 0),
            "penta_kills": event_stats.get("penta_kills", 0),
            # Early game indicators from events
            "first_blood_kill": int(event_stats.get("first_blood_kill", False)),
            "first_tower_kill": int(event_stats.get("first_tower_kill", False)),
            # Stats not available - use approximations or 0
            "damage_mitigated_per_min": 0,
            "vision_score": event_stats.get("wards_placed", 0) * 1.5,  # Rough approximation
            "vision_score_per_min": (
                (event_stats.get("wards_placed", 0) * 1.5) / game_duration_minutes
                if game_duration_minutes > 0
                else 0
            ),
            "heal_per_min": 0,
            "heals_on_teammates_per_min": 0,
            "shield_on_teammates_per_min": 0,
            "cc_time_dealt": 0,
        }

        return features

    def _extract_notable_events(
        self,
        events: list[dict[str, object]],
        participant_id: int,
    ) -> dict[str, list[tuple[float, str]]]:
        """Extract notable events for visualization on the plot.

        Args:
            events: List of timeline events
            participant_id: Participant ID to track (1-10)

        Returns:
            Dictionary mapping event categories to list of (timestamp_minutes, description) tuples
        """
        notable_events: dict[str, list[tuple[float, str]]] = {
            "kills": [],  # Champion kills by this player
            "deaths": [],  # Player's deaths
            "objectives": [],  # Major objectives (Baron, Dragon, Herald, Turrets, Inhibitors)
            "multikills": [],  # Multi-kills (Double, Triple, Quadra, Penta)
            "milestones": [],  # First Blood, First Tower
        }

        # Track kill timestamps for multi-kill detection
        recent_kills: list[int] = []
        multi_kill_window = 10000  # 10 seconds

        first_blood_occurred = False
        first_tower_occurred = False

        for event in events:
            event_timestamp_obj = event.get("timestamp", 0)
            if not isinstance(event_timestamp_obj, int):
                continue
            event_timestamp: int = event_timestamp_obj
            timestamp_minutes = float(event_timestamp) / 60000.0  # Convert to minutes
            event_type = event.get("type")

            # Champion kills
            if event_type == "CHAMPION_KILL":
                killer_id = event.get("killerId")
                victim_id = event.get("victimId")

                # Player got a kill
                if killer_id == participant_id:
                    notable_events["kills"].append((timestamp_minutes, "Kill"))
                    recent_kills.append(event_timestamp)

                    # Check for first blood
                    if not first_blood_occurred:
                        notable_events["milestones"].append((timestamp_minutes, "First Blood"))
                        first_blood_occurred = True

                    # Clean old kills outside multi-kill window
                    recent_kills = [
                        t for t in recent_kills if event_timestamp - t <= multi_kill_window
                    ]

                    # Check for multi-kills
                    kill_count = len(recent_kills)
                    if kill_count >= 5:
                        notable_events["multikills"].append((timestamp_minutes, "Penta Kill"))
                    elif kill_count == 4:
                        notable_events["multikills"].append((timestamp_minutes, "Quadra Kill"))
                    elif kill_count == 3:
                        notable_events["multikills"].append((timestamp_minutes, "Triple Kill"))
                    elif kill_count == 2:
                        notable_events["multikills"].append((timestamp_minutes, "Double Kill"))

                # Player died
                if victim_id == participant_id:
                    notable_events["deaths"].append((timestamp_minutes, "Death"))
                    # Clear recent kills on death
                    recent_kills.clear()

            # Building kills (turrets and inhibitors)
            elif event_type == "BUILDING_KILL":
                killer_id = event.get("killerId")
                building_type = event.get("buildingType")

                if killer_id == participant_id:
                    if building_type == "TURRET":
                        notable_events["objectives"].append((timestamp_minutes, "Turret"))
                        # Check for first tower
                        if not first_tower_occurred:
                            notable_events["milestones"].append((timestamp_minutes, "First Tower"))
                            first_tower_occurred = True
                    elif building_type == "INHIBITOR":
                        notable_events["objectives"].append((timestamp_minutes, "Inhibitor"))

            # Elite monster kills (Baron, Dragon, Herald)
            elif event_type == "ELITE_MONSTER_KILL":
                killer_id = event.get("killerId")
                monster_type = event.get("monsterType")
                monster_sub_type = event.get("monsterSubType", "")

                if killer_id == participant_id:
                    if monster_type == "BARON_NASHOR":
                        notable_events["objectives"].append((timestamp_minutes, "Baron"))
                    elif monster_type == "DRAGON":
                        # Get dragon type if available
                        dragon_type_suffix = ""
                        if monster_sub_type and isinstance(monster_sub_type, str):
                            dragon_type_suffix = (
                                f" ({monster_sub_type.replace('_DRAGON', '').title()})"
                            )
                        notable_events["objectives"].append(
                            (timestamp_minutes, f"Dragon{dragon_type_suffix}")
                        )
                    elif monster_type == "RIFTHERALD":
                        notable_events["objectives"].append((timestamp_minutes, "Herald"))

        return notable_events

    def _add_event_markers_to_plot(
        self,
        ax: Axes,
        notable_events: dict[str, list[tuple[float, str]]],
        timestamps_minutes: list[float],
        win_probabilities: list[float],
    ) -> None:
        """Add visual markers for notable events to the plot.

        Args:
            ax: Matplotlib axes object
            notable_events: Dictionary of event categories with (timestamp, description) tuples
            timestamps_minutes: List of frame timestamps in minutes
            win_probabilities: List of win probabilities corresponding to timestamps
        """

        # Helper function to interpolate win probability at event time
        def get_win_prob_at_time(event_time: float) -> float:
            """Interpolate win probability at a specific time."""
            if not timestamps_minutes or not win_probabilities:
                return 50.0

            # Find closest frame timestamps
            for i, t in enumerate(timestamps_minutes):
                if t >= event_time:
                    if i == 0:
                        return win_probabilities[0]
                    # Linear interpolation between frames
                    t_prev = timestamps_minutes[i - 1]
                    prob_prev = win_probabilities[i - 1]
                    prob_curr = win_probabilities[i]
                    # Use epsilon for floating-point comparison
                    time_diff = t - t_prev
                    if abs(time_diff) > 1e-6:  # Epsilon for numerical stability
                        ratio = (event_time - t_prev) / time_diff
                        return prob_prev + ratio * (prob_curr - prob_prev)
                    return prob_prev

            # Event is after last frame
            return win_probabilities[-1] if win_probabilities else 50.0

        # Event type configurations: (marker, color, size, label)
        event_configs = {
            "kills": ("^", "#2ecc71", 80, "Kills"),  # Green up triangle
            "deaths": ("v", "#e74c3c", 80, "Deaths"),  # Red down triangle
            "objectives": ("*", "#f39c12", 120, "Objectives"),  # Orange star
            "multikills": ("P", "#9b59b6", 100, "Multi-kills"),  # Purple plus
            "milestones": ("D", "#3498db", 100, "Milestones"),  # Blue diamond
        }

        # Plot markers for each event category
        handles = []
        for event_type, (marker, color, size, label) in event_configs.items():
            events = notable_events.get(event_type, [])
            if not events:
                continue

            # Extract times and get corresponding probabilities
            event_times = [e[0] for e in events]
            event_probs = [get_win_prob_at_time(t) for t in event_times]

            # Plot markers
            scatter = ax.scatter(
                event_times,
                event_probs,
                marker=marker,
                s=size,
                color=color,
                edgecolors="black",
                linewidths=0.5,
                alpha=0.8,
                zorder=5,  # Draw on top of the line
                label=label,
            )
            handles.append(scatter)

        # Add legend if there are any events
        if handles:
            ax.legend(
                handles=handles,
                loc="upper left",
                framealpha=0.9,
                fontsize=9,
                ncol=2,
            )

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

        # Get timeline events
        timeline_result = await self._session.execute(
            select(MatchTimeline).where(MatchTimeline.match_id == match_id)
        )
        timeline = timeline_result.scalar_one_or_none()

        if not timeline:
            raise ValueError(f"No timeline found for match {match_id}")

        # Extract events list from JSON
        events_data = timeline.events.get("events", [])
        # Type assertion: events should be a list of dictionaries
        if not isinstance(events_data, list):
            raise ValueError(f"Invalid timeline events format for match {match_id}")
        events: list[dict[str, object]] = events_data

        # Get participant_id for this player
        participant_id = frames[0].participant_id if frames else None
        if not participant_id:
            raise ValueError(f"Could not determine participant_id for player {puuid}")

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

            # Extract stats from events up to this timestamp
            event_stats = self._extract_stats_from_events(events, participant_id, frame.timestamp)

            # Extract features combining frame data and event stats
            features = self._extract_features_from_frame(frame, frame.timestamp, event_stats)

            # Predict win probability
            try:
                prediction = predictor.predict_win_probability(features)
                # Convert to percentage
                win_probabilities.append(prediction["win_probability"] * 100)
            except Exception as e:
                logger.warning(
                    "Failed to predict win probability for frame",
                    timestamp=frame.timestamp,
                    error=str(e),
                )
                # Use 50% as fallback
                win_probabilities.append(50.0)

        # Extract notable events for visualization
        notable_events = self._extract_notable_events(events, participant_id)

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
            zorder=3,
        )

        # Add event markers to the plot
        self._add_event_markers_to_plot(ax, notable_events, timestamps_minutes, win_probabilities)

        # Formatting
        ax.set_xlabel("Game Time (minutes)", fontsize=12)
        ax.set_ylabel("Win Probability (%)", fontsize=12)
        ax.set_title(
            "Win Probability Over Time with Notable Events", fontsize=14, fontweight="bold"
        )
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
