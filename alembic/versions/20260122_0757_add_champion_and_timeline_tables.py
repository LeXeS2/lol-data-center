"""add_champion_and_timeline_tables

Revision ID: 20260122_0757
Revises: 
Create Date: 2026-01-22 07:57:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260122_0757'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Champion and MatchTimeline tables."""
    # Create champions table
    op.create_table(
        'champions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_champions_name'), 'champions', ['name'], unique=False)

    # Create match_timelines table
    op.create_table(
        'match_timelines',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('match_id', sa.String(length=50), nullable=False),
        sa.Column('timeline_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['match_id'], ['matches.match_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id')
    )
    op.create_index(op.f('ix_match_timelines_match_id'), 'match_timelines', ['match_id'], unique=False)


def downgrade() -> None:
    """Drop Champion and MatchTimeline tables."""
    op.drop_index(op.f('ix_match_timelines_match_id'), table_name='match_timelines')
    op.drop_table('match_timelines')
    op.drop_index(op.f('ix_champions_name'), table_name='champions')
    op.drop_table('champions')
