"""Tests for rank utilities."""

from lol_data_center.services.rank_utils import calculate_elo, format_rank


def test_calculate_elo_bronze() -> None:
    """Test ELO calculation for Bronze tier."""
    # Bronze IV - 0 LP
    assert calculate_elo("BRONZE", "IV", 0) == 400

    # Bronze II - 50 LP
    assert calculate_elo("BRONZE", "II", 50) == 650

    # Bronze I - 100 LP
    assert calculate_elo("BRONZE", "I", 100) == 800


def test_calculate_elo_gold() -> None:
    """Test ELO calculation for Gold tier."""
    # Gold IV - 0 LP
    assert calculate_elo("GOLD", "IV", 0) == 1200

    # Gold II - 50 LP
    assert calculate_elo("GOLD", "II", 50) == 1450

    # Gold I - 75 LP
    assert calculate_elo("GOLD", "I", 75) == 1575


def test_calculate_elo_diamond() -> None:
    """Test ELO calculation for Diamond tier."""
    # Diamond III - 33 LP
    assert calculate_elo("DIAMOND", "III", 33) == 2533


def test_calculate_elo_master() -> None:
    """Test ELO calculation for Master tier (no divisions)."""
    # Master - 0 LP
    assert calculate_elo("MASTER", "I", 0) == 2800

    # Master - 100 LP
    assert calculate_elo("MASTER", "I", 100) == 2900

    # Master - 500 LP
    assert calculate_elo("MASTER", "I", 500) == 3300


def test_calculate_elo_challenger() -> None:
    """Test ELO calculation for Challenger tier."""
    # Challenger - 200 LP
    assert calculate_elo("CHALLENGER", "I", 200) == 3800


def test_calculate_elo_case_insensitive() -> None:
    """Test that tier and rank are case-insensitive."""
    assert calculate_elo("gold", "ii", 50) == 1450
    assert calculate_elo("Gold", "II", 50) == 1450
    assert calculate_elo("GOLD", "ii", 50) == 1450


def test_format_rank_lower_tiers() -> None:
    """Test rank formatting for lower tiers."""
    assert format_rank("GOLD", "II", 50) == "Gold II - 50 LP"
    assert format_rank("SILVER", "III", 25) == "Silver III - 25 LP"


def test_format_rank_master_plus() -> None:
    """Test rank formatting for Master+ tiers."""
    assert format_rank("MASTER", "I", 100) == "Master - 100 LP"
    assert format_rank("GRANDMASTER", "I", 250) == "Grandmaster - 250 LP"
    assert format_rank("CHALLENGER", "I", 500) == "Challenger - 500 LP"
