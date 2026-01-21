"""Tests for MatchService."""

import pytest
from unittest.mock import AsyncMock

from lol_data_center.services.match_service import MatchService


class TestMatchService:
    """Tests for MatchService."""

    @pytest.mark.asyncio
    async def test_match_exists_false(self, async_session):
        """Test match_exists returns False for non-existent match."""
        service = MatchService(async_session)

        exists = await service.match_exists("NONEXISTENT_12345")

        assert exists is False

    @pytest.mark.asyncio
    async def test_save_match(self, async_session, sample_match_dto):
        """Test saving a match to the database."""
        from sqlalchemy import select
        from lol_data_center.database.models import MatchParticipant

        service = MatchService(async_session)

        match = await service.save_match(sample_match_dto)

        assert match.match_id == "EUW1_12345678"
        assert match.game_mode == "CLASSIC"

        # Query participants separately to avoid lazy loading
        result = await async_session.execute(
            select(MatchParticipant).where(MatchParticipant.match_db_id == match.id)
        )
        participants = result.scalars().all()
        assert len(participants) == 10

    @pytest.mark.asyncio
    async def test_save_match_idempotent(self, async_session, sample_match_dto):
        """Test that saving the same match twice is idempotent."""
        service = MatchService(async_session)

        match1 = await service.save_match(sample_match_dto)
        match2 = await service.save_match(sample_match_dto)

        # Should return the same match
        assert match1.id == match2.id

    @pytest.mark.asyncio
    async def test_update_player_records(
        self,
        async_session,
        sample_player,
        sample_participant_dto,
    ):
        """Test updating player records."""
        service = MatchService(async_session)

        # Set kills higher than current max (15)
        sample_participant_dto.kills = 20

        broken_records = await service.update_player_records(
            sample_player,
            sample_participant_dto,
            "EUW1_12345678",
        )

        assert "kills" in broken_records
        assert broken_records["kills"] == (15, 20)  # Old, new

    @pytest.mark.asyncio
    async def test_get_recent_matches_for_player(
        self,
        async_session,
        sample_player,
        sample_match_dto,
    ):
        """Test getting recent matches for a player."""
        service = MatchService(async_session)

        # First save a match
        await service.save_match(sample_match_dto)

        # Get recent matches
        matches = await service.get_recent_matches_for_player(sample_player.puuid)

        assert len(matches) == 1
        assert matches[0].puuid == sample_player.puuid


