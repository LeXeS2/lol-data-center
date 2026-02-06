"""Achievement condition implementations."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import MatchParticipant, PlayerRecord, TrackedPlayer
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.achievements import (
    AchievementDefinition,
    AchievementResult,
    ConditionType,
    Operator,
)
from lol_data_center.schemas.riot_api import ParticipantDto
from lol_data_center.services.match_service import MatchService

logger = get_logger(__name__)

# Baseline duration for achievement normalization (30 minutes in seconds)
# Most ranked games last approximately 25-35 minutes, making 30 minutes a representative baseline
BASELINE_DURATION_SECONDS = 1800


class BaseCondition(ABC):
    """Base class for achievement conditions."""

    def __init__(self, definition: AchievementDefinition) -> None:
        """Initialize with achievement definition.

        Args:
            definition: The achievement definition
        """
        self.definition = definition

    @abstractmethod
    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if the condition is met.

        Args:
            player: The tracked player
            participant: The player's match stats
            session: Database session
            game_duration: Game duration in seconds

        Returns:
            AchievementResult with triggered status and message
        """
        pass

    def _get_stat_value(self, participant: ParticipantDto, game_duration: int) -> float:
        """Get the stat value from participant data.

        Args:
            participant: The participant data
            game_duration: Game duration in seconds

        Returns:
            The stat value, normalized by game duration if configured
        """
        stat_field = self.definition.stat_field

        # Handle special computed fields
        if stat_field == "kda":
            return participant.kda

        # Get attribute from participant
        if hasattr(participant, stat_field):
            value = getattr(participant, stat_field)
            raw_value = float(value)

            # Apply duration normalization if enabled
            if self.definition.normalize_by_duration:
                return self._normalize_to_30_minutes(raw_value, game_duration)

            return raw_value

        raise ValueError(f"Unknown stat field: {stat_field}")

    def _normalize_to_30_minutes(self, value: float, game_duration: int) -> float:
        """Normalize a stat value to a 30-minute game baseline.

        The 30-minute baseline was chosen because:
        - Most ranked games last approximately 25-35 minutes
        - It represents a typical game duration in League of Legends
        - Achievement thresholds are designed around this duration

        Args:
            value: The raw stat value
            game_duration: Game duration in seconds

        Returns:
            The normalized value as if the game lasted 30 minutes
        """
        # Avoid division by zero
        if game_duration <= 0:
            return value

        # Normalize: (value / actual_duration) * baseline_duration
        return (value / game_duration) * BASELINE_DURATION_SECONDS


class AbsoluteCondition(BaseCondition):
    """Condition that compares a stat to a fixed threshold."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if the stat meets the threshold."""
        value = self._get_stat_value(participant, game_duration)
        threshold = self.definition.threshold
        operator = self.definition.operator

        if threshold is None or operator is None:
            raise ValueError(
                f"Absolute condition requires threshold and operator: {self.definition.id}"
            )

        # Evaluate the condition
        triggered = self._compare(value, operator, threshold)

        return AchievementResult(
            achievement=self.definition,
            triggered=triggered,
            player_name=player.riot_id,
            current_value=value,
        )

    def _compare(self, value: float, operator: Operator, threshold: float) -> bool:
        """Compare value against threshold using operator."""
        match operator:
            case Operator.GT:
                return value > threshold
            case Operator.GTE:
                return value >= threshold
            case Operator.LT:
                return value < threshold
            case Operator.LTE:
                return value <= threshold
            case Operator.EQ:
                return value == threshold
            case Operator.NE:
                return value != threshold


