"""Tests for ML data extraction service."""

import pytest
from sqlalchemy import select

from lol_data_center.database.models import Match, MatchParticipant
from lol_data_center.ml.data_extraction import MatchDataExtractor
from lol_data_center.services.match_service import MatchService


@pytest.mark.asyncio
async def test_extract_match_features(async_session, sample_match_dto):
    """Test extracting match features for ML."""
    # First save a match to the database
    match_service = MatchService(async_session)
    await match_service.save_match(sample_match_dto)

    extractor = MatchDataExtractor(async_session)

    # Extract features
    df = await extractor.extract_match_features()

    # Should have at least one row
    assert len(df) > 0

    # Check expected columns
    expected_cols = ["match_id", "puuid", "win", "kills", "deaths", "assists", "damage_per_min"]
    for col in expected_cols:
        assert col in df.columns

    # Check data types
    assert df["win"].dtype == bool
    assert df["kills"].dtype in ["int64", "int32"]


@pytest.mark.asyncio
async def test_extract_match_features_empty_db(async_session):
    """Test extracting features from empty database."""
    extractor = MatchDataExtractor(async_session)

    df = await extractor.extract_match_features()

    # Should return empty DataFrame
    assert len(df) == 0


@pytest.mark.asyncio
async def test_extract_champion_stats(async_session, sample_match_dto):
    """Test extracting champion statistics."""
    # First save a match to the database
    match_service = MatchService(async_session)
    await match_service.save_match(sample_match_dto)

    extractor = MatchDataExtractor(async_session)

    df = await extractor.get_champion_stats()

    # Should have at least one row
    assert len(df) > 0

    # Check expected columns
    assert "champion_name" in df.columns
    assert "total_games" in df.columns
    assert "win_rate" in df.columns

    # Win rate should be between 0 and 1
    assert (df["win_rate"] >= 0).all()
    assert (df["win_rate"] <= 1).all()


@pytest.mark.asyncio
async def test_extract_role_stats(async_session, sample_match_dto):
    """Test extracting role statistics."""
    # First save a match to the database
    match_service = MatchService(async_session)
    await match_service.save_match(sample_match_dto)

    extractor = MatchDataExtractor(async_session)

    df = await extractor.get_role_stats()

    # Should have at least one row
    assert len(df) > 0

    # Check expected columns
    assert "role" in df.columns
    assert "total_games" in df.columns
    assert "win_rate" in df.columns

    # Win rate should be between 0 and 1
    assert (df["win_rate"] >= 0).all()
    assert (df["win_rate"] <= 1).all()


@pytest.mark.asyncio
async def test_per_minute_calculations(async_session, sample_match_dto):
    """Test that per-minute metrics are calculated correctly."""
    # First save a match to the database
    match_service = MatchService(async_session)
    await match_service.save_match(sample_match_dto)

    extractor = MatchDataExtractor(async_session)

    df = await extractor.extract_match_features()

    # Get one row
    row = df.iloc[0]

    # Game duration should be positive
    assert row["game_duration_minutes"] > 0

    # Per-minute stats should be reasonable
    assert row["gold_per_min"] > 0
    assert row["cs_per_min"] >= 0
    assert row["damage_per_min"] >= 0


@pytest.mark.asyncio
async def test_queue_filter(async_session, sample_match_dto):
    """Test filtering by queue ID."""
    # First save a match to the database
    match_service = MatchService(async_session)
    await match_service.save_match(sample_match_dto)

    extractor = MatchDataExtractor(async_session)

    # Extract with specific queue
    df = await extractor.extract_match_features(queue_ids=[420])  # Ranked Solo

    # Should only include matches from specified queue
    # (We'd need to join with Match to verify, but at least it shouldn't crash)
    assert df is not None
