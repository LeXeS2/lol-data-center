"""Tests for Riot API schemas."""

import pytest
from pydantic import ValidationError

from lol_data_center.schemas.riot_api import (
    AccountDto,
    MatchDto,
    ParticipantDto,
)


class TestAccountDto:
    """Tests for AccountDto schema."""

    def test_valid_account(self):
        """Test creating a valid account."""
        account = AccountDto(
            puuid="test-puuid-12345",
            gameName="TestPlayer",
            tagLine="EUW",
        )

        assert account.puuid == "test-puuid-12345"
        assert account.game_name == "TestPlayer"
        assert account.tag_line == "EUW"

    def test_alias_mapping(self):
        """Test that alias mapping works correctly."""
        data = {
            "puuid": "test-puuid",
            "gameName": "Player",
            "tagLine": "TAG",
        }

        account = AccountDto.model_validate(data)
        assert account.game_name == "Player"
        assert account.tag_line == "TAG"

    def test_missing_required_field(self):
        """Test that missing required fields raise error."""
        with pytest.raises(ValidationError):
            AccountDto(puuid="test")  # Missing gameName and tagLine


class TestParticipantDto:
    """Tests for ParticipantDto schema."""

    def test_kda_property_with_deaths(self):
        """Test KDA calculation with deaths."""
        participant = ParticipantDto(
            puuid="test",
            summonerName="Test",
            summonerId=None,  # No longer returned by API
            profileIcon=1,
            summonerLevel=30,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            kills=10,
            deaths=2,
            assists=6,
            totalDamageDealt=100000,
            totalDamageDealtToChampions=50000,
            totalDamageTaken=20000,
            damageSelfMitigated=5000,
            goldEarned=12000,
            goldSpent=11000,
            totalMinionsKilled=150,
            neutralMinionsKilled=20,
            win=True,
            summoner1Id=4,
            summoner2Id=12,
        )

        # KDA = (10 + 6) / 2 = 8.0
        assert participant.kda == 8.0

    def test_kda_property_with_zero_deaths(self):
        """Test KDA calculation with zero deaths."""
        participant = ParticipantDto(
            puuid="test",
            summonerName="Test",
            summonerId=None,  # No longer returned by API
            profileIcon=1,
            summonerLevel=30,
            championId=1,
            championName="Annie",
            champLevel=18,
            teamId=100,
            kills=10,
            deaths=0,
            assists=5,
            totalDamageDealt=100000,
            totalDamageDealtToChampions=50000,
            totalDamageTaken=20000,
            damageSelfMitigated=5000,
            goldEarned=12000,
            goldSpent=11000,
            totalMinionsKilled=150,
            neutralMinionsKilled=20,
            win=True,
            summoner1Id=4,
            summoner2Id=12,
        )

        # With 0 deaths, KDA = kills + assists
        assert participant.kda == 15.0

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "puuid": "test",
            "summonerName": "Test",
            "summonerId": None,  # No longer returned by API
            "profileIcon": 1,
            "summonerLevel": 30,
            "championId": 1,
            "championName": "Annie",
            "champLevel": 18,
            "teamId": 100,
            "kills": 5,
            "deaths": 3,
            "assists": 7,
            "totalDamageDealt": 100000,
            "totalDamageDealtToChampions": 50000,
            "totalDamageTaken": 20000,
            "damageSelfMitigated": 5000,
            "goldEarned": 12000,
            "goldSpent": 11000,
            "totalMinionsKilled": 150,
            "neutralMinionsKilled": 20,
            "win": True,
            "summoner1Id": 4,
            "summoner2Id": 12,
            "unknownField": "should be ignored",
        }

        # Should not raise an error
        participant = ParticipantDto.model_validate(data)
        assert participant.kills == 5


class TestMatchDto:
    """Tests for MatchDto schema."""

    def test_get_participant_by_puuid(self, sample_match_dto):
        """Test getting participant by PUUID."""
        participant = sample_match_dto.get_participant_by_puuid("test-puuid-12345")

        assert participant is not None
        assert participant.puuid == "test-puuid-12345"
        assert participant.champion_name == "Annie"

    def test_get_participant_by_puuid_not_found(self, sample_match_dto):
        """Test getting participant by PUUID when not found."""
        participant = sample_match_dto.get_participant_by_puuid("nonexistent-puuid")

        assert participant is None
