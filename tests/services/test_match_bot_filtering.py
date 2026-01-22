"""Tests for BOT participant filtering and DB match retrieval."""


from lol_data_center.schemas.riot_api import (
    MatchDto,
    MatchInfoDto,
    MatchMetadataDto,
    ParticipantDto,
)
from lol_data_center.services.match_service import MatchService


class TestMatchServiceBotFiltering:
    """Tests for BOT participant filtering."""

    def test_has_bot_participant_with_bot(self) -> None:
        """Test that has_bot_participant returns True when BOT is present."""
        # Create a match with a BOT participant
        participants = [
            ParticipantDto(
                puuid="BOT",
                summoner_name="Bot",
                profile_icon=0,
                summoner_level=1,
                champion_id=1,
                champion_name="Annie",
                champ_level=1,
                team_id=100,
                kills=0,
                deaths=0,
                assists=0,
                total_damage_dealt=0,
                total_damage_dealt_to_champions=0,
                total_damage_taken=0,
                damage_self_mitigated=0,
                gold_earned=0,
                gold_spent=0,
                total_minions_killed=0,
                neutral_minions_killed=0,
                win=False,
                summoner1_id=1,
                summoner2_id=1,
            ),
            ParticipantDto(
                puuid="real-player-puuid",
                summoner_name="RealPlayer",
                profile_icon=1,
                summoner_level=30,
                champion_id=2,
                champion_name="Ahri",
                champ_level=10,
                team_id=100,
                kills=5,
                deaths=2,
                assists=8,
                total_damage_dealt=10000,
                total_damage_dealt_to_champions=5000,
                total_damage_taken=3000,
                damage_self_mitigated=1000,
                gold_earned=10000,
                gold_spent=9000,
                total_minions_killed=150,
                neutral_minions_killed=20,
                win=True,
                summoner1_id=4,
                summoner2_id=7,
            ),
        ]

        match_data = MatchDto(
            metadata=MatchMetadataDto(
                data_version="2",
                match_id="EUW1_123456",
                participants=["BOT", "real-player-puuid"],
            ),
            info=MatchInfoDto(
                game_creation=1234567890000,
                game_duration=1800,
                game_id=123456,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                game_version="13.1.1",
                map_id=11,
                participants=participants,
                platform_id="EUW1",
                queue_id=420,
                teams=[],
            ),
        )

        assert MatchService.has_bot_participant(match_data) is True

    def test_has_bot_participant_without_bot(self) -> None:
        """Test that has_bot_participant returns False when no BOT is present."""
        participants = [
            ParticipantDto(
                puuid="real-player-puuid-1",
                summoner_name="Player1",
                profile_icon=1,
                summoner_level=30,
                champion_id=1,
                champion_name="Annie",
                champ_level=10,
                team_id=100,
                kills=5,
                deaths=2,
                assists=8,
                total_damage_dealt=10000,
                total_damage_dealt_to_champions=5000,
                total_damage_taken=3000,
                damage_self_mitigated=1000,
                gold_earned=10000,
                gold_spent=9000,
                total_minions_killed=150,
                neutral_minions_killed=20,
                win=True,
                summoner1_id=4,
                summoner2_id=7,
            ),
            ParticipantDto(
                puuid="real-player-puuid-2",
                summoner_name="Player2",
                profile_icon=2,
                summoner_level=40,
                champion_id=2,
                champion_name="Ahri",
                champ_level=10,
                team_id=200,
                kills=3,
                deaths=5,
                assists=10,
                total_damage_dealt=12000,
                total_damage_dealt_to_champions=6000,
                total_damage_taken=4000,
                damage_self_mitigated=1500,
                gold_earned=9000,
                gold_spent=8500,
                total_minions_killed=140,
                neutral_minions_killed=15,
                win=False,
                summoner1_id=4,
                summoner2_id=7,
            ),
        ]

        match_data = MatchDto(
            metadata=MatchMetadataDto(
                data_version="2",
                match_id="EUW1_123456",
                participants=["real-player-puuid-1", "real-player-puuid-2"],
            ),
            info=MatchInfoDto(
                game_creation=1234567890000,
                game_duration=1800,
                game_id=123456,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                game_version="13.1.1",
                map_id=11,
                participants=participants,
                platform_id="EUW1",
                queue_id=420,
                teams=[],
            ),
        )

        assert MatchService.has_bot_participant(match_data) is False
