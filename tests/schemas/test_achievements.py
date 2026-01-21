"""Tests for Achievement schemas."""

from __future__ import annotations

from lol_data_center.schemas.achievements import (
    AchievementDefinition,
    AchievementResult,
    ConditionType,
    Operator,
)


class TestAchievementDefinition:
    """Tests for AchievementDefinition schema."""

    def test_absolute_condition_definition(self) -> None:
        """Test creating an absolute condition definition."""
        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 10 or more kills",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            message_template="{player_name} got {value} kills!",
        )

        assert definition.id == "high_kills"
        assert definition.condition_type == ConditionType.ABSOLUTE
        assert definition.operator == Operator.GTE
        assert definition.threshold == 10

    def test_personal_max_definition(self) -> None:
        """Test creating a personal max condition definition."""
        definition = AchievementDefinition(
            id="new_kill_record",
            name="New Kill Record",
            description="Set a new personal kill record",
            stat_field="kills",
            condition_type=ConditionType.PERSONAL_MAX,
            message_template="{player_name} set a new record: {value} kills!",
        )

        assert definition.condition_type == ConditionType.PERSONAL_MAX
        assert definition.operator is None
        assert definition.threshold is None

    def test_percentile_definition(self) -> None:
        """Test creating a percentile condition definition."""
        definition = AchievementDefinition(
            id="top_killer",
            name="Top Killer",
            description="Top 5% kills",
            stat_field="kills",
            condition_type=ConditionType.POPULATION_PERCENTILE,
            percentile=95,
            direction="high",
            message_template="{player_name} is in the top 5%!",
        )

        assert definition.percentile == 95
        assert definition.direction == "high"


class TestAchievementResult:
    """Tests for AchievementResult schema."""

    def test_format_message(self) -> None:
        """Test message formatting."""
        definition = AchievementDefinition(
            id="test",
            name="Test Achievement",
            description="Test",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            message_template="{player_name} achieved {achievement_name} with {value} kills!",
        )

        result = AchievementResult(
            achievement=definition,
            triggered=True,
            player_name="TestPlayer#EUW",
            current_value=15,
        )

        message = result.format_message()
        assert "TestPlayer#EUW" in message
        assert "Test Achievement" in message
        assert "15" in message
