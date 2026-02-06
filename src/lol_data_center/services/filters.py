"""Match filters and queue ID allowlist."""

from typing import Final

# Allowed queue IDs
# - 400: Draft Pick
# - 420: Ranked Solo/Duo
# - 440: Ranked Flex
# - 480: Swiftplay
ALLOWED_QUEUE_IDS: Final[set[int]] = {400, 420, 440, 480}

# Minimum game duration in seconds for a game to be considered legitimate.
# Games shorter than this are typically remakes, early disconnects, or other invalid matches.
#
# Rationale:
# - Riot API does not provide an explicit "remake" flag
# - Standard remakes occur at 3 minutes if a player is AFK/DC
# - Early surrenders can happen at 15 minutes (unanimous) or 20 minutes
# - A 10-minute threshold (600 seconds) safely excludes remakes and very early game issues
#   while preserving legitimate short games (e.g., one-sided stomps, early surrenders)
# - This is a common industry standard for filtering League of Legends match data
MINIMUM_GAME_DURATION_SECONDS: Final[int] = 600  # 10 minutes


def is_allowed_queue(queue_id: int) -> bool:
    """Return True if the given queue_id is allowed for processing."""
    return queue_id in ALLOWED_QUEUE_IDS


def is_valid_game_duration(duration_seconds: int) -> bool:
    """Return True if the game duration indicates a legitimate match.

    Args:
        duration_seconds: Game duration in seconds

    Returns:
        True if the game is long enough to be considered legitimate,
        False for remakes, early disconnects, or invalid matches

    Note:
        Games shorter than 10 minutes (600 seconds) are excluded as they are
        typically remakes or invalid matches. This prevents data skew in
        achievement evaluation and ensures statistical integrity.
    """
    return duration_seconds >= MINIMUM_GAME_DURATION_SECONDS
