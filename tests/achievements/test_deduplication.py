"""Tests for achievement deduplication in evaluator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lol_data_center.achievements.evaluator import AchievementEvaluator
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.schemas.achievements import (
    AchievementDefinition,
    AchievementResult,
    ConditionType,
    Operator,
)


class TestAchievementDeduplication:
    """Tests for consecutive achievement deduplication."""

    def test_deduplicate_no_consecutive(self):
        """Test that non-consecutive achievements are not affected."""
        evaluator = AchievementEvaluator(achievements=[])

        results = [
            AchievementResult(
                achievement=AchievementDefinition(
                    id="high_kills",
                    name="High Kills",
                    description="10+ kills",
                    stat_field="kills",
                    condition_type=ConditionType.ABSOLUTE,
                    operator=Operator.GTE,
                    threshold=10,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=12,
            ),
            AchievementResult(
                achievement=AchievementDefinition(
                    id="new_record",
                    name="New Record",
                    description="Personal best",
                    stat_field="kills",
                    condition_type=ConditionType.PERSONAL_MAX,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=12,
            ),
        ]

        deduplicated = evaluator._deduplicate_consecutive_achievements(results)

        # All results should be returned
        assert len(deduplicated) == 2

    def test_deduplicate_single_consecutive(self):
        """Test that a single consecutive achievement is returned unchanged."""
        evaluator = AchievementEvaluator(achievements=[])

        results = [
            AchievementResult(
                achievement=AchievementDefinition(
                    id="triple_win",
                    name="Triple Win",
                    description="3 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
        ]

        deduplicated = evaluator._deduplicate_consecutive_achievements(results)

        assert len(deduplicated) == 1
        assert deduplicated[0].achievement.id == "triple_win"

    def test_deduplicate_multiple_different_consecutive(self):
        """Test that different consecutive achievements are kept."""
        evaluator = AchievementEvaluator(achievements=[])

        results = [
            AchievementResult(
                achievement=AchievementDefinition(
                    id="triple_win",
                    name="Triple Win",
                    description="3 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
            AchievementResult(
                achievement=AchievementDefinition(
                    id="kda_streak",
                    name="KDA Streak",
                    description="High KDA",
                    stat_field="kda",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.GTE,
                    threshold=5.0,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=6.0,
            ),
        ]

        deduplicated = evaluator._deduplicate_consecutive_achievements(results)

        # Both should be kept since they're for different stats
        assert len(deduplicated) == 2

    def test_deduplicate_overlapping_consecutive(self):
        """Test that overlapping consecutive achievements keep only the highest count."""
        evaluator = AchievementEvaluator(achievements=[])

        # Create overlapping win streak achievements
        results = [
            AchievementResult(
                achievement=AchievementDefinition(
                    id="triple_win",
                    name="Triple Win",
                    description="3 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
            AchievementResult(
                achievement=AchievementDefinition(
                    id="five_win",
                    name="Five Win",
                    description="5 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=5,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
            AchievementResult(
                achievement=AchievementDefinition(
                    id="seven_win",
                    name="Seven Win",
                    description="7 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=7,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
        ]

        deduplicated = evaluator._deduplicate_consecutive_achievements(results)

        # Only the highest count (7) should be kept
        assert len(deduplicated) == 1
        assert deduplicated[0].achievement.id == "seven_win"
        assert deduplicated[0].achievement.consecutive_count == 7

    def test_deduplicate_mixed_achievements(self):
        """Test deduplication with both consecutive and non-consecutive achievements."""
        evaluator = AchievementEvaluator(achievements=[])

        results = [
            # Non-consecutive achievement
            AchievementResult(
                achievement=AchievementDefinition(
                    id="high_kills",
                    name="High Kills",
                    description="10+ kills",
                    stat_field="kills",
                    condition_type=ConditionType.ABSOLUTE,
                    operator=Operator.GTE,
                    threshold=10,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=12,
            ),
            # Overlapping consecutive achievements
            AchievementResult(
                achievement=AchievementDefinition(
                    id="triple_win",
                    name="Triple Win",
                    description="3 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
            AchievementResult(
                achievement=AchievementDefinition(
                    id="five_win",
                    name="Five Win",
                    description="5 wins",
                    stat_field="win",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.EQ,
                    threshold=1,
                    consecutive_count=5,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=1,
            ),
            # Different consecutive achievement
            AchievementResult(
                achievement=AchievementDefinition(
                    id="kda_streak",
                    name="KDA Streak",
                    description="High KDA",
                    stat_field="kda",
                    condition_type=ConditionType.CONSECUTIVE,
                    operator=Operator.GTE,
                    threshold=5.0,
                    consecutive_count=3,
                    message_template="test",
                ),
                triggered=True,
                player_name="TestPlayer#EUW",
                current_value=6.0,
            ),
        ]

        deduplicated = evaluator._deduplicate_consecutive_achievements(results)

        # Should have: high_kills, five_win (not triple_win), kda_streak
        assert len(deduplicated) == 3

        achievement_ids = [r.achievement.id for r in deduplicated]
        assert "high_kills" in achievement_ids
        assert "five_win" in achievement_ids
        assert "kda_streak" in achievement_ids
        assert "triple_win" not in achievement_ids
