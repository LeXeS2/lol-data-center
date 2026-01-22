"""Achievement definition loading from YAML configuration."""

from pathlib import Path

import yaml

from lol_data_center.config import get_settings
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.achievements import AchievementDefinition, AchievementsConfig

logger = get_logger(__name__)


def load_achievements(config_path: Path | None = None) -> list[AchievementDefinition]:
    """Load achievement definitions from YAML file.

    Args:
        config_path: Path to achievements config file (defaults to settings)

    Returns:
        List of achievement definitions
    """
    if config_path is None:
        settings = get_settings()
        config_path = settings.achievements_config_path

    if not config_path.exists():
        logger.warning(
            "Achievements config file not found",
            path=str(config_path),
        )
        return []

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = AchievementsConfig.model_validate(data)

        logger.info(
            "Loaded achievements",
            count=len(config.achievements),
            path=str(config_path),
        )

        return config.achievements

    except yaml.YAMLError as e:
        logger.error(
            "Failed to parse achievements YAML",
            path=str(config_path),
            error=str(e),
        )
        raise

    except Exception as e:
        logger.error(
            "Failed to load achievements",
            path=str(config_path),
            error=str(e),
        )
        raise


def get_achievement_by_id(
    achievement_id: str,
    achievements: list[AchievementDefinition] | None = None,
) -> AchievementDefinition | None:
    """Get an achievement by its ID.

    Args:
        achievement_id: The achievement ID
        achievements: List of achievements (loads from config if not provided)

    Returns:
        The achievement definition or None
    """
    if achievements is None:
        achievements = load_achievements()

    for achievement in achievements:
        if achievement.id == achievement_id:
            return achievement

    return None
