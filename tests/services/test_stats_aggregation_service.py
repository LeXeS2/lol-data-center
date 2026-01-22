"""Tests for StatsAggregationService."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from lol_data_center.database.models import Match, MatchParticipant
from lol_data_center.services.stats_aggregation_service import StatsAggregationService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lol_data_center.database.models import TrackedPlayer


class TestStatsAggregationService:
    """Tests for StatsAggregationService."""

    @pytest.mark.asyncio
    async def test_get_player_stats_by_role(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting player stats aggregated by role."""
        # Create some test match participants
        match1 = Match(
            match_id="TEST_MATCH_1",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match1)
        await async_session.flush()

        # Create participants with different stats
        participant1 = MatchParticipant(
            match_db_id=match1.id,
            match_id=match1.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match1.game_creation,
            summoner_name="TestPlayer",
            profile_icon=1,
            summoner_level=100,
            champion_id=1,
            champion_name="Annie",
            champion_level=18,
            team_id=100,
            individual_position="MIDDLE",
            team_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=8,
            kda=6.0,
            total_damage_dealt=100000,
            total_damage_dealt_to_champions=30000,
            total_damage_taken=20000,
            damage_self_mitigated=10000,
            gold_earned=12000,
            largest_killing_spree=0,
            largest_multi_kill=0,
            killing_sprees=0,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
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
            gold_spent=11000,
            total_minions_killed=200,
            neutral_minions_killed=30,
            vision_score=40,
            wards_placed=15,
            wards_killed=5,
            vision_wards_bought_in_game=3,
            win=True,
            summoner1_id=4,
            summoner2_id=12,
        )
        async_session.add(participant1)
        await async_session.commit()

        # Test stats aggregation
        service = StatsAggregationService(async_session)
        stats = await service.get_player_stats_by_role(sample_player.puuid, "MIDDLE")

        assert "kills" in stats
        assert stats["kills"]["avg"] == 10.0
        assert stats["kills"]["min"] == 10.0
        assert stats["kills"]["max"] == 10.0
        assert stats["deaths"]["avg"] == 3.0
        assert stats["vision_score"]["avg"] == 40.0

    @pytest.mark.asyncio
    async def test_get_nth_most_recent_game(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting nth most recent game."""
        # Create two test matches
        match1 = Match(
            match_id="TEST_MATCH_1",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        match2 = Match(
            match_id="TEST_MATCH_2",
            data_version="2",
            game_creation=datetime(2024, 1, 2, 12, 0, 0),  # More recent
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match1)
        async_session.add(match2)
        await async_session.flush()

        # Create participants
        participant1 = MatchParticipant(
            match_db_id=match1.id,
            match_id=match1.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match1.game_creation,
            summoner_name="TestPlayer",
            profile_icon=1,
            summoner_level=100,
            champion_id=1,
            champion_name="Annie",
            champion_level=18,
            team_id=100,
            individual_position="MIDDLE",
            team_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=8,
            kda=6.0,
            total_damage_dealt=100000,
            total_damage_dealt_to_champions=30000,
            total_damage_taken=20000,
            damage_self_mitigated=10000,
            gold_earned=12000,
            largest_killing_spree=0,
            largest_multi_kill=0,
            killing_sprees=0,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
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
            gold_spent=11000,
            total_minions_killed=200,
            neutral_minions_killed=30,
            vision_score=40,
            wards_placed=15,
            wards_killed=5,
            vision_wards_bought_in_game=3,
            win=True,
            summoner1_id=4,
            summoner2_id=12,
        )
        participant2 = MatchParticipant(
            match_db_id=match2.id,
            match_id=match2.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match2.game_creation,
            summoner_name="TestPlayer",
            profile_icon=1,
            summoner_level=100,
            champion_id=2,
            champion_name="Ahri",
            champion_level=18,
            team_id=100,
            individual_position="MIDDLE",
            team_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=5,
            deaths=2,
            assists=10,
            kda=7.5,
            total_damage_dealt=95000,
            total_damage_dealt_to_champions=28000,
            total_damage_taken=18000,
            damage_self_mitigated=9000,
            gold_earned=11000,
            largest_killing_spree=0,
            largest_multi_kill=0,
            killing_sprees=0,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
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
            gold_spent=10500,
            total_minions_killed=180,
            neutral_minions_killed=25,
            vision_score=35,
            wards_placed=12,
            wards_killed=4,
            vision_wards_bought_in_game=2,
            win=False,
            summoner1_id=4,
            summoner2_id=12,
        )
        async_session.add(participant1)
        async_session.add(participant2)
        await async_session.commit()

        # Test getting nth most recent game
        service = StatsAggregationService(async_session)

        # Get most recent game (should be match2)
        most_recent = await service.get_nth_most_recent_game(sample_player.puuid, 1)
        assert most_recent is not None
        assert most_recent.match_id == "TEST_MATCH_2"
        assert most_recent.champion_name == "Ahri"

        # Get second most recent game (should be match1)
        second_recent = await service.get_nth_most_recent_game(sample_player.puuid, 2)
        assert second_recent is not None
        assert second_recent.match_id == "TEST_MATCH_1"
        assert second_recent.champion_name == "Annie"

        # Get non-existent game
        nonexistent = await service.get_nth_most_recent_game(sample_player.puuid, 3)
        assert nonexistent is None

    @pytest.mark.asyncio
    async def test_get_all_roles_stats(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting stats for all roles."""
        # Create matches for different roles
        match1 = Match(
            match_id="TEST_MATCH_1",
            data_version="2",
            game_creation=datetime(2024, 1, 1, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        match2 = Match(
            match_id="TEST_MATCH_2",
            data_version="2",
            game_creation=datetime(2024, 1, 2, 12, 0, 0),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match1)
        async_session.add(match2)
        await async_session.flush()

        # Participant for MIDDLE role
        participant1 = MatchParticipant(
            match_db_id=match1.id,
            match_id=match1.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match1.game_creation,
            summoner_name="TestPlayer",
            profile_icon=1,
            summoner_level=100,
            champion_id=1,
            champion_name="Annie",
            champion_level=18,
            team_id=100,
            individual_position="MIDDLE",
            team_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=3,
            assists=8,
            kda=6.0,
            total_damage_dealt=100000,
            total_damage_dealt_to_champions=30000,
            total_damage_taken=20000,
            damage_self_mitigated=10000,
            gold_earned=12000,
            largest_killing_spree=0,
            largest_multi_kill=0,
            killing_sprees=0,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
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
            gold_spent=11000,
            total_minions_killed=200,
            neutral_minions_killed=30,
            vision_score=40,
            wards_placed=15,
            wards_killed=5,
            vision_wards_bought_in_game=3,
            win=True,
            summoner1_id=4,
            summoner2_id=12,
        )
        # Participant for JUNGLE role
        participant2 = MatchParticipant(
            match_db_id=match2.id,
            match_id=match2.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match2.game_creation,
            summoner_name="TestPlayer",
            profile_icon=1,
            summoner_level=100,
            champion_id=2,
            champion_name="LeeSin",
            champion_level=18,
            team_id=100,
            individual_position="JUNGLE",
            team_position="JUNGLE",
            lane="JUNGLE",
            role="NONE",
            kills=5,
            deaths=2,
            assists=15,
            kda=10.0,
            total_damage_dealt=80000,
            total_damage_dealt_to_champions=25000,
            total_damage_taken=25000,
            damage_self_mitigated=15000,
            gold_earned=10000,
            largest_killing_spree=0,
            largest_multi_kill=0,
            killing_sprees=0,
            double_kills=0,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            turret_kills=0,
            turret_takedowns=0,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=0,
            total_heals_on_teammates=0,
            total_damage_shielded_on_teammates=0,
            total_time_cc_dealt=0,
            time_ccing_others=0,
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
            gold_spent=9500,
            total_minions_killed=100,
            neutral_minions_killed=150,
            vision_score=50,
            wards_placed=20,
            wards_killed=8,
            vision_wards_bought_in_game=5,
            win=True,
            summoner1_id=4,
            summoner2_id=12,
        )
        async_session.add(participant1)
        async_session.add(participant2)
        await async_session.commit()

        # Test getting all roles stats
        service = StatsAggregationService(async_session)
        all_stats = await service.get_all_roles_stats(sample_player.puuid)

        assert "MIDDLE" in all_stats
        assert "JUNGLE" in all_stats
        assert all_stats["MIDDLE"]["kills"]["avg"] == 10.0
        assert all_stats["JUNGLE"]["kills"]["avg"] == 5.0
