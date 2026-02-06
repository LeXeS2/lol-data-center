"""Tests for ConsecutiveCondition."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from lol_data_center.achievements.conditions import ConsecutiveCondition
from lol_data_center.database.models import Match, MatchParticipant, TrackedPlayer
from lol_data_center.schemas.achievements import (
    AchievementDefinition,
    ConditionType,
    Operator,
)
from lol_data_center.schemas.riot_api import ParticipantDto

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestConsecutiveCondition:
    """Tests for ConsecutiveCondition."""

    @pytest.mark.asyncio
    async def test_consecutive_wins_triggered(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test consecutive wins achievement when triggered (3 wins in a row)."""
        # Create 2 previous winning matches
        await self._create_previous_matches(
            async_session,
            sample_player,
            count=2,
            win=True,
        )

        # Current game is also a win (from sample_participant_dto)
        assert sample_participant_dto.win is True

        definition = AchievementDefinition(
            id="triple_win",
            name="Triple Win",
            description="Win 3 games in a row",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.EQ,
            threshold=1,  # Boolean win = 1 for True
            consecutive_count=3,
            message_template="{player_name} won 3 in a row!",
        )

        condition = ConsecutiveCondition(definition)
        result = await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_consecutive_wins_not_triggered_current_loss(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test consecutive wins not triggered when current game is a loss."""
        # Create 2 previous winning matches
        await self._create_previous_matches(
            async_session,
            sample_player,
            count=2,
            win=True,
        )

        # Current game is a loss
        sample_participant_dto.win = False

        definition = AchievementDefinition(
            id="triple_win",
            name="Triple Win",
            description="Win 3 games in a row",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.EQ,
            threshold=1,
            consecutive_count=3,
            message_template="{player_name} won 3 in a row!",
        )

        condition = ConsecutiveCondition(definition)
        result = await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_consecutive_wins_not_triggered_previous_loss(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test consecutive wins not triggered when one previous game was a loss."""
        # Create 1 win, 1 loss
        await self._create_previous_matches(
            async_session,
            sample_player,
            count=1,
            win=True,
        )
        await self._create_previous_matches(
            async_session,
            sample_player,
            count=1,
            win=False,
        )

        # Current game is a win
        assert sample_participant_dto.win is True

        definition = AchievementDefinition(
            id="triple_win",
            name="Triple Win",
            description="Win 3 games in a row",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.EQ,
            threshold=1,
            consecutive_count=3,
            message_template="{player_name} won 3 in a row!",
        )

        condition = ConsecutiveCondition(definition)
        result = await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_consecutive_not_enough_previous_games(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test consecutive achievement not triggered when not enough previous games."""
        # Create only 1 previous match (need 2 for streak of 3)
        await self._create_previous_matches(
            async_session,
            sample_player,
            count=1,
            win=True,
        )

        # Current game is a win
        assert sample_participant_dto.win is True

        definition = AchievementDefinition(
            id="triple_win",
            name="Triple Win",
            description="Win 3 games in a row",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.EQ,
            threshold=1,
            consecutive_count=3,
            message_template="{player_name} won 3 in a row!",
        )

        condition = ConsecutiveCondition(definition)
        result = await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_consecutive_high_kda_streak(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test consecutive high KDA achievement."""
        # Create 2 previous matches with KDA >= 5.0
        await self._create_previous_matches_with_kda(
            async_session,
            sample_player,
            count=2,
            kda=6.0,
        )

        # Current game also has high KDA
        sample_participant_dto.kills = 10
        sample_participant_dto.deaths = 2
        sample_participant_dto.assists = 10
        # KDA should be (10 + 10) / 2 = 10.0 >= 5.0

        definition = AchievementDefinition(
            id="perfect_kda_streak",
            name="Perfect KDA Streak",
            description="Get KDA >= 5 for 3 games in a row",
            stat_field="kda",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.GTE,
            threshold=5.0,
            consecutive_count=3,
            message_template="{player_name} had great KDA for 3 games!",
        )

        condition = ConsecutiveCondition(definition)
        result = await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_consecutive_validation_errors(
        self,
        sample_participant_dto: ParticipantDto,
        sample_player: TrackedPlayer,
        async_session: AsyncSession,
    ) -> None:
        """Test that validation errors are raised for invalid configurations."""
        # Missing consecutive_count
        definition = AchievementDefinition(
            id="bad_def",
            name="Bad Definition",
            description="Missing consecutive_count",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=Operator.EQ,
            threshold=1,
            consecutive_count=None,
            message_template="Test",
        )

        condition = ConsecutiveCondition(definition)
        with pytest.raises(ValueError, match="requires consecutive_count"):
            await condition.evaluate(sample_player, sample_participant_dto, async_session, 1800)

        # Missing operator
        definition2 = AchievementDefinition(
            id="bad_def2",
            name="Bad Definition 2",
            description="Missing operator",
            stat_field="win",
            condition_type=ConditionType.CONSECUTIVE,
            operator=None,
            threshold=1,
            consecutive_count=3,
            message_template="Test",
        )

        condition2 = ConsecutiveCondition(definition2)
        with pytest.raises(ValueError, match="requires threshold and operator"):
            await condition2.evaluate(sample_player, sample_participant_dto, async_session, 1800)

    async def _create_previous_matches(
        self,
        session: AsyncSession,
        player: TrackedPlayer,
        count: int,
        win: bool,
    ) -> None:
        """Helper to create previous match records."""
        base_time = datetime.now(UTC)

        for i in range(count):
            # Create matches in reverse chronological order (most recent first)
            game_creation = base_time - timedelta(hours=i + 1)

            # Use a unique match ID that includes the timestamp to avoid collisions
            match_id = f"TEST_MATCH_{win}_{i}_{int(game_creation.timestamp())}"

            match = Match(
                match_id=match_id,
                data_version="2",
                game_creation=game_creation,
                game_duration=1800,
                game_end_timestamp=game_creation + timedelta(seconds=1800),
                game_mode="CLASSIC",
                game_name="",
                game_type="MATCHED_GAME",
                game_version="14.1.123",
                map_id=11,
                platform_id="EUW1",
                queue_id=420,
                tournament_code=None,
            )
            session.add(match)
            await session.flush()

            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=player.puuid,
                player_id=player.id,
                game_creation=game_creation,
                summoner_name=player.game_name,
                summoner_id=None,
                riot_id_game_name=player.game_name,
                riot_id_tagline=player.tag_line,
                profile_icon=1,
                summoner_level=100,
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position="MID",
                individual_position="MID",
                lane="MID",
                role="SOLO",
                kills=5,
                deaths=3,
                assists=10,
                kda=5.0,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=30000,
                total_damage_taken=20000,
                damage_self_mitigated=10000,
                largest_killing_spree=3,
                largest_multi_kill=1,
                killing_sprees=1,
                double_kills=0,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=12000,
                gold_spent=11000,
                total_minions_killed=200,
                neutral_minions_killed=30,
                vision_score=40,
                wards_placed=15,
                wards_killed=5,
                vision_wards_bought_in_game=3,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=1,
                baron_kills=0,
                dragon_kills=1,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=0,
                total_damage_shielded_on_teammates=0,
                total_time_cc_dealt=100,
                time_ccing_others=20,
                win=win,
                first_blood_kill=False,
                first_blood_assist=False,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=0,
                item1=0,
                item2=0,
                item3=0,
                item4=0,
                item5=0,
                item6=0,
                summoner1_id=4,
                summoner2_id=12,
            )
            session.add(participant)

        await session.commit()

    async def _create_previous_matches_with_kda(
        self,
        session: AsyncSession,
        player: TrackedPlayer,
        count: int,
        kda: float,
    ) -> None:
        """Helper to create previous match records with specific KDA."""
        base_time = datetime.now(UTC)

        for i in range(count):
            game_creation = base_time - timedelta(hours=i + 1)

            # Use a unique match ID that includes the timestamp to avoid collisions
            match_id = f"TEST_MATCH_KDA_{i}_{int(game_creation.timestamp())}"

            match = Match(
                match_id=match_id,
                data_version="2",
                game_creation=game_creation,
                game_duration=1800,
                game_end_timestamp=game_creation + timedelta(seconds=1800),
                game_mode="CLASSIC",
                game_name="",
                game_type="MATCHED_GAME",
                game_version="14.1.123",
                map_id=11,
                platform_id="EUW1",
                queue_id=420,
                tournament_code=None,
            )
            session.add(match)
            await session.flush()

            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=player.puuid,
                player_id=player.id,
                game_creation=game_creation,
                summoner_name=player.game_name,
                summoner_id=None,
                riot_id_game_name=player.game_name,
                riot_id_tagline=player.tag_line,
                profile_icon=1,
                summoner_level=100,
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position="MID",
                individual_position="MID",
                lane="MID",
                role="SOLO",
                kills=10,
                deaths=2,
                assists=10,
                kda=kda,  # Use the specified KDA
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=30000,
                total_damage_taken=20000,
                damage_self_mitigated=10000,
                largest_killing_spree=3,
                largest_multi_kill=1,
                killing_sprees=1,
                double_kills=0,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=12000,
                gold_spent=11000,
                total_minions_killed=200,
                neutral_minions_killed=30,
                vision_score=40,
                wards_placed=15,
                wards_killed=5,
                vision_wards_bought_in_game=3,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=1,
                baron_kills=0,
                dragon_kills=1,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=0,
                total_damage_shielded_on_teammates=0,
                total_time_cc_dealt=100,
                time_ccing_others=20,
                win=True,
                first_blood_kill=False,
                first_blood_assist=False,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=0,
                item1=0,
                item2=0,
                item3=0,
                item4=0,
                item5=0,
                item6=0,
                summoner1_id=4,
                summoner2_id=12,
            )
            session.add(participant)

        await session.commit()
