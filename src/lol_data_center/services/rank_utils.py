"""Utilities for rank and ELO calculations."""

# ELO base values for each tier
# These are approximate values used to convert League ranks to a numeric ELO scale
TIER_BASE_ELO = {
    "IRON": 0,
    "BRONZE": 400,
    "SILVER": 800,
    "GOLD": 1200,
    "PLATINUM": 1600,
    "EMERALD": 2000,
    "DIAMOND": 2400,
    "MASTER": 2800,
    "GRANDMASTER": 3200,
    "CHALLENGER": 3600,
}

# Division values (I = highest, IV = lowest within a tier)
DIVISION_ELO = {
    "I": 300,
    "II": 200,
    "III": 100,
    "IV": 0,
}


def calculate_elo(tier: str, rank: str, league_points: int) -> int:
    """Calculate approximate ELO from League rank components.

    This converts League of Legends rank (Tier/Division/LP) into a single
    numeric ELO value for graphing and comparison.

    Args:
        tier: Tier name (IRON, BRONZE, SILVER, GOLD, PLATINUM, EMERALD,
            DIAMOND, MASTER, GRANDMASTER, CHALLENGER)
        rank: Division (I, II, III, IV) - not used for Master+
        league_points: LP within the current division (0-100)

    Returns:
        Calculated ELO value

    Examples:
        >>> calculate_elo("GOLD", "II", 50)
        1450
        >>> calculate_elo("MASTER", "I", 100)
        2900
    """
    tier = tier.upper()
    rank = rank.upper()

    # Base ELO from tier
    elo = TIER_BASE_ELO.get(tier, 0)

    # For Master+ tiers, rank division doesn't apply, only LP matters
    if tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        # Each LP is worth 1 point
        elo += league_points
    else:
        # For lower tiers, add division value
        elo += DIVISION_ELO.get(rank, 0)
        # LP is worth 1 point (max 100 LP per division)
        elo += league_points

    return elo


def format_rank(tier: str, rank: str, league_points: int) -> str:
    """Format rank as human-readable string.

    Args:
        tier: Tier name
        rank: Division
        league_points: LP

    Returns:
        Formatted rank string

    Examples:
        >>> format_rank("GOLD", "II", 50)
        "Gold II - 50 LP"
        >>> format_rank("MASTER", "I", 100)
        "Master - 100 LP"
    """
    tier_formatted = tier.capitalize()

    # Master+ tiers don't use divisions
    if tier.upper() in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return f"{tier_formatted} - {league_points} LP"

    return f"{tier_formatted} {rank} - {league_points} LP"
