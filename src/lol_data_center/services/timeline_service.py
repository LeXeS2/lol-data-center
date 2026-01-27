"""Service for managing match timeline data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lol_data_center.database.models import (
    MatchTimeline,
    TimelineParticipantFrame,
    TrackedPlayer,
)
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.riot_api import EventDto, TimelineDto

logger = get_logger(__name__)


class TimelineService:
    """Service for handling match timeline operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self._session = session

    async def timeline_exists(self, match_id: str) -> bool:
        """Check if timeline data already exists for a match.

        Args:
            match_id: Match ID

        Returns:
            True if timeline exists
        """
        result = await self._session.execute(
            select(MatchTimeline).where(MatchTimeline.match_id == match_id)
        )
        return result.scalar_one_or_none() is not None

    async def _get_tracked_puuids(self) -> set[str]:
        """Get set of all tracked player PUUIDs.

        Returns:
            Set of tracked PUUIDs
        """
        result = await self._session.execute(select(TrackedPlayer.puuid))
        return {row[0] for row in result.all()}

    async def _filter_events_by_tracked_players(
        self,
        events: list[EventDto],
        participant_id_to_puuid: dict[int, str],
        tracked_puuids: set[str],
    ) -> list[EventDto]:
        """Filter events to only include those involving tracked players.

        An event is included if any of these fields reference a tracked player:
        - participantId
        - killerId
        - victimId
        - assistingParticipantIds
        - creatorId

        Args:
            events: All events from timeline
            participant_id_to_puuid: Mapping of participant ID to PUUID
            tracked_puuids: Set of tracked player PUUIDs

        Returns:
            Filtered list of events
        """
        filtered_events = []

        for event in events:
            # Check if event involves any tracked player
            involved_participant_ids: set[int] = set()

            if event.participant_id is not None:
                involved_participant_ids.add(event.participant_id)
            if event.killer_id is not None:
                involved_participant_ids.add(event.killer_id)
            if event.victim_id is not None:
                involved_participant_ids.add(event.victim_id)
            if event.creator_id is not None:
                involved_participant_ids.add(event.creator_id)
            if event.assisting_participant_ids:
                involved_participant_ids.update(event.assisting_participant_ids)

            # Check if any involved participant is tracked
            for participant_id in involved_participant_ids:
                puuid = participant_id_to_puuid.get(participant_id)
                if puuid and puuid in tracked_puuids:
                    filtered_events.append(event)
                    break

        return filtered_events

    async def save_timeline(
        self,
        timeline_dto: TimelineDto,
        match_db_id: int,
        filter_events: bool = True,
    ) -> MatchTimeline:
        """Save timeline data to database.

        Args:
            timeline_dto: Timeline data from Riot API
            match_db_id: Database ID of the match
            filter_events: If True, only save events involving tracked players

        Returns:
            Created MatchTimeline object
        """
        # Check if already exists
        if await self.timeline_exists(timeline_dto.metadata.match_id):
            logger.info(
                "Timeline already exists, skipping",
                match_id=timeline_dto.metadata.match_id,
            )
            result = await self._session.execute(
                select(MatchTimeline).where(
                    MatchTimeline.match_id == timeline_dto.metadata.match_id
                )
            )
            return result.scalar_one()

        # Get tracked player PUUIDs
        tracked_puuids = await self._get_tracked_puuids()

        # Build participant ID to PUUID mapping
        participant_id_to_puuid: dict[int, str] = {}
        for participant in timeline_dto.info.participants:
            if isinstance(participant, dict):
                participant_id = participant.get("participantId")
                puuid = participant.get("puuid")
                if isinstance(participant_id, int) and isinstance(puuid, str):
                    participant_id_to_puuid[participant_id] = puuid

        # Also use metadata participants (list of PUUIDs in order)
        for idx, puuid in enumerate(timeline_dto.metadata.participants, start=1):
            if idx not in participant_id_to_puuid:
                participant_id_to_puuid[idx] = puuid

        # Collect all events from all frames
        all_events: list[EventDto] = []
        for frame in timeline_dto.info.frames:
            all_events.extend(frame.events)

        # Filter events if requested
        if filter_events:
            all_events = await self._filter_events_by_tracked_players(
                all_events, participant_id_to_puuid, tracked_puuids
            )

        # Convert events to JSON-serializable dicts
        events_json = [event.model_dump(by_alias=True) for event in all_events]

        # Create timeline record
        timeline = MatchTimeline(
            match_db_id=match_db_id,
            match_id=timeline_dto.metadata.match_id,
            data_version=timeline_dto.metadata.data_version,
            frame_interval=timeline_dto.info.frame_interval,
            game_id=timeline_dto.info.game_id,
            events={"events": events_json},  # Store as dict with "events" key
            events_filtered=filter_events,
        )

        self._session.add(timeline)
        await self._session.flush()  # Get timeline.id

        # Save participant frames for tracked players only
        participant_frames_to_add: list[TimelineParticipantFrame] = []

        for frame in timeline_dto.info.frames:
            timestamp = frame.timestamp

            for participant_id_str, participant_frame in frame.participant_frames.items():
                participant_id = int(participant_id_str)
                puuid = participant_id_to_puuid.get(participant_id)

                # Only save frames for tracked players
                if not puuid or puuid not in tracked_puuids:
                    continue

                # Get player DB ID
                player_result = await self._session.execute(
                    select(TrackedPlayer.id).where(TrackedPlayer.puuid == puuid)
                )
                player_id = player_result.scalar_one_or_none()

                # Extract damage stats
                damage_stats = participant_frame.damage_stats or {}
                champion_stats = participant_frame.champion_stats or {}

                frame_record = TimelineParticipantFrame(
                    timeline_id=timeline.id,
                    match_id=timeline_dto.metadata.match_id,
                    puuid=puuid,
                    player_id=player_id,
                    timestamp=timestamp,
                    participant_id=participant_id,
                    level=participant_frame.level,
                    current_gold=participant_frame.current_gold,
                    total_gold=participant_frame.total_gold,
                    gold_per_second=participant_frame.gold_per_second,
                    xp=participant_frame.xp,
                    minions_killed=participant_frame.minions_killed,
                    jungle_minions_killed=participant_frame.jungle_minions_killed,
                    position_x=participant_frame.position.x,
                    position_y=participant_frame.position.y,
                    time_enemy_spent_controlled=participant_frame.time_enemy_spent_controlled,
                    # Damage stats
                    magic_damage_done=damage_stats.get("magicDamageDone"),
                    magic_damage_done_to_champions=damage_stats.get("magicDamageDoneToChampions"),
                    magic_damage_taken=damage_stats.get("magicDamageTaken"),
                    physical_damage_done=damage_stats.get("physicalDamageDone"),
                    physical_damage_done_to_champions=damage_stats.get(
                        "physicalDamageDoneToChampions"
                    ),
                    physical_damage_taken=damage_stats.get("physicalDamageTaken"),
                    total_damage_done=damage_stats.get("totalDamageDone"),
                    total_damage_done_to_champions=damage_stats.get("totalDamageDoneToChampions"),
                    total_damage_taken=damage_stats.get("totalDamageTaken"),
                    true_damage_done=damage_stats.get("trueDamageDone"),
                    true_damage_done_to_champions=damage_stats.get("trueDamageDoneToChampions"),
                    true_damage_taken=damage_stats.get("trueDamageTaken"),
                    # Champion stats
                    ability_haste=champion_stats.get("abilityHaste"),
                    ability_power=champion_stats.get("abilityPower"),
                    armor=champion_stats.get("armor"),
                    armor_pen=champion_stats.get("armorPen"),
                    armor_pen_percent=champion_stats.get("armorPenPercent"),
                    attack_damage=champion_stats.get("attackDamage"),
                    attack_speed=champion_stats.get("attackSpeed"),
                    bonus_armor_pen_percent=champion_stats.get("bonusArmorPenPercent"),
                    bonus_magic_pen_percent=champion_stats.get("bonusMagicPenPercent"),
                    cc_reduction=champion_stats.get("ccReduction"),
                    cooldown_reduction=champion_stats.get("cooldownReduction"),
                    health=champion_stats.get("health"),
                    health_max=champion_stats.get("healthMax"),
                    health_regen=champion_stats.get("healthRegen"),
                    lifesteal=champion_stats.get("lifesteal"),
                    magic_pen=champion_stats.get("magicPen"),
                    magic_pen_percent=champion_stats.get("magicPenPercent"),
                    magic_resist=champion_stats.get("magicResist"),
                    movement_speed=champion_stats.get("movementSpeed"),
                    omnivamp=champion_stats.get("omnivamp"),
                    physical_vamp=champion_stats.get("physicalVamp"),
                    power=champion_stats.get("power"),
                    power_max=champion_stats.get("powerMax"),
                    power_regen=champion_stats.get("powerRegen"),
                    spell_vamp=champion_stats.get("spellVamp"),
                )
                participant_frames_to_add.append(frame_record)

        # Bulk add participant frames
        if participant_frames_to_add:
            self._session.add_all(participant_frames_to_add)

        await self._session.commit()

        logger.info(
            "Saved timeline data",
            match_id=timeline_dto.metadata.match_id,
            total_events=len(events_json),
            tracked_frames=len(participant_frames_to_add),
            events_filtered=filter_events,
        )

        return timeline

    async def get_timeline(self, match_id: str) -> MatchTimeline | None:
        """Get timeline data for a match.

        Args:
            match_id: Match ID

        Returns:
            Timeline object or None if not found
        """
        result = await self._session.execute(
            select(MatchTimeline).where(MatchTimeline.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def get_participant_frames(
        self, match_id: str, puuid: str | None = None
    ) -> list[TimelineParticipantFrame]:
        """Get participant frames for a match.

        Args:
            match_id: Match ID
            puuid: Optional PUUID to filter by specific player

        Returns:
            List of participant frames
        """
        query = select(TimelineParticipantFrame).where(
            TimelineParticipantFrame.match_id == match_id
        )

        if puuid:
            query = query.where(TimelineParticipantFrame.puuid == puuid)

        query = query.order_by(TimelineParticipantFrame.timestamp)

        result = await self._session.execute(query)
        return list(result.scalars().all())
