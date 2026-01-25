"""Add timezone to datetime columns.

Revision ID: 20260125_timezone_aware_datetimes
Revises: 20260125_discord_registrations
Create Date: 2026-01-25 17:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260125_tz_aware"
down_revision = "20260125_discord_registrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema to use TIMESTAMP WITH TIME ZONE for all datetime columns."""
    # Alter tracked_players table
    op.alter_column(
        "tracked_players",
        "last_polled_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        nullable=True,
    )
    op.alter_column(
        "tracked_players",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "tracked_players",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter matches table
    op.alter_column(
        "matches",
        "game_creation",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "matches",
        "game_end_timestamp",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        nullable=True,
    )
    op.alter_column(
        "matches",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter match_participants table
    op.alter_column(
        "match_participants",
        "game_creation",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "match_participants",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter invalid_api_responses table
    op.alter_column(
        "invalid_api_responses",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter player_records table
    op.alter_column(
        "player_records",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter match_timelines table
    op.alter_column(
        "match_timelines",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )

    # Alter discord_user_registrations table
    op.alter_column(
        "discord_user_registrations",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "discord_user_registrations",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade database schema to remove timezone from datetime columns."""
    # Reverse alterations
    op.alter_column(
        "tracked_players",
        "last_polled_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        nullable=True,
    )
    op.alter_column(
        "tracked_players",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "tracked_players",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "matches",
        "game_creation",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "matches",
        "game_end_timestamp",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        nullable=True,
    )
    op.alter_column(
        "matches",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "match_participants",
        "game_creation",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "match_participants",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "invalid_api_responses",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "player_records",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "match_timelines",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "discord_user_registrations",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )
    op.alter_column(
        "discord_user_registrations",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
    )