class PersonalMaxCondition(BaseCondition):
    """Condition that checks for a new personal maximum."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if this is a new personal maximum."""
        value = self._get_stat_value(participant, game_duration)

        # Get the record field name for this stat
        record_field = self._get_record_field()
        if record_field is None:
            logger.warning(
                "No record field for stat",
                stat_field=self.definition.stat_field,
                achievement_id=self.definition.id,
            )
            return AchievementResult(
                achievement=self.definition,
                triggered=False,
                player_name=player.riot_id,
                current_value=value,
            )

        # Get player's records
        from sqlalchemy import select

        result = await session.execute(
            select(PlayerRecord).where(PlayerRecord.player_id == player.id)
        )
        records = result.scalar_one_or_none()

        previous_value = 0.0
        if records:
            previous_value = float(getattr(records, record_field, 0) or 0)

        # Check if this is a new maximum
        triggered = value > previous_value

        return AchievementResult(
            achievement=self.definition,
            triggered=triggered,
            player_name=player.riot_id,
            current_value=value,
            previous_value=previous_value,
        )

    def _get_record_field(self) -> str | None:
        """Map stat field to player record field."""
        mapping = {
            "kills": "max_kills",
            "deaths": "max_deaths",
            "assists": "max_assists",
            "kda": "max_kda",
            "total_minions_killed": "max_cs",
            "total_damage_dealt_to_champions": "max_damage_to_champions",
            "vision_score": "max_vision_score",
            "gold_earned": "max_gold",
        }
        return mapping.get(self.definition.stat_field)


class PersonalMinCondition(BaseCondition):
    """Condition that checks for a new personal minimum."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if this is a new personal minimum."""
        value = self._get_stat_value(participant, game_duration)

        # Check minimum value threshold
        min_value = self.definition.min_value
        if min_value is not None and value < min_value:
            return AchievementResult(
                achievement=self.definition,
                triggered=False,
                player_name=player.riot_id,
                current_value=value,
            )

        # Get the record field name for this stat
        record_field = self._get_record_field()
        if record_field is None:
            return AchievementResult(
                achievement=self.definition,
                triggered=False,
                player_name=player.riot_id,
                current_value=value,
            )

        # Get player's records
        from sqlalchemy import select

        result = await session.execute(
            select(PlayerRecord).where(PlayerRecord.player_id == player.id)
        )
        records = result.scalar_one_or_none()

        previous_value: float | None = None
        if records:
            previous_value = getattr(records, record_field, None)

        # Check if this is a new minimum
        triggered = previous_value is None or value < previous_value

        return AchievementResult(
            achievement=self.definition,
            triggered=triggered,
            player_name=player.riot_id,
            current_value=value,
            previous_value=previous_value,
        )

    def _get_record_field(self) -> str | None:
        """Map stat field to player record field."""
        mapping = {
            "deaths": "min_deaths",
        }
        return mapping.get(self.definition.stat_field)


class PopulationPercentileCondition(BaseCondition):
    """Condition that checks if stat is in top/bottom X% of all players."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if the stat is in the target percentile."""
        value = self._get_stat_value(participant, game_duration)
        target_percentile = self.definition.percentile
        direction = self.definition.direction

        if target_percentile is None or direction is None:
            raise ValueError(
                f"Population percentile requires percentile and direction: {self.definition.id}"
            )

        # Calculate the percentile rank, filtered by champion and role for fairer comparison
        match_service = MatchService(session)
        percentile = await match_service.get_player_stats_percentile(
            stat_field=self.definition.stat_field,
            value=value,
            champion_id=participant.champion_id,
            role=participant.individual_position,
        )

        # Check if condition is met
        if direction == "high":
            # High values are good - check if in top X%
            triggered = percentile >= target_percentile
        else:
            # Low values are good - check if in bottom X%
            triggered = percentile <= (100 - target_percentile)

        return AchievementResult(
            achievement=self.definition,
            triggered=triggered,
            player_name=player.riot_id,
            current_value=value,
        )


class PlayerPercentileCondition(BaseCondition):
    """Condition that checks if stat is in top/bottom X% of player's own games."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if the stat is in the target percentile for this player."""
        value = self._get_stat_value(participant, game_duration)
        target_percentile = self.definition.percentile
        direction = self.definition.direction

        if target_percentile is None or direction is None:
            raise ValueError(
                f"Player percentile requires percentile and direction: {self.definition.id}"
            )

        # Calculate the percentile rank within player's games, filtered by champion and role
        match_service = MatchService(session)
        percentile = await match_service.get_player_stats_percentile(
            stat_field=self.definition.stat_field,
            value=value,
            puuid=player.puuid,
            champion_id=participant.champion_id,
            role=participant.individual_position,
        )

        # Check if condition is met
        if direction == "high":
            triggered = percentile >= target_percentile
        else:
            triggered = percentile <= (100 - target_percentile)

        return AchievementResult(
            achievement=self.definition,
            triggered=triggered,
            player_name=player.riot_id,
            current_value=value,
        )


