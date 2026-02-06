"""Tests for achievement conditions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lol_data_center.achievements.conditions import (
    BASELINE_DURATION_SECONDS,
    AbsoluteCondition,
    PersonalMaxCondition,
    PersonalMinCondition,
    create_condition,
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


class TestAbsoluteCondition:
    """Tests for AbsoluteCondition."""

    @pytest.mark.asyncio
    async def test_greater_than_condition_met(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test greater than condition when met."""
        definition = AchievementDefinition(
            id="high_kills",
            name="High Kills",
            description="Get 5 or more kills",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=5,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is True
        assert result.current_value == 10  # From sample_participant_dto

    @pytest.mark.asyncio
    async def test_greater_than_condition_not_met(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test greater than condition when not met."""
        definition = AchievementDefinition(
            id="very_high_kills",
            name="Very High Kills",
            description="Get 20 or more kills",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=20,
            message_template="{player_name} got {value} kills!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is False
        assert result.current_value == 10

    @pytest.mark.asyncio
    async def test_equals_condition(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test equals condition for perfect game (0 deaths would be)."""
        # Modify participant to have 0 deaths
        sample_participant_dto.deaths = 0

        definition = AchievementDefinition(
            id="perfect_game",
            name="Perfect Game",
            description="0 deaths",
            stat_field="deaths",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.EQ,
            threshold=0,
            message_template="{player_name} had a perfect game!",
        )

        condition = AbsoluteCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is True
        assert result.current_value == 0


class TestPersonalMaxCondition:
    """Tests for PersonalMaxCondition."""

    @pytest.mark.asyncio
    async def test_new_personal_max(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test when a new personal maximum is achieved."""
        # Set kills higher than current record (15)
        sample_participant_dto.kills = 20

        definition = AchievementDefinition(
            id="new_kill_record",
            name="New Kill Record",
            description="New personal kill record",
            stat_field="kills",
            condition_type=ConditionType.PERSONAL_MAX,
            message_template="{player_name} set a new record: {value} kills!",
        )

        condition = PersonalMaxCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is True
        assert result.current_value == 20
        assert result.previous_value == 15  # From fixture

    @pytest.mark.asyncio
    async def test_no_new_personal_max(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test when no new personal maximum is achieved."""
        # Set kills lower than current record (15)
        sample_participant_dto.kills = 10

        definition = AchievementDefinition(
            id="new_kill_record",
            name="New Kill Record",
            description="New personal kill record",
            stat_field="kills",
            condition_type=ConditionType.PERSONAL_MAX,
            message_template="{player_name} set a new record!",
        )

        condition = PersonalMaxCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is False


class TestPersonalMinCondition:
    """Tests for PersonalMinCondition."""

    @pytest.mark.asyncio
    async def test_new_personal_min(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test when a new personal minimum is achieved."""
        # Set deaths lower than current record (2)
        sample_participant_dto.deaths = 1

        definition = AchievementDefinition(
            id="survival_expert",
            name="Survival Expert",
            description="New minimum deaths",
            stat_field="deaths",
            condition_type=ConditionType.PERSONAL_MIN,
            min_value=1,  # Exclude 0 deaths
            message_template="{player_name} only died {value} times!",
        )

        condition = PersonalMinCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        assert result.triggered is True
        assert result.current_value == 1

    @pytest.mark.asyncio
    async def test_min_value_threshold(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that values below min_value are excluded."""
        # Set deaths to 0 (below min_value of 1)
        sample_participant_dto.deaths = 0

        definition = AchievementDefinition(
            id="survival_expert",
            name="Survival Expert",
            description="New minimum deaths",
            stat_field="deaths",
            condition_type=ConditionType.PERSONAL_MIN,
            min_value=1,
            message_template="{player_name} only died {value} times!",
        )

        condition = PersonalMinCondition(definition)
        result = await condition.evaluate(
            sample_player, sample_participant_dto, async_session, BASELINE_DURATION_SECONDS
        )

        # Should not trigger because 0 < min_value of 1
        assert result.triggered is False


class TestConditionFactory:
    """Tests for the condition factory function."""

    def test_create_absolute_condition(self) -> None:
        """Test creating an absolute condition."""
        definition = AchievementDefinition(
            id="test",
            name="Test",
            description="Test",
            stat_field="kills",
            condition_type=ConditionType.ABSOLUTE,
            operator=Operator.GTE,
            threshold=10,
            message_template="Test",
        )

        condition = create_condition(definition)
        assert isinstance(condition, AbsoluteCondition)

    def test_create_personal_max_condition(self) -> None:
        """Test creating a personal max condition."""
        definition = AchievementDefinition(
            id="test",
            name="Test",
            description="Test",
            stat_field="kills",
            condition_type=ConditionType.PERSONAL_MAX,
            message_template="Test",
        )

        condition = create_condition(definition)
        assert isinstance(condition, PersonalMaxCondition)

    def test_create_personal_min_condition(self) -> None:
        """Test creating a personal min condition."""
        definition = AchievementDefinition(
            id="test",
            name="Test",
            description="Test",
            stat_field="deaths",
            condition_type=ConditionType.PERSONAL_MIN,
            message_template="Test",
        )

        condition = create_condition(definition)
        assert isinstance(condition, PersonalMinCondition)
