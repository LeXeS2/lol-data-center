"""Add discord user registrations

Revision ID: 20260125_discord_registrations
Revises: 20260124_timeline
Create Date: 2026-01-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260125_discord_registrations'
down_revision: Union[str, None] = '20260124_timeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create discord_user_registrations table."""
    op.create_table(
        'discord_user_registrations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('discord_user_id', sa.String(length=100), nullable=False),
        sa.Column('puuid', sa.String(length=78), nullable=False),
        sa.Column('game_name', sa.String(length=100), nullable=False),
        sa.Column('tag_line', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('discord_user_id', name='uq_discord_user_registrations_discord_user_id'),
    )
    op.create_index('ix_discord_user_registrations_discord_user_id', 'discord_user_registrations', ['discord_user_id'], unique=True)


def downgrade() -> None:
    """Drop discord_user_registrations table."""
    op.drop_index('ix_discord_user_registrations_discord_user_id', table_name='discord_user_registrations')
    op.drop_table('discord_user_registrations')
