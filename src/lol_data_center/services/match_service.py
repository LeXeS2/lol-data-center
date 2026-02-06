"""Match data management service."""

from typing import TYPE_CHECKING

from scipy.stats import norm  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lol_data_center.database.models import Match, MatchParticipant, PlayerRecord, TrackedPlayer
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.riot_api import (
    MatchDto,
    MatchInfoDto,
    MatchMetadataDto,
    ParticipantDto,
)

if TYPE_CHECKING:
    from lol_data_center.api_client.riot_client import Region, RiotApiClient

logger = get_logger(__name__)


class MatchService:
    """Service for managing match data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the match service.

        Args:
            session: Database session
        """
        self._session = session

    async def match_exists(self, match_id: str) -> bool:
        """Check if a match already exists in the database.

        Args:
            match_id: The match ID to check

        Returns:
            True if match exists
        """
        result = await self._session.execute(
            select(Match.id).where(Match.match_id == match_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def save_match(self, match_data: MatchDto) -> Match:
        """Save a match and all participants to the database.

        This method is safe for concurrent execution. If multiple processes try to save
        the same match simultaneously, the database will handle the conflict gracefully.

        Args:
            match_data: Validated match data from the API

        Returns:
            The saved Match instance
        """
        # Check if match already exists
        if await self.match_exists(match_data.metadata.match_id):
            logger.debug(
                "Match already exists, skipping",
                match_id=match_data.metadata.match_id,
            )
            result = await self._session.execute(
                select(Match).where(Match.match_id == match_data.metadata.match_id)
            )
            return result.scalar_one()

        # Prepare match data
        match_values = {
            "match_id": match_data.metadata.match_id,
            "data_version": match_data.metadata.data_version,
            "game_creation": match_data.info.game_creation_datetime,
            "game_duration": match_data.info.game_duration,
            "game_end_timestamp": match_data.info.game_end_datetime,
            "game_mode": match_data.info.game_mode,
            "game_name": match_data.info.game_name,
            "game_type": match_data.info.game_type,
            "game_version": match_data.info.game_version,
            "map_id": match_data.info.map_id,
            "platform_id": match_data.info.platform_id,
            "queue_id": match_data.info.queue_id,
            "tournament_code": match_data.info.tournament_code,
        }

        try:
            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for match
            stmt = insert(Match).values(**match_values)
            stmt = stmt.on_conflict_do_nothing(index_elements=["match_id"])
            await self._session.execute(stmt)
            await self._session.flush()

            # Fetch the match (either just inserted or already existing)
            result = await self._session.execute(
                select(Match).where(Match.match_id == match_data.metadata.match_id)
            )
            match = result.scalar_one()

            # Create participant records using ON CONFLICT for each participant
            for participant in match_data.info.participants:
                # Check if this participant is a tracked player
                player_result = await self._session.execute(
                    select(TrackedPlayer.id).where(TrackedPlayer.puuid == participant.puuid)
                )
                player_id = player_result.scalar_one_or_none()

                participant_values = {
                    "match_db_id": match.id,
                    "match_id": match.match_id,
                    "puuid": participant.puuid,
                    "player_id": player_id,
                    "game_creation": match.game_creation,
                    # Player info
                    "summoner_name": participant.summoner_name,
                    "summoner_id": participant.summoner_id,
                    "riot_id_game_name": participant.riot_id_game_name,
                    "riot_id_tagline": participant.riot_id_tagline,
                    "profile_icon": participant.profile_icon,
                    "summoner_level": participant.summoner_level,
                    # Champion & Role
                    "champion_id": participant.champion_id,
                    "champion_name": participant.champion_name,
                    "champion_level": participant.champ_level,
                    "team_id": participant.team_id,
                    "team_position": participant.team_position,
                    "individual_position": participant.individual_position,
                    "lane": participant.lane,
                    "role": participant.role,
                    # Core Stats
                    "kills": participant.kills,
                    "deaths": participant.deaths,
                    "assists": participant.assists,
                    "kda": participant.kda,
                    # Combat Stats
                    "total_damage_dealt": participant.total_damage_dealt,
                    "total_damage_dealt_to_champions": participant.total_damage_dealt_to_champions,
                    "total_damage_taken": participant.total_damage_taken,
                    "damage_self_mitigated": participant.damage_self_mitigated,
                    "largest_killing_spree": participant.largest_killing_spree,
                    "largest_multi_kill": participant.largest_multi_kill,
                    "killing_sprees": participant.killing_sprees,
                    "double_kills": participant.double_kills,
                    "triple_kills": participant.triple_kills,
                    "quadra_kills": participant.quadra_kills,
                    "penta_kills": participant.penta_kills,
                    # Economy
                    "gold_earned": participant.gold_earned,
                    "gold_spent": participant.gold_spent,
                    "total_minions_killed": participant.total_minions_killed,
                    "neutral_minions_killed": participant.neutral_minions_killed,
                    # Vision
                    "vision_score": participant.vision_score,
                    "wards_placed": participant.wards_placed,
                    "wards_killed": participant.wards_killed,
                    "vision_wards_bought_in_game": participant.vision_wards_bought_in_game,
                    # Objectives
                    "turret_kills": participant.turret_kills,
                    "turret_takedowns": participant.turret_takedowns,
                    "inhibitor_kills": participant.inhibitor_kills,
                    "inhibitor_takedowns": participant.inhibitor_takedowns,
                    "baron_kills": participant.baron_kills,
                    "dragon_kills": participant.dragon_kills,
                    "objective_stolen": participant.objectives_stolen,
                    # Utility
                    "total_heal": participant.total_heal,
                    "total_heals_on_teammates": participant.total_heals_on_teammates,
                    "total_damage_shielded_on_teammates": participant.total_damage_shielded_on_teammates,
                    "total_time_cc_dealt": participant.total_time_cc_dealt,
                    "time_ccing_others": participant.time_ccing_others,
                    # Game State
                    "win": participant.win,
                    "first_blood_kill": participant.first_blood_kill,
                    "first_blood_assist": participant.first_blood_assist,
                    "first_tower_kill": participant.first_tower_kill,
                    "first_tower_assist": participant.first_tower_assist,
                    "game_ended_in_surrender": participant.game_ended_in_surrender,
                    "game_ended_in_early_surrender": participant.game_ended_in_early_surrender,
                    "time_played": participant.time_played,
                    # Items
                    "item0": participant.item0,
                    "item1": participant.item1,
                    "item2": participant.item2,
                    "item3": participant.item3,
                    "item4": participant.item4,
                    "item5": participant.item5,
                    "item6": participant.item6,
                    # Spells
                    "summoner1_id": participant.summoner1_id,
                    "summoner2_id": participant.summoner2_id,
                    # ML Predictions
                    "predicted_win_probability": participant.predicted_win_probability,
                }

                # Use ON CONFLICT DO NOTHING for participant
                participant_stmt = insert(MatchParticipant).values(**participant_values)
                participant_stmt = participant_stmt.on_conflict_do_nothing(
                    constraint="uq_match_participant"
                )
                await self._session.execute(participant_stmt)

            await self._session.commit()

            logger.info(
                "Saved match",
                match_id=match.match_id,
                game_mode=match.game_mode,
                participants=len(match_data.info.participants),
            )

            return match

        except IntegrityError as e:
            # Rollback and try to fetch existing match as fallback
            await self._session.rollback()
            logger.warning(
                "IntegrityError while saving match, fetching existing",
                match_id=match_data.metadata.match_id,
                error=str(e),
            )
            result = await self._session.execute(
                select(Match).where(Match.match_id == match_data.metadata.match_id)
            )
            return result.scalar_one()

    async def save_match_with_timeline(
        self,
        match_data: MatchDto,
        api_client: "RiotApiClient",
        region: "Region",
        filter_events: bool = True,
    ) -> Match:
        """Save a match with timeline data.

        This method saves the match and then fetches and saves timeline data.
        If the match already exists, timeline data will still be fetched if missing.

        Args:
            match_data: Validated match data from the API
            api_client: Riot API client to fetch timeline data
            region: Region for API requests
            filter_events: If True, only save events involving tracked players

        Returns:
            The saved Match instance
        """
        from lol_data_center.api_client.validation import ValidationError
        from lol_data_center.services.timeline_service import TimelineService

        # Save match data first
        match = await self.save_match(match_data)

        # Check if timeline already exists
        timeline_service = TimelineService(self._session)
        if await timeline_service.timeline_exists(match_data.metadata.match_id):
            logger.debug(
                "Timeline already exists, skipping fetch",
                match_id=match_data.metadata.match_id,
            )
            return match

        # Fetch and save timeline
        try:
            timeline_data = await api_client.get_match_timeline(
                match_data.metadata.match_id, region
            )
            await timeline_service.save_timeline(
                timeline_data,
                match.id,
                filter_events=filter_events,
            )
        except ValidationError as e:
            logger.error(
                "Failed to save timeline - validation error",
                match_id=match_data.metadata.match_id,
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "Failed to save timeline",
                match_id=match_data.metadata.match_id,
                error=str(e),
            )

        return match

    async def update_player_records(
        self,
        player: TrackedPlayer,
        participant: ParticipantDto,
        match_id: str,
    ) -> dict[str, tuple[float, float]]:
        """Update player records based on new match data.

        Args:
            player: The tracked player
            participant: The player's stats in the match
            match_id: The match ID

        Returns:
            Dictionary of records that were broken: {stat_name: (old_value, new_value)}
        """
        # Get or create player records
        result = await self._session.execute(
            select(PlayerRecord).where(PlayerRecord.player_id == player.id)
        )
        records = result.scalar_one_or_none()

        if records is None:
            records = PlayerRecord(player_id=player.id)
            self._session.add(records)

        broken_records: dict[str, tuple[float, float]] = {}

        # Check maximum records
        record_checks = [
            ("kills", participant.kills, "max_kills", "max_kills_match_id"),
            ("deaths", participant.deaths, "max_deaths", "max_deaths_match_id"),
            ("assists", participant.assists, "max_assists", "max_assists_match_id"),
            ("kda", participant.kda, "max_kda", "max_kda_match_id"),
            (
                "total_minions_killed",
                participant.total_minions_killed,
                "max_cs",
                "max_cs_match_id",
            ),
            (
                "total_damage_dealt_to_champions",
                participant.total_damage_dealt_to_champions,
                "max_damage_to_champions",
                "max_damage_match_id",
            ),
            ("vision_score", participant.vision_score, "max_vision_score", "max_vision_match_id"),
            ("gold_earned", participant.gold_earned, "max_gold", "max_gold_match_id"),
        ]

        for stat_name, new_value, record_field, match_field in record_checks:
            old_value = getattr(records, record_field)
            if new_value > old_value:
                broken_records[stat_name] = (old_value, new_value)
                setattr(records, record_field, new_value)
                setattr(records, match_field, match_id)

        # Check minimum records (deaths, excluding 0)
        if participant.deaths > 0 and (
            records.min_deaths is None or participant.deaths < records.min_deaths
        ):
            broken_records["min_deaths"] = (
                records.min_deaths or float("inf"),
                participant.deaths,
            )
            records.min_deaths = participant.deaths
            records.min_deaths_match_id = match_id

        # Update game counts
        records.total_games += 1
        if participant.win:
            records.total_wins += 1
        else:
            records.total_losses += 1

        await self._session.commit()

        if broken_records:
            logger.info(
                "Player broke records",
                player_id=player.id,
                riot_id=player.riot_id,
                records=broken_records,
            )

        return broken_records

    async def get_player_stats_percentile(
        self,
        stat_field: str,
        value: float,
        puuid: str | None = None,
        champion_id: int | None = None,
        role: str | None = None,
    ) -> float:
        """Calculate the percentile rank of a stat value using z-score.

        This method uses a more sophisticated approach than simple counting:
        1. Queries the mean and standard deviation for the stat
        2. Calculates the z-score: (value - mean) / std_dev
        3. Converts z-score to percentile using the cumulative distribution function

        The population can be filtered by champion and role for fairer comparisons.

        Args:
            stat_field: Name of the stat field (e.g., "kills")
            value: The value to calculate percentile for
            puuid: If provided, calculate percentile within player's own games only
            champion_id: If provided, only compare against games with this champion
            role: If provided, only compare against games with this role

        Returns:
            Percentile rank (0-100)
        """
        # Build the base query for statistics
        column = getattr(MatchParticipant, stat_field)

        # Build WHERE conditions
        conditions = []
        if puuid:
            conditions.append(MatchParticipant.puuid == puuid)
        if champion_id is not None:
            conditions.append(MatchParticipant.champion_id == champion_id)
        if role:
            conditions.append(MatchParticipant.individual_position == role)

        # Fetch all values for manual standard deviation calculation
        # This is necessary because SQLite doesn't support stddev_samp
        # NOTE: For very large datasets (thousands of matches), consider using database-level
        # aggregation or streaming approaches to reduce memory usage
        values_query = select(column).select_from(MatchParticipant)

        if conditions:
            values_query = values_query.where(*conditions)

        result = await self._session.execute(values_query)
        values = [row[0] for row in result.fetchall()]

        count = len(values)

        # Handle edge cases
        if count == 0:
            logger.warning(
                "No data for percentile calculation",
                stat_field=stat_field,
                puuid=puuid,
                champion_id=champion_id,
                role=role,
            )
            return 0.0

        if count == 1:
            # Only one data point - it's at the 50th percentile
            return 50.0

        # Calculate mean
        mean = sum(values) / count

        # Calculate standard deviation (sample)
        # Note: count > 1 is guaranteed by the check above, so division by (count - 1) is safe
        variance = sum((x - mean) ** 2 for x in values) / (count - 1)
        stddev = variance**0.5

        if stddev == 0:
            # No variance in data - all values are the same
            if value > mean:
                return 100.0
            elif value < mean:
                return 0.0
            else:
                return 50.0

        # Calculate z-score
        z_score = (value - mean) / stddev

        # Convert z-score to percentile using cumulative distribution function
        # norm.cdf returns value between 0 and 1, we convert to 0-100
        percentile = norm.cdf(z_score) * 100

        logger.debug(
            "Calculated percentile using z-score",
            stat_field=stat_field,
            value=value,
            mean=mean,
            stddev=stddev,
            z_score=z_score,
            percentile=percentile,
            count=count,
            champion_id=champion_id,
            role=role,
        )

        return float(percentile)

    async def get_recent_matches_for_player(
        self,
        puuid: str,
        limit: int = 20,
    ) -> list[MatchParticipant]:
        """Get recent match participations for a player.

        Args:
            puuid: Player PUUID
            limit: Maximum number of matches to return

        Returns:
            List of MatchParticipant records
        """
        result = await self._session.execute(
            select(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
            .order_by(MatchParticipant.game_creation.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_match_dto(self, match_id: str) -> MatchDto | None:
        """Retrieve a match from the database and convert it to MatchDto format.

        This allows reusing already-fetched matches instead of querying the Riot API again.

        Args:
            match_id: The match ID to retrieve

        Returns:
            MatchDto if match exists, None otherwise
        """
        # Load match with all participants
        result = await self._session.execute(
            select(Match)
            .options(selectinload(Match.participants))
            .where(Match.match_id == match_id)
        )
        match = result.scalar_one_or_none()

        if match is None:
            return None

        # Convert database models to DTOs
        participants_dto: list[ParticipantDto] = []
        puuids: list[str] = []

        for participant in match.participants:
            puuids.append(participant.puuid)

            # Reconstruct ParticipantDto from database model
            participant_dto = ParticipantDto(
                puuid=participant.puuid,
                summoner_name=participant.summoner_name,
                summoner_id=participant.summoner_id,
                riot_id_game_name=participant.riot_id_game_name,
                riot_id_tagline=participant.riot_id_tagline,
                profile_icon=participant.profile_icon,
                summoner_level=participant.summoner_level,
                champion_id=participant.champion_id,
                champion_name=participant.champion_name,
                champ_level=participant.champion_level,
                team_id=participant.team_id,
                team_position=participant.team_position,
                individual_position=participant.individual_position,
                lane=participant.lane,
                role=participant.role,
                kills=participant.kills,
                deaths=participant.deaths,
                assists=participant.assists,
                total_damage_dealt=participant.total_damage_dealt,
                total_damage_dealt_to_champions=participant.total_damage_dealt_to_champions,
                total_damage_taken=participant.total_damage_taken,
                damage_self_mitigated=participant.damage_self_mitigated,
                largest_killing_spree=participant.largest_killing_spree,
                largest_multi_kill=participant.largest_multi_kill,
                killing_sprees=participant.killing_sprees,
                double_kills=participant.double_kills,
                triple_kills=participant.triple_kills,
                quadra_kills=participant.quadra_kills,
                penta_kills=participant.penta_kills,
                gold_earned=participant.gold_earned,
                gold_spent=participant.gold_spent,
                total_minions_killed=participant.total_minions_killed,
                neutral_minions_killed=participant.neutral_minions_killed,
                vision_score=participant.vision_score,
                wards_placed=participant.wards_placed,
                wards_killed=participant.wards_killed,
                vision_wards_bought_in_game=participant.vision_wards_bought_in_game,
                turret_kills=participant.turret_kills,
                turret_takedowns=participant.turret_takedowns,
                inhibitor_kills=participant.inhibitor_kills,
                inhibitor_takedowns=participant.inhibitor_takedowns,
                baron_kills=participant.baron_kills,
                dragon_kills=participant.dragon_kills,
                objectives_stolen=participant.objective_stolen,
                total_heal=participant.total_heal,
                total_heals_on_teammates=participant.total_heals_on_teammates,
                total_damage_shielded_on_teammates=participant.total_damage_shielded_on_teammates,
                total_time_cc_dealt=participant.total_time_cc_dealt,
                time_ccing_others=participant.time_ccing_others,
                win=participant.win,
                first_blood_kill=participant.first_blood_kill,
                first_blood_assist=participant.first_blood_assist,
                first_tower_kill=participant.first_tower_kill,
                first_tower_assist=participant.first_tower_assist,
                game_ended_in_surrender=participant.game_ended_in_surrender,
                game_ended_in_early_surrender=participant.game_ended_in_early_surrender,
                time_played=participant.time_played,
                item0=participant.item0,
                item1=participant.item1,
                item2=participant.item2,
                item3=participant.item3,
                item4=participant.item4,
                item5=participant.item5,
                item6=participant.item6,
                summoner1_id=participant.summoner1_id,
                summoner2_id=participant.summoner2_id,
            )
            participants_dto.append(participant_dto)

        # Create metadata
        metadata = MatchMetadataDto(
            data_version=match.data_version,
            match_id=match.match_id,
            participants=puuids,
        )

        # Create info (note: teams data is not stored in DB, so we use empty list)
        info = MatchInfoDto(
            game_creation=int(match.game_creation.timestamp() * 1000),
            game_duration=match.game_duration,
            game_end_timestamp=(
                int(match.game_end_timestamp.timestamp() * 1000)
                if match.game_end_timestamp
                else None
            ),
            game_id=0,  # Not stored in DB
            game_mode=match.game_mode,
            game_name=match.game_name or "",
            game_type=match.game_type,
            game_version=match.game_version,
            map_id=match.map_id,
            participants=participants_dto,
            platform_id=match.platform_id,
            queue_id=match.queue_id,
            teams=[],  # Team data not stored in DB
            tournament_code=match.tournament_code,
        )

        return MatchDto(metadata=metadata, info=info)

    @staticmethod
    def has_bot_participant(match_data: MatchDto) -> bool:
        """Check if a match contains any BOT participants.

        Matches with BOT participants (AI games) should be filtered out.

        Args:
            match_data: Match data to check

        Returns:
            True if any participant has PUUID "BOT"
        """
        return any(p.puuid == "BOT" for p in match_data.info.participants)
