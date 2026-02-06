"""Achievement definition schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class ConditionType(str, Enum):
    """Types of achievement conditions."""

    ABSOLUTE = "absolute"  # Value compared to fixed threshold
    PERSONAL_MAX = "personal_max"  # New personal maximum
    PERSONAL_MIN = "personal_min"  # New personal minimum
    POPULATION_PERCENTILE = "population_percentile"  # Compared to all players
    PLAYER_PERCENTILE = "player_percentile"  # Compared to own history
    CONSECUTIVE = "consecutive"  # Condition met across N consecutive games
    WIN_PROBABILITY = "win_probability"  # Based on predicted win probability vs actual result


class Operator(str, Enum):
    """Comparison operators for absolute conditions."""

    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NE = "!="


class AchievementDefinition(BaseModel):
    """Definition of an achievement."""

    id: str = Field(..., description="Unique identifier for the achievement")
    name: str = Field(..., description="Display name of the achievement")
    description: str = Field(..., description="Description of what triggers the achievement")
    stat_field: str = Field(
        ...,
        description="Field name from MatchParticipant to evaluate (e.g., 'kills', 'deaths')",
    )
    condition_type: ConditionType = Field(..., description="Type of condition to evaluate")

    # For ABSOLUTE conditions
    operator: Operator | None = Field(
        None,
        description="Comparison operator for absolute conditions",
    )
    threshold: float | None = Field(
        None,
        description="Threshold value for absolute conditions",
    )

    # For PERSONAL_MIN conditions
    min_value: float | None = Field(
        None,
        description="Minimum value to consider (e.g., exclude 0 deaths)",
    )

    # For PERCENTILE conditions
    percentile: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentile threshold (e.g., 95 for top 5%)",
    )
    direction: str | None = Field(
        None,
        pattern="^(high|low)$",
        description="Whether high or low values achieve the percentile",
    )

    # For CONSECUTIVE conditions
    consecutive_count: int | None = Field(
        None,
        ge=2,
        description="Number of consecutive games that must meet the condition",
    )

    # Discord message
    message_template: str = Field(
        ...,
        description="Template for Discord message. Supports {player_name}, {achievement_name}, "
        "{value}, {previous_value}, etc.",
    )


class AchievementResult(BaseModel):
    """Result of evaluating an achievement."""

    achievement: AchievementDefinition
    triggered: bool
    player_name: str
    current_value: float
    previous_value: float | None = None
    message: str | None = None

    def format_message(self) -> str:
        """Format the achievement message with values."""
        if self.message:
            return self.message

        try:
            # Use current_value as predicted_win_probability for win_probability achievements
            return self.achievement.message_template.format(
                player_name=self.player_name,
                achievement_name=self.achievement.name,
                value=self.current_value,
                previous_value=self.previous_value or 0,
                predicted_win_probability=self.current_value,
            )
        except (KeyError, ValueError):
            return (
                f"{self.player_name} achieved {self.achievement.name}! Value: {self.current_value}"
            )


class AchievementsConfig(BaseModel):
    """Root configuration for achievements YAML file."""

    achievements: list[AchievementDefinition]
