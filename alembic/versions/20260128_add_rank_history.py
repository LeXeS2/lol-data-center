"""Add rank history table

Revision ID: 20260128_rank_history
Revises: 20260125_tz_aware
Create Date: 2026-01-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260128_rank_history'
down_revision: Union[str, None] = '20260125_tz_aware'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create rank_history table."""
    op.create_table(
        'rank_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('queue_type', sa.String(length=50), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('rank', sa.String(length=10), nullable=False),
        sa.Column('league_points', sa.Integer(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False),
        sa.Column('losses', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.String(length=100), nullable=False),
        sa.Column('veteran', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('inactive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fresh_blood', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('hot_streak', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['player_id'], ['tracked_players.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('player_id', 'queue_type', 'recorded_at', name='uq_rank_snapshot'),
    )
    op.create_index('ix_rank_player_queue_time', 'rank_history', ['player_id', 'queue_type', 'recorded_at'])
    op.create_index('ix_rank_history_recorded_at', 'rank_history', ['recorded_at'])


def downgrade() -> None:
    """Drop rank_history table."""
    op.drop_index('ix_rank_history_recorded_at', table_name='rank_history')
    op.drop_index('ix_rank_player_queue_time', table_name='rank_history')
    op.drop_table('rank_history')
