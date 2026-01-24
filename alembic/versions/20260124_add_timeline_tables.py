"""Add timeline tables

Revision ID: 20260124_timeline
Revises: (check your latest migration)
Create Date: 2026-01-24 14:46:01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = '20260124_timeline'
down_revision: Union[str, None] = None  # TODO: Update this to your latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create timeline tables."""
    # Create match_timelines table
    op.create_table(
        'match_timelines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('match_db_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.String(length=50), nullable=False),
        sa.Column('data_version', sa.String(length=10), nullable=False),
        sa.Column('frame_interval', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.BigInteger(), nullable=False),
        sa.Column('events', JSON, nullable=False),
        sa.Column('events_filtered', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['match_db_id'],
            ['matches.id'],
            name='fk_match_timelines_match_db_id',
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('match_db_id', name='uq_match_timelines_match_db_id'),
    )
    op.create_index('ix_match_timelines_match_id', 'match_timelines', ['match_id'], unique=True)

    # Create timeline_participant_frames table
    op.create_table(
        'timeline_participant_frames',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('timeline_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.String(length=50), nullable=False),
        sa.Column('puuid', sa.String(length=78), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('current_gold', sa.Integer(), nullable=False),
        sa.Column('total_gold', sa.Integer(), nullable=False),
        sa.Column('gold_per_second', sa.Integer(), nullable=False),
        sa.Column('xp', sa.Integer(), nullable=False),
        sa.Column('minions_killed', sa.Integer(), nullable=False),
        sa.Column('jungle_minions_killed', sa.Integer(), nullable=False),
        sa.Column('position_x', sa.Integer(), nullable=False),
        sa.Column('position_y', sa.Integer(), nullable=False),
        sa.Column('time_enemy_spent_controlled', sa.Integer(), nullable=False),
        # Damage stats
        sa.Column('magic_damage_done', sa.Integer(), nullable=True),
        sa.Column('magic_damage_done_to_champions', sa.Integer(), nullable=True),
        sa.Column('magic_damage_taken', sa.Integer(), nullable=True),
        sa.Column('physical_damage_done', sa.Integer(), nullable=True),
        sa.Column('physical_damage_done_to_champions', sa.Integer(), nullable=True),
        sa.Column('physical_damage_taken', sa.Integer(), nullable=True),
        sa.Column('total_damage_done', sa.Integer(), nullable=True),
        sa.Column('total_damage_done_to_champions', sa.Integer(), nullable=True),
        sa.Column('total_damage_taken', sa.Integer(), nullable=True),
        sa.Column('true_damage_done', sa.Integer(), nullable=True),
        sa.Column('true_damage_done_to_champions', sa.Integer(), nullable=True),
        sa.Column('true_damage_taken', sa.Integer(), nullable=True),
        # Champion stats
        sa.Column('ability_haste', sa.Integer(), nullable=True),
        sa.Column('ability_power', sa.Integer(), nullable=True),
        sa.Column('armor', sa.Integer(), nullable=True),
        sa.Column('armor_pen', sa.Integer(), nullable=True),
        sa.Column('armor_pen_percent', sa.Integer(), nullable=True),
        sa.Column('attack_damage', sa.Integer(), nullable=True),
        sa.Column('attack_speed', sa.Integer(), nullable=True),
        sa.Column('bonus_armor_pen_percent', sa.Integer(), nullable=True),
        sa.Column('bonus_magic_pen_percent', sa.Integer(), nullable=True),
        sa.Column('cc_reduction', sa.Integer(), nullable=True),
        sa.Column('cooldown_reduction', sa.Integer(), nullable=True),
        sa.Column('health', sa.Integer(), nullable=True),
        sa.Column('health_max', sa.Integer(), nullable=True),
        sa.Column('health_regen', sa.Integer(), nullable=True),
        sa.Column('lifesteal', sa.Integer(), nullable=True),
        sa.Column('magic_pen', sa.Integer(), nullable=True),
        sa.Column('magic_pen_percent', sa.Integer(), nullable=True),
        sa.Column('magic_resist', sa.Integer(), nullable=True),
        sa.Column('movement_speed', sa.Integer(), nullable=True),
        sa.Column('omnivamp', sa.Integer(), nullable=True),
        sa.Column('physical_vamp', sa.Integer(), nullable=True),
        sa.Column('power', sa.Integer(), nullable=True),
        sa.Column('power_max', sa.Integer(), nullable=True),
        sa.Column('power_regen', sa.Integer(), nullable=True),
        sa.Column('spell_vamp', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['timeline_id'],
            ['match_timelines.id'],
            name='fk_timeline_participant_frames_timeline_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['player_id'],
            ['tracked_players.id'],
            name='fk_timeline_participant_frames_player_id',
            ondelete='SET NULL',
        ),
        sa.UniqueConstraint(
            'timeline_id',
            'timestamp',
            'participant_id',
            name='uq_timeline_participant_frame',
        ),
    )
    op.create_index(
        'ix_timeline_participant_frames_match_id',
        'timeline_participant_frames',
        ['match_id'],
    )
    op.create_index(
        'ix_timeline_participant_frames_puuid',
        'timeline_participant_frames',
        ['puuid'],
    )
    op.create_index(
        'ix_timeline_puuid_timestamp',
        'timeline_participant_frames',
        ['puuid', 'timestamp'],
    )


def downgrade() -> None:
    """Drop timeline tables."""
    op.drop_index('ix_timeline_puuid_timestamp', table_name='timeline_participant_frames')
    op.drop_index('ix_timeline_participant_frames_puuid', table_name='timeline_participant_frames')
    op.drop_index('ix_timeline_participant_frames_match_id', table_name='timeline_participant_frames')
    op.drop_table('timeline_participant_frames')
    
    op.drop_index('ix_match_timelines_match_id', table_name='match_timelines')
    op.drop_table('match_timelines')
