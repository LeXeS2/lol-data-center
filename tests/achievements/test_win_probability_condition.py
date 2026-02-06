"""Tests for WinProbabilityCondition."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lol_data_center.achievements.conditions import WinProbabilityCondition, create_condition
from lol_data_center.database.models import TrackedPlayer
from lol_data_center.schemas.achievements import AchievementDefinition, ConditionType
from lol_data_center.schemas.riot_api import ParticipantDto

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestWinProbabilityCondition:
    """Tests for WinProbabilityCondition."""

    @pytest.mark.asyncio
    async def test_surprise_win_triggered(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test surprise win when player wins despite low predicted probability."""
        # Create a participant that won but had low win probability
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=True,  # Won the game
            predicted_win_probability=0.15,  # But only 15% chance predicted
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_win",
            name="Surprise Win",
            description="Won despite low win probability",
            stat_field="surprise_win",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.2,  # Threshold of 20%
            message_template="⚡ **{player_name}** achieved a Surprise Win!",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is True
        assert result.current_value == 0.15

    @pytest.mark.asyncio
    async def test_surprise_win_not_triggered_high_probability(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test surprise win not triggered when win probability was high."""
        # Won with high probability - not a surprise
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=True,
            predicted_win_probability=0.85,  # High probability
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_win",
            name="Surprise Win",
            description="Won despite low win probability",
            stat_field="surprise_win",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.2,
            message_template="⚡ **{player_name}** achieved a Surprise Win!",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_surprise_win_not_triggered_lost(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test surprise win not triggered when player lost."""
        # Lost with low probability - expected outcome
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=False,  # Lost
            predicted_win_probability=0.10,  # Low probability
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_win",
            name="Surprise Win",
            description="Won despite low win probability",
            stat_field="surprise_win",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.2,
            message_template="⚡ **{player_name}** achieved a Surprise Win!",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_surprise_loss_triggered(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test surprise loss when player loses despite high predicted probability."""
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=False,  # Lost the game
            predicted_win_probability=0.85,  # But 85% chance predicted
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_loss",
            name="Surprise Loss",
            description="Lost despite high win probability",
            stat_field="surprise_loss",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.8,  # Threshold of 80%
            message_template="⚡ **{player_name}** suffered a Surprise Loss.",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is True
        assert result.current_value == 0.85

    @pytest.mark.asyncio
    async def test_surprise_loss_not_triggered_low_probability(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test surprise loss not triggered when win probability was low."""
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=False,
            predicted_win_probability=0.30,  # Low probability
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_loss",
            name="Surprise Loss",
            description="Lost despite high win probability",
            stat_field="surprise_loss",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.8,
            message_template="⚡ **{player_name}** suffered a Surprise Loss.",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_no_prediction_available(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that achievement is not triggered when no prediction is available."""
        participant = ParticipantDto(
            puuid="test-puuid-12345",
            summonerName="TestPlayer",
            summonerId=None,
            riotIdGameName="TestPlayer",
            riotIdTagline="EUW",
            profileIcon=1,
            summonerLevel=100,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            teamPosition="MIDDLE",
            individualPosition="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=15,
            totalDamageDealt=150000,
            totalDamageDealtToChampions=45000,
            totalDamageTaken=25000,
            damageSelfMitigated=10000,
            goldEarned=15000,
            goldSpent=14000,
            totalMinionsKilled=200,
            neutralMinionsKilled=30,
            win=True,
            predicted_win_probability=None,  # No prediction
            summoner1Id=4,
            summoner2Id=14,
        )

        definition = AchievementDefinition(
            id="surprise_win",
            name="Surprise Win",
            description="Won despite low win probability",
            stat_field="surprise_win",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.2,
            message_template="⚡ **{player_name}** achieved a Surprise Win!",
        )

        condition = WinProbabilityCondition(definition)
        result = await condition.evaluate(sample_player, participant, async_session)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_create_condition_factory(
        self,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that create_condition factory creates WinProbabilityCondition correctly."""
        definition = AchievementDefinition(
            id="surprise_win",
            name="Surprise Win",
            description="Won despite low win probability",
            stat_field="surprise_win",
            condition_type=ConditionType.WIN_PROBABILITY,
            threshold=0.2,
            message_template="⚡ **{player_name}** achieved a Surprise Win!",
        )

        condition = create_condition(definition)

        assert isinstance(condition, WinProbabilityCondition)
        assert condition.definition == definition
