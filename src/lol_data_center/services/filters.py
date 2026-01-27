"""Match filters and queue ID allowlist."""

from typing import Final

# Allowed queue IDs
# - 400: Draft Pick
# - 420: Ranked Solo/Duo
# - 440: Ranked Flex
# - 480: Swiftplay
ALLOWED_QUEUE_IDS: Final[set[int]] = {400, 420, 440, 480}


def is_allowed_queue(queue_id: int) -> bool:
    """Return True if the given queue_id is allowed for processing."""
    return queue_id in ALLOWED_QUEUE_IDS
