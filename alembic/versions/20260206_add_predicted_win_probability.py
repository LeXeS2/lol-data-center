"""Add predicted_win_probability to match_participants.

Revision ID: 20260206_win_prob
Revises: 20260128_rank_history
Create Date: 2026-02-06 10:44:11.544000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260206_win_prob"
down_revision: str | None = "20260128_rank_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add predicted_win_probability column to match_participants table."""
    op.add_column(
        "match_participants",
        sa.Column("predicted_win_probability", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove predicted_win_probability column from match_participants table."""
    op.drop_column("match_participants", "predicted_win_probability")
