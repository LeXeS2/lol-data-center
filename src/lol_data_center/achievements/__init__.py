"""Achievements package."""

from lol_data_center.achievements.conditions import (
    AbsoluteCondition,
    BaseCondition,
    PersonalMaxCondition,
    PersonalMinCondition,
    PlayerPercentileCondition,
    PopulationPercentileCondition,
)
from lol_data_center.achievements.definitions import load_achievements
from lol_data_center.achievements.evaluator import AchievementEvaluator

__all__ = [
    "AbsoluteCondition",
    "AchievementEvaluator",
    "BaseCondition",
    "PersonalMaxCondition",
    "PersonalMinCondition",
    "PlayerPercentileCondition",
    "PopulationPercentileCondition",
    "load_achievements",
]