class ConsecutiveCondition(BaseCondition):
    """Condition that checks if a condition is met across N consecutive games."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
        game_duration: int,
    ) -> AchievementResult:
        """Evaluate if the condition is met across N consecutive games."""
        value = self._get_stat_value(participant, game_duration)
        consecutive_count = self.definition.consecutive_count
        threshold = self.definition.threshold
        operator = self.definition.operator

        if consecutive_count is None or consecutive_count < 2:
            raise ValueError(
                f"Consecutive condition requires consecutive_count >= 2: {self.definition.id}"
            )

        if threshold is None or operator is None:
            raise ValueError(
                f"Consecutive condition requires threshold and operator: {self.definition.id}"
            )

        # Check if current game meets the condition
        if not self._compare(value, operator, threshold):
            return AchievementResult(
                achievement=self.definition,
                triggered=False,
                player_name=player.riot_id,
                current_value=value,
            )

        # Query the last N-1 games for this player
        match_service = MatchService(session)
        recent_matches = await match_service.get_recent_matches_for_player(
            puuid=player.puuid,
            limit=consecutive_count - 1,
        )

        # Need exactly N-1 previous games
        if len(recent_matches) < consecutive_count - 1:
            return AchievementResult(
                achievement=self.definition,
                triggered=False,
                player_name=player.riot_id,
                current_value=value,
            )

        # Check if all previous N-1 games also meet the condition
        for match_participant in recent_matches:
            # Get game duration from the match relationship
            match_duration = match_participant.match.game_duration
            prev_value = self._get_stat_value_from_participant(match_participant, match_duration)
            if not self._compare(prev_value, operator, threshold):
                return AchievementResult(
                    achievement=self.definition,
                    triggered=False,
                    player_name=player.riot_id,
                    current_value=value,
                )

        # All N games meet the condition
        return AchievementResult(
            achievement=self.definition,
            triggered=True,
            player_name=player.riot_id,
            current_value=value,
        )

    def _get_stat_value_from_participant(
        self, participant: MatchParticipant, game_duration: int
    ) -> float:
        """Get the stat value from a MatchParticipant database model.

        Args:
            participant: The MatchParticipant model instance
            game_duration: Game duration in seconds

        Returns:
            The stat value, normalized by game duration if configured
        """
        stat_field = self.definition.stat_field

        # Handle special computed fields
        if stat_field == "kda":
            return participant.kda

        # Get attribute from participant
        if hasattr(participant, stat_field):
            value = getattr(participant, stat_field)
            raw_value = float(value)

            # Apply duration normalization if enabled
            if self.definition.normalize_by_duration:
                return self._normalize_to_30_minutes(raw_value, game_duration)

            return raw_value

        raise ValueError(f"Unknown stat field: {stat_field}")

    def _compare(self, value: float, operator: Operator, threshold: float) -> bool:
        """Compare value against threshold using operator."""
        match operator:
            case Operator.GT:
                return value > threshold
            case Operator.GTE:
                return value >= threshold
            case Operator.LT:
                return value < threshold
            case Operator.LTE:
                return value <= threshold
            case Operator.EQ:
                return value == threshold
            case Operator.NE:
                return value != threshold


def create_condition(definition: AchievementDefinition) -> BaseCondition:
    """Factory function to create the appropriate condition.

    Args:
        definition: The achievement definition

    Returns:
        The appropriate condition instance
    """
    match definition.condition_type:
        case ConditionType.ABSOLUTE:
            return AbsoluteCondition(definition)
        case ConditionType.PERSONAL_MAX:
            return PersonalMaxCondition(definition)
        case ConditionType.PERSONAL_MIN:
            return PersonalMinCondition(definition)
        case ConditionType.POPULATION_PERCENTILE:
            return PopulationPercentileCondition(definition)
        case ConditionType.PLAYER_PERCENTILE:
            return PlayerPercentileCondition(definition)
        case ConditionType.CONSECUTIVE:
            return ConsecutiveCondition(definition)
        case _:
            raise ValueError(f"Unknown condition type: {definition.condition_type}")
