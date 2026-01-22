"""Seed script for champion data.

This script populates the champions table with basic champion information.
In production, this data should be fetched from Riot's Data Dragon API:
https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json
"""

import asyncio

from sqlalchemy import select

from lol_data_center.database.engine import get_async_session
from lol_data_center.database.models import Champion
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

# Basic champion data - in production, fetch from Data Dragon API
# This is a minimal subset for demonstration
CHAMPION_DATA = [
    {"id": 1, "key": "Annie", "name": "Annie", "title": "the Dark Child"},
    {"id": 2, "key": "Olaf", "name": "Olaf", "title": "the Berserker"},
    {"id": 3, "key": "Galio", "name": "Galio", "title": "the Colossus"},
    {"id": 4, "key": "TwistedFate", "name": "Twisted Fate", "title": "the Card Master"},
    {"id": 5, "key": "XinZhao", "name": "Xin Zhao", "title": "the Seneschal of Demacia"},
    {"id": 6, "key": "Urgot", "name": "Urgot", "title": "the Dreadnought"},
    {"id": 7, "key": "LeBlanc", "name": "LeBlanc", "title": "the Deceiver"},
    {"id": 8, "key": "Vladimir", "name": "Vladimir", "title": "the Crimson Reaper"},
    {"id": 9, "key": "Fiddlesticks", "name": "Fiddlesticks", "title": "the Ancient Fear"},
    {"id": 10, "key": "Kayle", "name": "Kayle", "title": "the Righteous"},
    {"id": 11, "key": "MasterYi", "name": "Master Yi", "title": "the Wuju Bladesman"},
    {"id": 12, "key": "Alistar", "name": "Alistar", "title": "the Minotaur"},
    {"id": 13, "key": "Ryze", "name": "Ryze", "title": "the Rune Mage"},
    {"id": 14, "key": "Sion", "name": "Sion", "title": "The Undead Juggernaut"},
    {"id": 15, "key": "Sivir", "name": "Sivir", "title": "the Battle Mistress"},
    {"id": 16, "key": "Soraka", "name": "Soraka", "title": "the Starchild"},
    {"id": 17, "key": "Teemo", "name": "Teemo", "title": "the Swift Scout"},
    {"id": 18, "key": "Tristana", "name": "Tristana", "title": "the Yordle Gunner"},
    {"id": 19, "key": "Warwick", "name": "Warwick", "title": "the Uncaged Wrath of Zaun"},
    {"id": 20, "key": "Nunu", "name": "Nunu & Willump", "title": "the Boy and His Yeti"},
    # Add more champions as needed - typically 160+ total
]


async def seed_champions() -> None:
    """Seed the champion data into the database."""
    async with get_async_session() as session:
        # Check if champions already exist
        result = await session.execute(select(Champion).limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("Champions already seeded, skipping")
            return

        # Insert champions
        for champ_data in CHAMPION_DATA:
            champion = Champion(
                id=champ_data["id"],
                key=champ_data["key"],
                name=champ_data["name"],
                title=champ_data.get("title"),
            )
            session.add(champion)

        await session.commit()
        logger.info("Seeded champions", count=len(CHAMPION_DATA))


async def update_champions_from_data_dragon() -> None:
    """Update champion data from Riot's Data Dragon API.

    This is a placeholder for future implementation that fetches
    the latest champion data from:
    https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json
    """
    # TODO: Implement Data Dragon integration
    logger.warning("Data Dragon integration not yet implemented")
    pass


if __name__ == "__main__":
    asyncio.run(seed_champions())
