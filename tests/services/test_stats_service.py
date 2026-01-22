"""Tests for StatsService."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import MatchParticipant, TrackedPlayer
from lol_data_center.services.stats_service import StatsService


class TestStatsService:
    """Tests for StatsService."""

    @pytest.mark.asyncio
    async def test_get_stats_by_champion_no_games(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test stats by champion with no games."""
        service = StatsService(async_session)

        stats = await service.get_stats_by_champion(sample_player.puuid)

        assert stats == []

    @pytest.mark.asyncio
    async def test_get_stats_by_champion_single_game(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test stats by champion with single game."""
        # Create a single match participation
        participant = MatchParticipant(
            match_db_id=1,
            match_id="TEST_MATCH_1",
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=datetime.now(),
            summoner_name=sample_player.game_name,
            profile_icon=1,
            summoner_level=100,
            champion_id=157,
            champion_name="Yasuo",
            champion_level=18,
            team_id=100,
            team_position="MIDDLE",
            individual_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=5,
            assists=8,
            kda=3.6,
            total_damage_dealt=100000,
            total_damage_dealt_to_champions=25000,
            total_damage_taken=20000,
            damage_self_mitigated=15000,
            largest_killing_spree=5,
            largest_multi_kill=2,
            killing_sprees=2,
            double_kills=1,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            gold_earned=15000,
            gold_spent=14500,
            total_minions_killed=200,
            neutral_minions_killed=20,
            vision_score=30,
            wards_placed=15,
            wards_killed=8,
            vision_wards_bought_in_game=5,
            turret_kills=2,
            turret_takedowns=3,
            inhibitor_kills=1,
            inhibitor_takedowns=1,
            baron_kills=1,
            dragon_kills=2,
            objective_stolen=0,
            total_heal=5000,
            total_heals_on_teammates=1000,
            total_damage_shielded_on_teammates=2000,
            total_time_cc_dealt=30,
            time_ccing_others=30,
            win=True,
            first_blood_kill=False,
            first_blood_assist=True,
            first_tower_kill=False,
            first_tower_assist=False,
            game_ended_in_surrender=False,
            game_ended_in_early_surrender=False,
            time_played=1800,
            item0=3031,
            item1=3006,
            item2=3094,
            item3=3072,
            item4=3026,
            item5=3139,
            item6=3340,
            summoner1_id=4,
            summoner2_id=14,
        )
        async_session.add(participant)
        await async_session.commit()

        service = StatsService(async_session)
        stats = await service.get_stats_by_champion(sample_player.puuid)

        assert len(stats) == 1
        assert stats[0].group_key == "Yasuo"
        assert stats[0].game_count == 1
        assert stats[0].avg_kills == 10
        assert stats[0].avg_deaths == 5
        assert stats[0].avg_assists == 8
        assert stats[0].avg_kda == 3.6
        assert stats[0].avg_cs == 200
        assert stats[0].avg_gold == 15000
        assert stats[0].avg_damage == 25000
        assert stats[0].avg_vision_score == 30
        assert stats[0].max_kills == 10
        assert stats[0].min_kills == 10
        # Standard deviation is 0 for a single game (division by n-1 with n=1 is undefined)
        assert stats[0].stddev_kills == 0.0
        assert stats[0].win_rate == 100.0

    @pytest.mark.asyncio
    async def test_get_stats_by_champion_multiple_games(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test stats by champion with multiple games."""
        # Create multiple match participations for different champions
        base_time = datetime.now()

        participants = [
            # Yasuo games
            MatchParticipant(
                match_db_id=1,
                match_id="TEST_MATCH_1",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time,
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10,
                deaths=5,
                assists=8,
                kda=3.6,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=25000,
                total_damage_taken=20000,
                damage_self_mitigated=15000,
                largest_killing_spree=5,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=15000,
                gold_spent=14500,
                total_minions_killed=200,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=15,
                wards_killed=8,
                vision_wards_bought_in_game=5,
                turret_kills=2,
                turret_takedowns=3,
                inhibitor_kills=1,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=2,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=1000,
                total_damage_shielded_on_teammates=2000,
                total_time_cc_dealt=30,
                time_ccing_others=30,
                win=True,
                first_blood_kill=False,
                first_blood_assist=True,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=3031,
                item1=3006,
                item2=3094,
                item3=3072,
                item4=3026,
                item5=3139,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            ),
            MatchParticipant(
                match_db_id=2,
                match_id="TEST_MATCH_2",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=1),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=16,
                team_id=200,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=5,
                deaths=8,
                assists=6,
                kda=1.375,
                total_damage_dealt=80000,
                total_damage_dealt_to_champions=18000,
                total_damage_taken=25000,
                damage_self_mitigated=12000,
                largest_killing_spree=2,
                largest_multi_kill=1,
                killing_sprees=1,
                double_kills=0,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=12000,
                gold_spent=11800,
                total_minions_killed=180,
                neutral_minions_killed=15,
                vision_score=25,
                wards_placed=12,
                wards_killed=6,
                vision_wards_bought_in_game=4,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=1,
                objective_stolen=0,
                total_heal=4000,
                total_heals_on_teammates=800,
                total_damage_shielded_on_teammates=1500,
                total_time_cc_dealt=25,
                time_ccing_others=25,
                win=False,
                first_blood_kill=False,
                first_blood_assist=False,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=True,
                game_ended_in_early_surrender=False,
                time_played=1650,
                item0=3031,
                item1=3006,
                item2=1018,
                item3=0,
                item4=0,
                item5=0,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            ),
            # Ahri game
            MatchParticipant(
                match_db_id=3,
                match_id="TEST_MATCH_3",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=2),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=103,
                champion_name="Ahri",
                champion_level=17,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=12,
                deaths=4,
                assists=10,
                kda=5.5,
                total_damage_dealt=95000,
                total_damage_dealt_to_champions=30000,
                total_damage_taken=18000,
                damage_self_mitigated=10000,
                largest_killing_spree=6,
                largest_multi_kill=3,
                killing_sprees=2,
                double_kills=2,
                triple_kills=1,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=16000,
                gold_spent=15500,
                total_minions_killed=210,
                neutral_minions_killed=25,
                vision_score=35,
                wards_placed=18,
                wards_killed=10,
                vision_wards_bought_in_game=6,
                turret_kills=3,
                turret_takedowns=4,
                inhibitor_kills=1,
                inhibitor_takedowns=2,
                baron_kills=1,
                dragon_kills=3,
                objective_stolen=1,
                total_heal=5500,
                total_heals_on_teammates=1200,
                total_damage_shielded_on_teammates=2200,
                total_time_cc_dealt=35,
                time_ccing_others=35,
                win=True,
                first_blood_kill=True,
                first_blood_assist=False,
                first_tower_kill=True,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1900,
                item0=3089,
                item1=3020,
                item2=3135,
                item3=3165,
                item4=3157,
                item5=3151,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            ),
        ]

        for p in participants:
            async_session.add(p)
        await async_session.commit()

        service = StatsService(async_session)
        stats = await service.get_stats_by_champion(sample_player.puuid)

        # Should have 2 champions (Yasuo with 2 games, Ahri with 1 game)
        assert len(stats) == 2

        # Stats should be sorted by game count (Yasuo first with 2 games)
        yasuo_stats = stats[0]
        assert yasuo_stats.group_key == "Yasuo"
        assert yasuo_stats.game_count == 2
        assert yasuo_stats.avg_kills == 7.5  # (10 + 5) / 2
        assert yasuo_stats.avg_deaths == 6.5  # (5 + 8) / 2
        assert yasuo_stats.win_rate == 50.0  # 1 win, 1 loss

        ahri_stats = stats[1]
        assert ahri_stats.group_key == "Ahri"
        assert ahri_stats.game_count == 1

    @pytest.mark.asyncio
    async def test_get_stats_by_champion_min_games_filter(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test min_games filter in stats by champion."""
        base_time = datetime.now()

        # Add 3 Yasuo games and 1 Ahri game
        participants = []
        for i in range(3):
            participants.append(
                MatchParticipant(
                    match_db_id=i + 1,
                    match_id=f"TEST_MATCH_{i + 1}",
                    puuid=sample_player.puuid,
                    player_id=sample_player.id,
                    game_creation=base_time - timedelta(hours=i),
                    summoner_name=sample_player.game_name,
                    profile_icon=1,
                    summoner_level=100,
                    champion_id=157,
                    champion_name="Yasuo",
                    champion_level=18,
                    team_id=100,
                    team_position="MIDDLE",
                    individual_position="MIDDLE",
                    lane="MIDDLE",
                    role="SOLO",
                    kills=10,
                    deaths=5,
                    assists=8,
                    kda=3.6,
                    total_damage_dealt=100000,
                    total_damage_dealt_to_champions=25000,
                    total_damage_taken=20000,
                    damage_self_mitigated=15000,
                    largest_killing_spree=5,
                    largest_multi_kill=2,
                    killing_sprees=2,
                    double_kills=1,
                    triple_kills=0,
                    quadra_kills=0,
                    penta_kills=0,
                    gold_earned=15000,
                    gold_spent=14500,
                    total_minions_killed=200,
                    neutral_minions_killed=20,
                    vision_score=30,
                    wards_placed=15,
                    wards_killed=8,
                    vision_wards_bought_in_game=5,
                    turret_kills=2,
                    turret_takedowns=3,
                    inhibitor_kills=1,
                    inhibitor_takedowns=1,
                    baron_kills=1,
                    dragon_kills=2,
                    objective_stolen=0,
                    total_heal=5000,
                    total_heals_on_teammates=1000,
                    total_damage_shielded_on_teammates=2000,
                    total_time_cc_dealt=30,
                    time_ccing_others=30,
                    win=True,
                    first_blood_kill=False,
                    first_blood_assist=True,
                    first_tower_kill=False,
                    first_tower_assist=False,
                    game_ended_in_surrender=False,
                    game_ended_in_early_surrender=False,
                    time_played=1800,
                    item0=3031,
                    item1=3006,
                    item2=3094,
                    item3=3072,
                    item4=3026,
                    item5=3139,
                    item6=3340,
                    summoner1_id=4,
                    summoner2_id=14,
                )
            )

        # Add 1 Ahri game
        participants.append(
            MatchParticipant(
                match_db_id=4,
                match_id="TEST_MATCH_4",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=3),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=103,
                champion_name="Ahri",
                champion_level=17,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=12,
                deaths=4,
                assists=10,
                kda=5.5,
                total_damage_dealt=95000,
                total_damage_dealt_to_champions=30000,
                total_damage_taken=18000,
                damage_self_mitigated=10000,
                largest_killing_spree=6,
                largest_multi_kill=3,
                killing_sprees=2,
                double_kills=2,
                triple_kills=1,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=16000,
                gold_spent=15500,
                total_minions_killed=210,
                neutral_minions_killed=25,
                vision_score=35,
                wards_placed=18,
                wards_killed=10,
                vision_wards_bought_in_game=6,
                turret_kills=3,
                turret_takedowns=4,
                inhibitor_kills=1,
                inhibitor_takedowns=2,
                baron_kills=1,
                dragon_kills=3,
                objective_stolen=1,
                total_heal=5500,
                total_heals_on_teammates=1200,
                total_damage_shielded_on_teammates=2200,
                total_time_cc_dealt=35,
                time_ccing_others=35,
                win=True,
                first_blood_kill=True,
                first_blood_assist=False,
                first_tower_kill=True,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1900,
                item0=3089,
                item1=3020,
                item2=3135,
                item3=3165,
                item4=3157,
                item5=3151,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            )
        )

        for p in participants:
            async_session.add(p)
        await async_session.commit()

        service = StatsService(async_session)

        # With min_games=2, should only return Yasuo (3 games)
        stats = await service.get_stats_by_champion(sample_player.puuid, min_games=2)
        assert len(stats) == 1
        assert stats[0].group_key == "Yasuo"
        assert stats[0].game_count == 3

    @pytest.mark.asyncio
    async def test_get_stats_by_role_no_games(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test stats by role with no games."""
        service = StatsService(async_session)

        stats = await service.get_stats_by_role(sample_player.puuid)

        assert stats == []

    @pytest.mark.asyncio
    async def test_get_stats_by_role_multiple_games(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test stats by role with multiple games."""
        base_time = datetime.now()

        # Create games in different roles
        participants = [
            # MIDDLE games
            MatchParticipant(
                match_db_id=1,
                match_id="TEST_MATCH_1",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time,
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10,
                deaths=5,
                assists=8,
                kda=3.6,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=25000,
                total_damage_taken=20000,
                damage_self_mitigated=15000,
                largest_killing_spree=5,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=15000,
                gold_spent=14500,
                total_minions_killed=200,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=15,
                wards_killed=8,
                vision_wards_bought_in_game=5,
                turret_kills=2,
                turret_takedowns=3,
                inhibitor_kills=1,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=2,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=1000,
                total_damage_shielded_on_teammates=2000,
                total_time_cc_dealt=30,
                time_ccing_others=30,
                win=True,
                first_blood_kill=False,
                first_blood_assist=True,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=3031,
                item1=3006,
                item2=3094,
                item3=3072,
                item4=3026,
                item5=3139,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            ),
            MatchParticipant(
                match_db_id=2,
                match_id="TEST_MATCH_2",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=1),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=103,
                champion_name="Ahri",
                champion_level=17,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=12,
                deaths=4,
                assists=10,
                kda=5.5,
                total_damage_dealt=95000,
                total_damage_dealt_to_champions=30000,
                total_damage_taken=18000,
                damage_self_mitigated=10000,
                largest_killing_spree=6,
                largest_multi_kill=3,
                killing_sprees=2,
                double_kills=2,
                triple_kills=1,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=16000,
                gold_spent=15500,
                total_minions_killed=210,
                neutral_minions_killed=25,
                vision_score=35,
                wards_placed=18,
                wards_killed=10,
                vision_wards_bought_in_game=6,
                turret_kills=3,
                turret_takedowns=4,
                inhibitor_kills=1,
                inhibitor_takedowns=2,
                baron_kills=1,
                dragon_kills=3,
                objective_stolen=1,
                total_heal=5500,
                total_heals_on_teammates=1200,
                total_damage_shielded_on_teammates=2200,
                total_time_cc_dealt=35,
                time_ccing_others=35,
                win=True,
                first_blood_kill=True,
                first_blood_assist=False,
                first_tower_kill=True,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1900,
                item0=3089,
                item1=3020,
                item2=3135,
                item3=3165,
                item4=3157,
                item5=3151,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            ),
            # JUNGLE game
            MatchParticipant(
                match_db_id=3,
                match_id="TEST_MATCH_3",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=2),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=64,
                champion_name="Lee Sin",
                champion_level=16,
                team_id=100,
                team_position="JUNGLE",
                individual_position="JUNGLE",
                lane="JUNGLE",
                role="NONE",
                kills=8,
                deaths=6,
                assists=12,
                kda=3.33,
                total_damage_dealt=90000,
                total_damage_dealt_to_champions=20000,
                total_damage_taken=30000,
                damage_self_mitigated=20000,
                largest_killing_spree=3,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=13000,
                gold_spent=12500,
                total_minions_killed=150,
                neutral_minions_killed=100,
                vision_score=40,
                wards_placed=20,
                wards_killed=12,
                vision_wards_bought_in_game=8,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=4,
                objective_stolen=2,
                total_heal=8000,
                total_heals_on_teammates=2000,
                total_damage_shielded_on_teammates=1000,
                total_time_cc_dealt=40,
                time_ccing_others=40,
                win=True,
                first_blood_kill=True,
                first_blood_assist=False,
                first_tower_kill=False,
                first_tower_assist=True,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1850,
                item0=3074,
                item1=3047,
                item2=3053,
                item3=3065,
                item4=3742,
                item5=0,
                item6=3364,
                summoner1_id=11,
                summoner2_id=4,
            ),
        ]

        for p in participants:
            async_session.add(p)
        await async_session.commit()

        service = StatsService(async_session)
        stats = await service.get_stats_by_role(sample_player.puuid)

        # Should have 2 roles (MIDDLE with 2 games, JUNGLE with 1 game)
        assert len(stats) == 2

        # Stats should be sorted by game count (MIDDLE first)
        middle_stats = stats[0]
        assert middle_stats.group_key == "MIDDLE"
        assert middle_stats.game_count == 2
        assert middle_stats.avg_kills == 11.0  # (10 + 12) / 2

        jungle_stats = stats[1]
        assert jungle_stats.group_key == "JUNGLE"
        assert jungle_stats.game_count == 1

    @pytest.mark.asyncio
    async def test_get_nth_recent_game_first_game(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting the most recent game."""
        base_time = datetime.now()

        # Add 3 games with different times
        for i in range(3):
            participant = MatchParticipant(
                match_db_id=i + 1,
                match_id=f"TEST_MATCH_{i + 1}",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=i),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10 + i,  # Different kills to distinguish games
                deaths=5,
                assists=8,
                kda=3.6,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=25000,
                total_damage_taken=20000,
                damage_self_mitigated=15000,
                largest_killing_spree=5,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=15000,
                gold_spent=14500,
                total_minions_killed=200,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=15,
                wards_killed=8,
                vision_wards_bought_in_game=5,
                turret_kills=2,
                turret_takedowns=3,
                inhibitor_kills=1,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=2,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=1000,
                total_damage_shielded_on_teammates=2000,
                total_time_cc_dealt=30,
                time_ccing_others=30,
                win=True,
                first_blood_kill=False,
                first_blood_assist=True,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=3031,
                item1=3006,
                item2=3094,
                item3=3072,
                item4=3026,
                item5=3139,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            )
            async_session.add(participant)
        await async_session.commit()

        service = StatsService(async_session)

        # Get most recent game (n=1)
        game = await service.get_nth_recent_game(sample_player.puuid, n=1)

        assert game is not None
        assert game.match_id == "TEST_MATCH_1"  # Most recent
        assert game.kills == 10  # First game

    @pytest.mark.asyncio
    async def test_get_nth_recent_game_second_game(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting the second most recent game."""
        base_time = datetime.now()

        # Add 3 games
        for i in range(3):
            participant = MatchParticipant(
                match_db_id=i + 1,
                match_id=f"TEST_MATCH_{i + 1}",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=i),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10 + i,
                deaths=5,
                assists=8,
                kda=3.6,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=25000,
                total_damage_taken=20000,
                damage_self_mitigated=15000,
                largest_killing_spree=5,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=15000,
                gold_spent=14500,
                total_minions_killed=200,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=15,
                wards_killed=8,
                vision_wards_bought_in_game=5,
                turret_kills=2,
                turret_takedowns=3,
                inhibitor_kills=1,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=2,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=1000,
                total_damage_shielded_on_teammates=2000,
                total_time_cc_dealt=30,
                time_ccing_others=30,
                win=True,
                first_blood_kill=False,
                first_blood_assist=True,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=3031,
                item1=3006,
                item2=3094,
                item3=3072,
                item4=3026,
                item5=3139,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            )
            async_session.add(participant)
        await async_session.commit()

        service = StatsService(async_session)

        # Get second most recent game (n=2)
        game = await service.get_nth_recent_game(sample_player.puuid, n=2)

        assert game is not None
        assert game.match_id == "TEST_MATCH_2"
        assert game.kills == 11  # Second game

    @pytest.mark.asyncio
    async def test_get_nth_recent_game_out_of_bounds(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting game with index out of bounds."""
        # Add only 2 games
        base_time = datetime.now()
        for i in range(2):
            participant = MatchParticipant(
                match_db_id=i + 1,
                match_id=f"TEST_MATCH_{i + 1}",
                puuid=sample_player.puuid,
                player_id=sample_player.id,
                game_creation=base_time - timedelta(hours=i),
                summoner_name=sample_player.game_name,
                profile_icon=1,
                summoner_level=100,
                champion_id=157,
                champion_name="Yasuo",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10,
                deaths=5,
                assists=8,
                kda=3.6,
                total_damage_dealt=100000,
                total_damage_dealt_to_champions=25000,
                total_damage_taken=20000,
                damage_self_mitigated=15000,
                largest_killing_spree=5,
                largest_multi_kill=2,
                killing_sprees=2,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                penta_kills=0,
                gold_earned=15000,
                gold_spent=14500,
                total_minions_killed=200,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=15,
                wards_killed=8,
                vision_wards_bought_in_game=5,
                turret_kills=2,
                turret_takedowns=3,
                inhibitor_kills=1,
                inhibitor_takedowns=1,
                baron_kills=1,
                dragon_kills=2,
                objective_stolen=0,
                total_heal=5000,
                total_heals_on_teammates=1000,
                total_damage_shielded_on_teammates=2000,
                total_time_cc_dealt=30,
                time_ccing_others=30,
                win=True,
                first_blood_kill=False,
                first_blood_assist=True,
                first_tower_kill=False,
                first_tower_assist=False,
                game_ended_in_surrender=False,
                game_ended_in_early_surrender=False,
                time_played=1800,
                item0=3031,
                item1=3006,
                item2=3094,
                item3=3072,
                item4=3026,
                item5=3139,
                item6=3340,
                summoner1_id=4,
                summoner2_id=14,
            )
            async_session.add(participant)
        await async_session.commit()

        service = StatsService(async_session)

        # Try to get 5th most recent game (doesn't exist)
        game = await service.get_nth_recent_game(sample_player.puuid, n=5)

        assert game is None

    @pytest.mark.asyncio
    async def test_get_nth_recent_game_invalid_index(
        self,
        async_session: AsyncSession,
        sample_player: TrackedPlayer,
    ) -> None:
        """Test getting game with invalid index (< 1)."""
        service = StatsService(async_session)

        # Try to get 0th game (invalid)
        game = await service.get_nth_recent_game(sample_player.puuid, n=0)

        assert game is None

        # Try to get -1th game (invalid)
        game = await service.get_nth_recent_game(sample_player.puuid, n=-1)

        assert game is None
