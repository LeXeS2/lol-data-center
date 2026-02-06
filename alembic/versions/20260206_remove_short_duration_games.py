"""Remove short duration games (remakes and early disconnects).

Revision ID: 20260206_remove_short_games
Revises: 20260128_rank_history
Create Date: 2026-02-06 13:35:00.000000

This migration deletes matches with duration < 600 seconds (10 minutes).
Such games are typically remakes, early disconnects, or otherwise invalid matches.

Rationale:
- Riot API does not provide an explicit "remake" flag
- Games shorter than 10 minutes skew statistics and achievement evaluation
- Common industry standard for filtering League of Legends match data
- Preserves legitimate short games while excluding remakes and early issues

The deletion cascades to related tables (match_participants, timeline data)
due to foreign key constraints with CASCADE DELETE.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260206_remove_short_games"
down_revision: str | None = "20260128_rank_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Minimum duration threshold in seconds (10 minutes)
MINIMUM_GAME_DURATION_SECONDS = 600


def upgrade() -> None:
    """Delete matches with duration less than 10 minutes.

    This removes illegitimate games (remakes, early disconnects) from the database.
    The CASCADE DELETE constraint automatically removes related records in:
    - match_participants
    - match_timeline_events
    - match_timeline_frames
    - player_records (via match_id reference)
    """
    # Use raw SQL for efficiency and clarity
    op.execute(
        f"""
        DELETE FROM matches
        WHERE game_duration < {MINIMUM_GAME_DURATION_SECONDS}
        """
    )


def downgrade() -> None:
    """No downgrade path - deleted data cannot be recovered.

    If you need to restore this data, you must re-fetch it from Riot API
    using the backfill functionality.
    """
    # Cannot restore deleted data
    pass
