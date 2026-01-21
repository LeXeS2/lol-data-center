"""Achievement condition implementations."""

from abc import ABC, abstractmethod
from typing import Any

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


class BaseCondition(ABC):
    """Base class for achievement conditions."""

    def __init__(self, definition: AchievementDefinition):
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
    ) -> AchievementResult:
        """Evaluate if the condition is met.

        Args:
            player: The tracked player
            participant: The player's match stats
            session: Database session

        Returns:
            AchievementResult with triggered status and message
        """
        pass

    def _get_stat_value(self, participant: ParticipantDto) -> float:
        """Get the stat value from participant data.

        Args:
            participant: The participant data

        Returns:
            The stat value
        """
        stat_field = self.definition.stat_field

        # Handle special computed fields
        if stat_field == "kda":
            return participant.kda

        # Get attribute from participant
        if hasattr(participant, stat_field):
            value = getattr(participant, stat_field)
            return float(value)

        raise ValueError(f"Unknown stat field: {stat_field}")


class AbsoluteCondition(BaseCondition):
    """Condition that compares a stat to a fixed threshold."""

    async def evaluate(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        session: AsyncSession,
    ) -> AchievementResult:
        """Evaluate if the stat meets the threshold."""
        value = self._get_stat_value(participant)
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
    ) -> AchievementResult:
        """Evaluate if this is a new personal maximum."""
        value = self._get_stat_value(participant)

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
    ) -> AchievementResult:
        """Evaluate if this is a new personal minimum."""
        value = self._get_stat_value(participant)

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
    ) -> AchievementResult:
        """Evaluate if the stat is in the target percentile."""
        value = self._get_stat_value(participant)
        target_percentile = self.definition.percentile
        direction = self.definition.direction

        if target_percentile is None or direction is None:
            raise ValueError(
                f"Population percentile requires percentile and direction: {self.definition.id}"
            )

        # Calculate the percentile rank
        match_service = MatchService(session)
        percentile = await match_service.get_player_stats_percentile(
            stat_field=self.definition.stat_field,
            value=value,
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
    ) -> AchievementResult:
        """Evaluate if the stat is in the target percentile for this player."""
        value = self._get_stat_value(participant)
        target_percentile = self.definition.percentile
        direction = self.definition.direction

        if target_percentile is None or direction is None:
            raise ValueError(
                f"Player percentile requires percentile and direction: {self.definition.id}"
            )

        # Calculate the percentile rank within player's games
        match_service = MatchService(session)
        percentile = await match_service.get_player_stats_percentile(
            stat_field=self.definition.stat_field,
            value=value,
            puuid=player.puuid,
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
    ) -> AchievementResult:
        """Evaluate if the condition is met across N consecutive games."""
        value = self._get_stat_value(participant)
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
            prev_value = self._get_stat_value_from_participant(match_participant)
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

    def _get_stat_value_from_participant(self, participant: MatchParticipant) -> float:
        """Get the stat value from a MatchParticipant database model.

        Args:
            participant: The MatchParticipant model instance

        Returns:
            The stat value
        """
        stat_field = self.definition.stat_field

        # Handle special computed fields
        if stat_field == "kda":
            return participant.kda

        # Get attribute from participant
        if hasattr(participant, stat_field):
            value = getattr(participant, stat_field)
            return float(value)

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
