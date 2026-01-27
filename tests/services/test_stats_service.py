"""Tests for player statistics service."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import Match, MatchParticipant, TrackedPlayer
from lol_data_center.services.stats_service import (
    RANKED_FLEX_QUEUE_ID,
    RANKED_SOLO_QUEUE_ID,
    StatsService,
)


@pytest.mark.asyncio
async def test_get_player_stats_current_season(
    async_session: AsyncSession,
    sample_player: TrackedPlayer,
) -> None:
    """Test getting player stats for current season."""
    stats_service = StatsService(async_session)
    current_season = stats_service.get_current_season()

    # Create matches for current season
    champion_names = ["Annie", "Annie", "Annie", "Ahri", "Lux"]
    for i in range(5):
        match = Match(
            match_id=f"TEST_{i}",
            data_version="2",
            game_creation=datetime.now(UTC),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version=f"{current_season}.1.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=RANKED_SOLO_QUEUE_ID,
        )
        async_session.add(match)
        await async_session.flush()

        # Create participant (win 3 out of 5 games)
        participant = MatchParticipant(
            match_db_id=match.id,
            match_id=match.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match.game_creation,
            summoner_name=sample_player.game_name,
            summoner_id=sample_player.summoner_id,
            profile_icon=sample_player.profile_icon_id or 0,
            summoner_level=sample_player.summoner_level or 1,
            champion_id=1,
            champion_name=champion_names[i],
            champion_level=18,
            team_id=100,
            team_position="MID",
            individual_position="MID",
            lane="MID",
            role="SOLO",
            kills=10,
            deaths=5,
            assists=8,
            kda=3.6,
            total_damage_dealt=150000,
            total_damage_dealt_to_champions=50000,
            total_damage_taken=30000,
            damage_self_mitigated=15000,
            largest_killing_spree=5,
            largest_multi_kill=2,
            killing_sprees=2,
            double_kills=2,
            triple_kills=1,
            quadra_kills=0,
            penta_kills=0,
            gold_earned=12000,
            gold_spent=11500,
            total_minions_killed=180,
            neutral_minions_killed=20,
            vision_score=30,
            wards_placed=15,
            wards_killed=5,
            vision_wards_bought_in_game=3,
            turret_kills=2,
            turret_takedowns=4,
            inhibitor_kills=1,
            inhibitor_takedowns=1,
            baron_kills=1,
            dragon_kills=2,
            objective_stolen=0,
            total_heal=5000,
            total_heals_on_teammates=1000,
            total_damage_shielded_on_teammates=2000,
            total_time_cc_dealt=50,
            time_ccing_others=50,
            win=i < 3,  # First 3 games are wins
            first_blood_kill=i == 0,
            first_blood_assist=False,
            first_tower_kill=i == 1,
            first_tower_assist=False,
            game_ended_in_surrender=False,
            game_ended_in_early_surrender=False,
            time_played=1800,
            item0=3089,
            item1=3020,
            item2=3135,
            item3=3165,
            item4=3157,
            item5=3916,
            item6=3340,
            summoner1_id=4,
            summoner2_id=14,
        )
        async_session.add(participant)

    await async_session.commit()

    # Get stats
    stats = await stats_service.get_player_stats(sample_player.puuid)

    # Verify results
    assert stats.total_games == 5
    assert stats.total_wins == 3
    assert stats.win_rate == 60.0
    assert len(stats.top_champions) == 3
    assert stats.top_champions[0] == ("Annie", 3)
    assert stats.top_champions[1] == ("Ahri", 1)
    assert stats.top_champions[2] == ("Lux", 1)


@pytest.mark.asyncio
async def test_get_player_stats_no_ranked_games(
    async_session: AsyncSession,
    sample_player: TrackedPlayer,
) -> None:
    """Test error when player has no ranked games."""
    stats_service = StatsService(async_session)

    # Try to get stats for player with no matches
    with pytest.raises(ValueError, match="No ranked games found"):
        await stats_service.get_player_stats(sample_player.puuid)


@pytest.mark.asyncio
async def test_get_player_stats_filters_non_ranked(
    async_session: AsyncSession,
    sample_player: TrackedPlayer,
) -> None:
    """Test that non-ranked games are filtered out."""
    stats_service = StatsService(async_session)
    current_season = stats_service.get_current_season()

    # Create a normal game (non-ranked, queue_id=400)
    match = Match(
        match_id="NORMAL_GAME",
        data_version="2",
        game_creation=datetime.now(UTC),
        game_duration=1800,
        game_mode="CLASSIC",
        game_type="MATCHED_GAME",
        game_version=f"{current_season}.1.1",
        map_id=11,
        platform_id="EUW1",
        queue_id=400,  # Normal Draft Pick
    )
    async_session.add(match)
    await async_session.flush()

    participant = MatchParticipant(
        match_db_id=match.id,
        match_id=match.match_id,
        puuid=sample_player.puuid,
        player_id=sample_player.id,
        game_creation=match.game_creation,
        summoner_name=sample_player.game_name,
        summoner_id=sample_player.summoner_id,
        profile_icon=sample_player.profile_icon_id or 0,
        summoner_level=sample_player.summoner_level or 1,
        champion_id=1,
        champion_name="Annie",
        champion_level=18,
        team_id=100,
        team_position="MID",
        individual_position="MID",
        lane="MID",
        role="SOLO",
        kills=10,
        deaths=5,
        assists=8,
        kda=3.6,
        total_damage_dealt=150000,
        total_damage_dealt_to_champions=50000,
        total_damage_taken=30000,
        damage_self_mitigated=15000,
        largest_killing_spree=5,
        largest_multi_kill=2,
        killing_sprees=2,
        double_kills=2,
        triple_kills=1,
        quadra_kills=0,
        penta_kills=0,
        gold_earned=12000,
        gold_spent=11500,
        total_minions_killed=180,
        neutral_minions_killed=20,
        vision_score=30,
        wards_placed=15,
        wards_killed=5,
        vision_wards_bought_in_game=3,
        turret_kills=2,
        turret_takedowns=4,
        inhibitor_kills=1,
        inhibitor_takedowns=1,
        baron_kills=1,
        dragon_kills=2,
        objective_stolen=0,
        total_heal=5000,
        total_heals_on_teammates=1000,
        total_damage_shielded_on_teammates=2000,
        total_time_cc_dealt=50,
        time_ccing_others=50,
        win=True,
        first_blood_kill=False,
        first_blood_assist=False,
        first_tower_kill=False,
        first_tower_assist=False,
        game_ended_in_surrender=False,
        game_ended_in_early_surrender=False,
        time_played=1800,
        item0=3089,
        item1=3020,
        item2=3135,
        item3=3165,
        item4=3157,
        item5=3916,
        item6=3340,
        summoner1_id=4,
        summoner2_id=14,
    )
    async_session.add(participant)
    await async_session.commit()

    # Should raise error because normal game doesn't count
    with pytest.raises(ValueError, match="No ranked games found"):
        await stats_service.get_player_stats(sample_player.puuid)


@pytest.mark.asyncio
async def test_get_player_stats_filters_old_season(
    async_session: AsyncSession,
    sample_player: TrackedPlayer,
) -> None:
    """Test that old season games are filtered out."""
    stats_service = StatsService(async_session)
    current_season = stats_service.get_current_season()
    old_season = current_season - 1

    # Create a ranked game from previous season
    match = Match(
        match_id="OLD_SEASON_GAME",
        data_version="2",
        game_creation=datetime.now(UTC),
        game_duration=1800,
        game_mode="CLASSIC",
        game_type="MATCHED_GAME",
        game_version=f"{old_season}.23.5",  # Previous season
        map_id=11,
        platform_id="EUW1",
        queue_id=RANKED_SOLO_QUEUE_ID,
    )
    async_session.add(match)
    await async_session.flush()

    participant = MatchParticipant(
        match_db_id=match.id,
        match_id=match.match_id,
        puuid=sample_player.puuid,
        player_id=sample_player.id,
        game_creation=match.game_creation,
        summoner_name=sample_player.game_name,
        summoner_id=sample_player.summoner_id,
        profile_icon=sample_player.profile_icon_id or 0,
        summoner_level=sample_player.summoner_level or 1,
        champion_id=1,
        champion_name="Annie",
        champion_level=18,
        team_id=100,
        team_position="MID",
        individual_position="MID",
        lane="MID",
        role="SOLO",
        kills=10,
        deaths=5,
        assists=8,
        kda=3.6,
        total_damage_dealt=150000,
        total_damage_dealt_to_champions=50000,
        total_damage_taken=30000,
        damage_self_mitigated=15000,
        largest_killing_spree=5,
        largest_multi_kill=2,
        killing_sprees=2,
        double_kills=2,
        triple_kills=1,
        quadra_kills=0,
        penta_kills=0,
        gold_earned=12000,
        gold_spent=11500,
        total_minions_killed=180,
        neutral_minions_killed=20,
        vision_score=30,
        wards_placed=15,
        wards_killed=5,
        vision_wards_bought_in_game=3,
        turret_kills=2,
        turret_takedowns=4,
        inhibitor_kills=1,
        inhibitor_takedowns=1,
        baron_kills=1,
        dragon_kills=2,
        objective_stolen=0,
        total_heal=5000,
        total_heals_on_teammates=1000,
        total_damage_shielded_on_teammates=2000,
        total_time_cc_dealt=50,
        time_ccing_others=50,
        win=True,
        first_blood_kill=False,
        first_blood_assist=False,
        first_tower_kill=False,
        first_tower_assist=False,
        game_ended_in_surrender=False,
        game_ended_in_early_surrender=False,
        time_played=1800,
        item0=3089,
        item1=3020,
        item2=3135,
        item3=3165,
        item4=3157,
        item5=3916,
        item6=3340,
        summoner1_id=4,
        summoner2_id=14,
    )
    async_session.add(participant)
    await async_session.commit()

    # Should raise error because old season game doesn't count
    with pytest.raises(ValueError, match="No ranked games found"):
        await stats_service.get_player_stats(sample_player.puuid)


@pytest.mark.asyncio
async def test_get_player_stats_both_ranked_queues(
    async_session: AsyncSession,
    sample_player: TrackedPlayer,
) -> None:
    """Test that both ranked solo and flex games are counted."""
    stats_service = StatsService(async_session)
    current_season = stats_service.get_current_season()

    # Create one ranked solo game and one ranked flex game
    for i, queue_id in enumerate([RANKED_SOLO_QUEUE_ID, RANKED_FLEX_QUEUE_ID]):
        match = Match(
            match_id=f"RANKED_{i}",
            data_version="2",
            game_creation=datetime.now(UTC),
            game_duration=1800,
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version=f"{current_season}.1.1",
            map_id=11,
            platform_id="EUW1",
            queue_id=queue_id,
        )
        async_session.add(match)
        await async_session.flush()

        participant = MatchParticipant(
            match_db_id=match.id,
            match_id=match.match_id,
            puuid=sample_player.puuid,
            player_id=sample_player.id,
            game_creation=match.game_creation,
            summoner_name=sample_player.game_name,
            summoner_id=sample_player.summoner_id,
            profile_icon=sample_player.profile_icon_id or 0,
            summoner_level=sample_player.summoner_level or 1,
            champion_id=1,
            champion_name="Annie",
            champion_level=18,
            team_id=100,
            team_position="MID",
            individual_position="MID",
            lane="MID",
            role="SOLO",
            kills=10,
            deaths=5,
            assists=8,
            kda=3.6,
            total_damage_dealt=150000,
            total_damage_dealt_to_champions=50000,
            total_damage_taken=30000,
            damage_self_mitigated=15000,
            largest_killing_spree=5,
            largest_multi_kill=2,
            killing_sprees=2,
            double_kills=2,
            triple_kills=1,
            quadra_kills=0,
            penta_kills=0,
            gold_earned=12000,
            gold_spent=11500,
            total_minions_killed=180,
            neutral_minions_killed=20,
            vision_score=30,
            wards_placed=15,
            wards_killed=5,
            vision_wards_bought_in_game=3,
            turret_kills=2,
            turret_takedowns=4,
            inhibitor_kills=1,
            inhibitor_takedowns=1,
            baron_kills=1,
            dragon_kills=2,
            objective_stolen=0,
            total_heal=5000,
            total_heals_on_teammates=1000,
            total_damage_shielded_on_teammates=2000,
            total_time_cc_dealt=50,
            time_ccing_others=50,
            win=i == 0,  # Win first game, lose second
            first_blood_kill=False,
            first_blood_assist=False,
            first_tower_kill=False,
            first_tower_assist=False,
            game_ended_in_surrender=False,
            game_ended_in_early_surrender=False,
            time_played=1800,
            item0=3089,
            item1=3020,
            item2=3135,
            item3=3165,
            item4=3157,
            item5=3916,
            item6=3340,
            summoner1_id=4,
            summoner2_id=14,
        )
        async_session.add(participant)

    await async_session.commit()

    # Get stats - should include both games
    stats = await stats_service.get_player_stats(sample_player.puuid)

    assert stats.total_games == 2
    assert stats.total_wins == 1
    assert stats.win_rate == 50.0
