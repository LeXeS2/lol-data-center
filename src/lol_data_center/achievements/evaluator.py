"""Achievement evaluator component that listens for new matches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lol_data_center.achievements.conditions import create_condition
from lol_data_center.achievements.definitions import load_achievements
from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.events.event_bus import EventBus, NewMatchEvent, get_event_bus
from lol_data_center.logging_config import get_logger
from lol_data_center.notifications.discord import DiscordNotifier
from lol_data_center.schemas.achievements import AchievementDefinition, AchievementResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AchievementEvaluator:
    """Evaluates achievements for new matches and sends notifications.

    This component subscribes to NewMatchEvent and evaluates all defined
    achievements for each new match.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        notifier: DiscordNotifier | None = None,
        achievements: list[AchievementDefinition] | None = None,
    ) -> None:
        """Initialize the achievement evaluator.

        Args:
            event_bus: Event bus to subscribe to (defaults to global)
            notifier: Discord notifier (creates new one if not provided)
            achievements: Achievement definitions (loads from config if not provided)
        """
        self._event_bus = event_bus or get_event_bus()
        self._notifier = notifier or DiscordNotifier()
        self._achievements = achievements or load_achievements()
        self._subscribed = False

    def subscribe(self) -> None:
        """Subscribe to match events."""
        if self._subscribed:
            return

        self._event_bus.subscribe(NewMatchEvent, self._handle_new_match)
        self._subscribed = True

        logger.info(
            "AchievementEvaluator subscribed to events",
            achievement_count=len(self._achievements),
        )

    def unsubscribe(self) -> None:
        """Unsubscribe from match events."""
        if not self._subscribed:
            return

        self._event_bus.unsubscribe(NewMatchEvent, self._handle_new_match)
        self._subscribed = False

        logger.info("AchievementEvaluator unsubscribed from events")

    async def _handle_new_match(self, event: NewMatchEvent) -> None:
        """Handle a new match event.

        Args:
            event: The new match event
        """
        # Defensive check: Skip evaluation for short games (should already be filtered upstream)
        from lol_data_center.services.filters import is_valid_game_duration

        if not is_valid_game_duration(event.match_data.info.game_duration):
            logger.warning(
                "Skipping achievement evaluation for short game "
                "(should have been filtered earlier)",
                player_name=event.player_name,
                match_id=event.match_id,
                duration_seconds=event.match_data.info.game_duration,
            )
            return

        logger.info(
            "Evaluating achievements for new match",
            player_name=event.player_name,
            match_id=event.match_id,
        )

        triggered_achievements: list[AchievementResult] = []

        async with get_async_session() as session:
            # Get the player from database
            from sqlalchemy import select

            player_result = await session.execute(
                select(TrackedPlayer).where(TrackedPlayer.puuid == event.player_puuid)
            )
            player = player_result.scalar_one_or_none()

            if player is None:
                logger.warning(
                    "Player not found in database",
                    puuid=event.player_puuid,
                )
                return

            # Evaluate each achievement
            for achievement_def in self._achievements:
                try:
                    achievement_result = await self._evaluate_achievement(
                        achievement_def,
                        player,
                        event,
                        session,
                    )

                    if achievement_result.triggered:
                        triggered_achievements.append(achievement_result)

                except Exception as e:
                    logger.error(
                        "Error evaluating achievement",
                        achievement_id=achievement_def.id,
                        error=str(e),
                        exc_info=True,
                    )

        # Send notifications for triggered achievements
        # Deduplicate consecutive achievements - only send the most prestigious one
        achievements_to_notify = self._deduplicate_consecutive_achievements(triggered_achievements)

        for achievement_result in achievements_to_notify:
            try:
                await self._send_notification(achievement_result, event)
            except Exception as e:
                logger.error(
                    "Error sending achievement notification",
                    achievement_id=achievement_result.achievement.id,
                    error=str(e),
                    exc_info=True,
                )

        if triggered_achievements:
            logger.info(
                "Achievements triggered",
                player_name=event.player_name,
                match_id=event.match_id,
                count=len(triggered_achievements),
                achievements=[a.achievement.id for a in triggered_achievements],
            )

    async def _evaluate_achievement(
        self,
        achievement: AchievementDefinition,
        player: TrackedPlayer,
        event: NewMatchEvent,
        session: AsyncSession,
    ) -> AchievementResult:
        """Evaluate a single achievement.

        Args:
            achievement: The achievement definition
            player: The tracked player
            event: The new match event
            session: Database session

        Returns:
            The evaluation result
        """
        condition = create_condition(achievement)
        game_duration = event.match_data.info.game_duration
        return await condition.evaluate(player, event.participant_data, session, game_duration)

    def _deduplicate_consecutive_achievements(
        self,
        triggered_achievements: list[AchievementResult],
    ) -> list[AchievementResult]:
        """Deduplicate consecutive achievements by keeping only the most prestigious.

        When multiple consecutive achievements trigger for the same stat_field and operator
        (e.g., "win 5 games in a row" and "win 7 games in a row"), only the achievement
        with the highest consecutive_count is returned.

        Args:
            triggered_achievements: List of all triggered achievements

        Returns:
            Filtered list with only the most prestigious consecutive achievements
        """
        from lol_data_center.schemas.achievements import ConditionType

        # Separate consecutive achievements from others
        consecutive_achievements: list[AchievementResult] = []
        other_achievements: list[AchievementResult] = []

        for result in triggered_achievements:
            if result.achievement.condition_type == ConditionType.CONSECUTIVE:
                consecutive_achievements.append(result)
            else:
                other_achievements.append(result)

        # If no consecutive achievements, return all
        if not consecutive_achievements:
            return triggered_achievements

        # Group consecutive achievements by (stat_field, operator, threshold)
        # This identifies achievements that are "the same" but with different counts
        from collections import defaultdict

        groups: dict[tuple[str, str, float], list[AchievementResult]] = defaultdict(list)

        for result in consecutive_achievements:
            key = (
                result.achievement.stat_field,
                str(result.achievement.operator),
                result.achievement.threshold or 0.0,
            )
            groups[key].append(result)

        # For each group, keep only the achievement with highest consecutive_count
        best_consecutive: list[AchievementResult] = []
        for group in groups.values():
            if len(group) == 1:
                best_consecutive.append(group[0])
            else:
                # Sort by consecutive_count descending and take the first
                sorted_group = sorted(
                    group,
                    key=lambda x: x.achievement.consecutive_count or 0,
                    reverse=True,
                )
                best_consecutive.append(sorted_group[0])

                # Log that we're deduplicating
                logger.info(
                    "Deduplicating consecutive achievements",
                    kept=sorted_group[0].achievement.id,
                    suppressed=[a.achievement.id for a in sorted_group[1:]],
                )

        # Return non-consecutive + best consecutive
        return other_achievements + best_consecutive

    async def _send_notification(
        self,
        result: AchievementResult,
        event: NewMatchEvent,
    ) -> None:
        """Send a Discord notification for a triggered achievement.

        Args:
            result: The achievement result
            event: The new match event
        """
        message = result.format_message()

        # Add match details
        participant = event.participant_data
        match_info = (
            f"\n\n**Match Details:**\n"
            f"🎮 {participant.champion_name} | "
            f"⚔️ {participant.kills}/{participant.deaths}/{participant.assists} | "
            f"{'✅ Victory' if participant.win else '❌ Defeat'}"
        )

        await self._notifier.send_message(
            message + match_info,
            title=f"🏆 Achievement Unlocked: {result.achievement.name}",
        )

        logger.info(
            "Sent achievement notification",
            achievement_id=result.achievement.id,
            player_name=result.player_name,
        )

    async def close(self) -> None:
        """Clean up resources."""
        self.unsubscribe()
        await self._notifier.close()
