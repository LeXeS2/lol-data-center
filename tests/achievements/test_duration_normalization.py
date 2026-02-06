"""Tests for achievement duration normalization."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lol_data_center.achievements.conditions import (
    BASELINE_DURATION_SECONDS,
    AbsoluteCondition,
    PersonalMaxCondition,
    PersonalMinCondition,
)
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.schemas.achievements import (
    AchievementDefinition,
    ConditionType,
    Operator,
)
from lol_data_center.schemas.riot_api import ParticipantDto

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestDurationNormalization:
    """Tests for duration normalization functionality."""

    @pytest.mark.asyncio
    async def test_normalization_calculation(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that normalization correctly adjusts values to 30-minute baseline."""
        # Test with a 45-minute (2700 second) game
        # If player got 15 kills in 45 minutes, normalized to 30 min = (15 / 2700) * 1800 = 10
        sample_participant_dto.kills = 15
        game_duration = 2700  # 45 minutes

        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 10 or more kills (30-min normalized)",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            normalize_by_duration=True,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should trigger because 15 kills in 45 min = 10 kills normalized to 30 min
        assert result.triggered is True
        assert result.current_value == 10.0

    @pytest.mark.asyncio
    async def test_normalization_shorter_game(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test normalization with a shorter game duration."""
        # Test with a 20-minute (1200 second) game
        # If player got 10 kills in 20 minutes, normalized to 30 min = (10 / 1200) * 1800 = 15
        sample_participant_dto.kills = 10
        game_duration = 1200  # 20 minutes

        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 12 or more kills (30-min normalized)",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=12,
            normalize_by_duration=True,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should trigger because 10 kills in 20 min = 15 kills normalized to 30 min
        assert result.triggered is True
        assert result.current_value == 15.0

    @pytest.mark.asyncio
    async def test_normalization_exact_30_minutes(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that 30-minute games are not affected by normalization."""
        sample_participant_dto.kills = 10
        game_duration = BASELINE_DURATION_SECONDS  # Exactly 30 minutes

        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 10 or more kills",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            normalize_by_duration=True,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Value should remain exactly 10
        assert result.triggered is True
        assert result.current_value == 10.0

    @pytest.mark.asyncio
    async def test_normalization_disabled(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that normalization can be disabled with normalize_by_duration=False."""
        sample_participant_dto.deaths = 0
        game_duration = 2700  # 45 minutes

        definition = AchievementDefinition(
            id="perfect_game",
            name="Perfect Game",
            description="Finish with 0 deaths",
            stat_field="deaths",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.EQ,
            threshold=0,
            normalize_by_duration=False,  # Disabled
            message_template="{player_name} had a perfect game!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Value should remain exactly 0 (not normalized)
        assert result.triggered is True
        assert result.current_value == 0

    @pytest.mark.asyncio
    async def test_normalization_with_personal_max(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test normalization with personal_max condition."""
        from sqlalchemy import select

        from lol_data_center.database.models import PlayerRecord

        # Fetch existing player record (created by sample_player fixture)
        result = await async_session.execute(
            select(PlayerRecord).where(PlayerRecord.player_id == sample_player.id)
        )
        player_record = result.scalar_one()

        # Set max_kills to 15 (normalized to 30 min baseline)
        player_record.max_kills = 15
        await async_session.commit()

        # In a 40-minute game (2400s), player gets 22 kills
        # Normalized: (22 / 2400) * 1800 = 16.5
        sample_participant_dto.kills = 22
        game_duration = 2400  # 40 minutes

        definition = AchievementDefinition(
            id="new_kill_record",
            name="New Kill Record",
            description="Set a new personal kill record",
            stat_field="kills",
            condition_type=ConditionType.PERSONAL_MAX,
            normalize_by_duration=True,
            message_template="{player_name} set a new record!",
        )

        condition = PersonalMaxCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should trigger because 16.5 > 15
        assert result.triggered is True
        assert result.current_value == 16.5
        assert result.previous_value == 15.0

    @pytest.mark.asyncio
    async def test_normalization_with_personal_min(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test normalization with personal_min condition."""
        from sqlalchemy import select

        from lol_data_center.database.models import PlayerRecord

        # Fetch existing player record (created by sample_player fixture)
        result = await async_session.execute(
            select(PlayerRecord).where(PlayerRecord.player_id == sample_player.id)
        )
        player_record = result.scalar_one()

        # Set min_deaths to 3.0 (normalized to 30 min baseline)
        player_record.min_deaths = 3.0
        await async_session.commit()

        # In a 40-minute game (2400s), player has 3 deaths
        # Normalized: (3 / 2400) * 1800 = 2.25
        sample_participant_dto.deaths = 3
        game_duration = 2400  # 40 minutes

        definition = AchievementDefinition(
            id="fewest_deaths",
            name="Survival Expert",
            description="New personal minimum deaths",
            stat_field="deaths",
            condition_type=ConditionType.PERSONAL_MIN,
            min_value=1,  # Exclude perfect games
            normalize_by_duration=True,
            message_template="{player_name} survived well!",
        )

        condition = PersonalMinCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should trigger because 2.25 < 3.0
        assert result.triggered is True
        assert result.current_value == 2.25
        assert result.previous_value == 3.0

    @pytest.mark.asyncio
    async def test_normalization_with_cs(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test normalization with CS (total_minions_killed)."""
        # In a 50-minute game (3000s), player gets 500 CS
        # Normalized: (500 / 3000) * 1800 = 300
        sample_participant_dto.total_minions_killed = 500
        game_duration = 3000  # 50 minutes

        definition = AchievementDefinition(
            id="cs_master",
            name="CS Master",
            description="Get 300 or more CS (normalized)",
            stat_field="total_minions_killed",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=300,
            normalize_by_duration=True,
            message_template="{player_name} farmed well!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should trigger because 500 CS in 50 min = 300 CS normalized
        assert result.triggered is True
        assert result.current_value == 300.0

    @pytest.mark.asyncio
    async def test_normalization_threshold_not_met(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that threshold is not met when normalized value is too low."""
        # In a 50-minute game (3000s), player gets 12 kills
        # Normalized: (12 / 3000) * 1800 = 7.2
        sample_participant_dto.kills = 12
        game_duration = 3000  # 50 minutes

        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 10 or more kills (normalized)",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            normalize_by_duration=True,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Should NOT trigger because 7.2 < 10
        assert result.triggered is False
        assert result.current_value == 7.2

    @pytest.mark.asyncio
    async def test_kda_not_normalized(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that KDA is not normalized (it's already a ratio)."""
        # KDA should not be affected by game duration
        sample_participant_dto.kills = 10
        sample_participant_dto.deaths = 2
        sample_participant_dto.assists = 15
        # KDA = (10 + 15) / 2 = 12.5
        game_duration = 2400  # 40 minutes

        definition = AchievementDefinition(
            id="high_kda",
            name="High KDA",
            description="Get KDA >= 5",
            stat_field="kda",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=5.0,
            normalize_by_duration=False,  # KDA should not be normalized
            message_template="{player_name} had high KDA!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # KDA should remain 12.5 regardless of game duration
        assert result.triggered is True
        assert result.current_value == 12.5

    @pytest.mark.asyncio
    async def test_win_not_normalized(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that boolean win field is not normalized."""
        sample_participant_dto.win = True
        game_duration = 2400  # 40 minutes

        definition = AchievementDefinition(
            id="win_check",
            name="Win",
            description="Win the game",
            stat_field="win",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.EQ,
            threshold=1,  # True = 1
            normalize_by_duration=False,  # Boolean shouldn't be normalized
            message_template="{player_name} won!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, game_duration
        )

        # Win should be 1 (True) regardless of duration
        assert result.triggered is True
        assert result.current_value == 1.0