class TestPercentileCalculation:
    """Tests for z-score based percentile calculation."""

    @pytest.mark.asyncio
    async def test_percentile_with_no_data(self, async_session):
        """Test percentile calculation with no data returns 0."""
        service = MatchService(async_session)
        
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
        )
        
        assert percentile == 0.0

    @pytest.mark.asyncio
    async def test_percentile_with_single_data_point(self, async_session):
        """Test percentile calculation with single data point returns 50th percentile."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create a match with only one participant
        match = Match(
            match_id="SINGLE_TEST",
            data_version="2",
            game_creation=datetime.utcnow(),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.flush()
        
        participant = MatchParticipant(
            match_db_id=match.id,
            match_id=match.match_id,
            puuid="single-puuid",
            game_creation=match.game_creation,
            summoner_name="SinglePlayer",
            champion_id=1,
            champion_name="TestChamp",
            champion_level=18,
            team_id=100,
            team_position="MIDDLE",
            individual_position="MIDDLE",
            lane="MIDDLE",
            role="SOLO",
            kills=10,
            deaths=5,
            assists=5,
            kda=2.0,
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
            total_minions_killed=150,
            neutral_minions_killed=20,
            vision_score=30,
            wards_placed=10,
            wards_killed=3,
            vision_wards_bought_in_game=2,
            turret_kills=1,
            turret_takedowns=2,
            inhibitor_kills=0,
            inhibitor_takedowns=0,
            baron_kills=0,
            dragon_kills=0,
            objective_stolen=0,
            total_heal=3000,
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
            profile_icon=1,
            summoner_level=100,
        )
        async_session.add(participant)
        await async_session.commit()
        
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
        )
        
        assert percentile == 50.0

    @pytest.mark.asyncio
    async def test_percentile_z_score_calculation(self, async_session):
        """Test percentile calculation using z-score with known distribution."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create a match
        match = Match(
            match_id="TEST_123",
            data_version="2",
            game_creation=datetime.utcnow(),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.flush()
        
        # Create participants with known kills distribution
        # Mean = 10, values: 5, 10, 15 (std dev will be calculated)
        kills_values = [5, 10, 15]
        for i, kills in enumerate(kills_values):
            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=f"puuid-{i}",
                game_creation=match.game_creation,
                summoner_name=f"Player{i}",
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=kills,
                deaths=5,
                assists=5,
                kda=2.0,
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
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=10,
                wards_killed=3,
                vision_wards_bought_in_game=2,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=0,
                objective_stolen=0,
                total_heal=3000,
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
                profile_icon=1,
                summoner_level=100,
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Test percentile for mean value (should be ~50th percentile)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
        )
        assert 45.0 <= percentile <= 55.0  # Allow some tolerance
        
        # Test percentile for high value (should be ~84th percentile for +1 std dev)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=15.0,
        )
        assert percentile > 80.0

    @pytest.mark.asyncio
    async def test_percentile_with_zero_std_dev(self, async_session):
        """Test percentile calculation when all values are the same (std dev = 0)."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create a match
        match = Match(
            match_id="TEST_456",
            data_version="2",
            game_creation=datetime.utcnow(),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.flush()
        
        # Create participants with identical kills (std dev = 0)
        for i in range(3):
            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=f"puuid-{i}",
                game_creation=match.game_creation,
                summoner_name=f"Player{i}",
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=10,  # All same value
                deaths=5,
                assists=5,
                kda=2.0,
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
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=10,
                wards_killed=3,
                vision_wards_bought_in_game=2,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=0,
                objective_stolen=0,
                total_heal=3000,
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
                profile_icon=1,
                summoner_level=100,
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Test with value equal to mean (should return 50)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
        )
        assert percentile == 50.0
        
        # Test with value above mean (should return 100)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=15.0,
        )
        assert percentile == 100.0
        
        # Test with value below mean (should return 0)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=5.0,
        )
        assert percentile == 0.0

    @pytest.mark.asyncio
    async def test_percentile_with_champion_filter(self, async_session):
        """Test percentile calculation filtered by champion."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create a match
        match = Match(
            match_id="TEST_789",
            data_version="2",
            game_creation=datetime.utcnow(),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.flush()
        
        # Create participants with different champions
        # Champion 1: kills = 5, 10, 15 (mean = 10)
        # Champion 2: kills = 15, 20, 25 (mean = 20)
        for i in range(6):
            champion_id = 1 if i < 3 else 2
            kills = [5, 10, 15, 15, 20, 25][i]
            
            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=f"puuid-{i}",
                game_creation=match.game_creation,
                summoner_name=f"Player{i}",
                champion_id=champion_id,
                champion_name=f"Champ{champion_id}",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=kills,
                deaths=5,
                assists=5,
                kda=2.0,
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
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=10,
                wards_killed=3,
                vision_wards_bought_in_game=2,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=0,
                objective_stolen=0,
                total_heal=3000,
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
                profile_icon=1,
                summoner_level=100,
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Test percentile for champion 1 with value 10 (should be ~50th percentile)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
            champion_id=1,
        )
        assert 40.0 <= percentile <= 60.0
        
        # Test percentile for champion 2 with value 10 (should be very low)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
            champion_id=2,
        )
        assert percentile < 10.0

    @pytest.mark.asyncio
    async def test_percentile_with_role_filter(self, async_session):
        """Test percentile calculation filtered by role."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create a match
        match = Match(
            match_id="TEST_ABC",
            data_version="2",
            game_creation=datetime.utcnow(),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=420,
        )
        async_session.add(match)
        await async_session.flush()
        
        # Create participants with different roles
        # MIDDLE: kills = 5, 10, 15 (mean = 10)
        # JUNGLE: kills = 15, 20, 25 (mean = 20)
        for i in range(6):
            role = "MIDDLE" if i < 3 else "JUNGLE"
            kills = [5, 10, 15, 15, 20, 25][i]
            
            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=f"puuid-{i}",
                game_creation=match.game_creation,
                summoner_name=f"Player{i}",
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position=role,
                individual_position=role,
                lane=role,
                role="SOLO" if role == "MIDDLE" else "NONE",
                kills=kills,
                deaths=5,
                assists=5,
                kda=2.0,
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
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=10,
                wards_killed=3,
                vision_wards_bought_in_game=2,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=0,
                objective_stolen=0,
                total_heal=3000,
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
                profile_icon=1,
                summoner_level=100,
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Test percentile for MIDDLE role with value 10 (should be ~50th percentile)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
            role="MIDDLE",
        )
        assert 40.0 <= percentile <= 60.0
        
        # Test percentile for JUNGLE role with value 10 (should be very low)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
            role="JUNGLE",
        )
        assert percentile < 10.0

    @pytest.mark.asyncio
    async def test_percentile_with_puuid_filter(self, async_session, sample_player):
        """Test percentile calculation filtered by player PUUID."""
        from lol_data_center.database.models import Match, MatchParticipant
        from datetime import datetime
        
        service = MatchService(async_session)
        
        # Create participants - some for sample_player, some for others
        # Each participant needs to be in a separate match (or have unique puuid per match)
        # sample_player: kills = 5, 10, 15 (mean = 10)
        # others: kills = 20, 25, 30 (mean = 25)
        for i in range(6):
            puuid = sample_player.puuid if i < 3 else f"other-puuid-{i}"
            kills = [5, 10, 15, 20, 25, 30][i]
            
            # Create a separate match for each participant
            match = Match(
                match_id=f"TEST_DEF_{i}",
                data_version="2",
                game_creation=datetime.utcnow(),
                game_duration=1800,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                game_version="14.1",
                map_id=11,
                platform_id="EUW1",
                queue_id=420,
            )
            async_session.add(match)
            await async_session.flush()
            
            participant = MatchParticipant(
                match_db_id=match.id,
                match_id=match.match_id,
                puuid=puuid,
                game_creation=match.game_creation,
                summoner_name=f"Player{i}",
                champion_id=1,
                champion_name="TestChamp",
                champion_level=18,
                team_id=100,
                team_position="MIDDLE",
                individual_position="MIDDLE",
                lane="MIDDLE",
                role="SOLO",
                kills=kills,
                deaths=5,
                assists=5,
                kda=2.0,
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
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=30,
                wards_placed=10,
                wards_killed=3,
                vision_wards_bought_in_game=2,
                turret_kills=1,
                turret_takedowns=2,
                inhibitor_kills=0,
                inhibitor_takedowns=0,
                baron_kills=0,
                dragon_kills=0,
                objective_stolen=0,
                total_heal=3000,
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
                profile_icon=1,
                summoner_level=100,
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Test percentile for sample_player with value 10 (should be ~50th percentile)
        percentile = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
            puuid=sample_player.puuid,
        )
        assert 40.0 <= percentile <= 60.0
        
        # Test percentile for all players with value 10 (should be lower)
        percentile_all = await service.get_player_stats_percentile(
            stat_field="kills",
            value=10.0,
        )
        assert percentile_all < percentile  # Should be lower when including high-kill players

