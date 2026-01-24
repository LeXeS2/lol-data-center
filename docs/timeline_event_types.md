# League of Legends Timeline Event Types

This document provides comprehensive documentation for all event types that can appear in the Riot API match timeline data.

## Overview

Match timelines contain sequential events that represent gameplay actions. Each event has:
- `timestamp` (integer): Milliseconds elapsed since game start
- `realTimestamp` (integer): Unix timestamp of when event occurred
- `type` (string): Event type identifier

Additional fields vary by event type.

---

## Event Types Reference

### PAUSE_END
**Description**: Game resumed after a pause.

**Fields**:
- `timestamp` (int): When game resumed
- `realTimestamp` (int): Unix timestamp
- `type` (string): "PAUSE_END"

**Example**:
```json
{
  "realTimestamp": 1769110876803,
  "timestamp": 0,
  "type": "PAUSE_END"
}
```

**Context**: Appears when game is unpaused. Multiple instances possible if game paused/unpaused several times.

---

### SKILL_LEVEL_UP
**Description**: A champion's ability level increased.

**Fields**:
- `participantId` (int): Champion who leveled ability
- `skillSlot` (int): Ability slot (0-4, where 4 is ultimate)
  - 0: Q ability
  - 1: W ability
  - 2: E ability
  - 3: R ability (ultimate)
- `levelUpType` (string): Type of level up
  - "NORMAL": Regular ability point allocation
  - "EVOLVE": Champion evolution (e.g., Kai'Sa, Evelynn)
- `timestamp` (int): When ability was leveled
- `type` (string): "SKILL_LEVEL_UP"

**Example**:
```json
{
  "levelUpType": "NORMAL",
  "participantId": 0,
  "skillSlot": 4,
  "timestamp": 0,
  "type": "SKILL_LEVEL_UP"
}
```

**Context**: Champions get skill points at levels 1, 2, 3, 6, 11, 16 (for ultimates). Each ability leveling generates one event.

---

### LEVEL_UP
**Description**: A champion reached a new level.

**Fields**:
- `participantId` (int): Champion who leveled up
- `timestamp` (int): When champion leveled
- `type` (string): "LEVEL_UP"

**Example**:
```json
{
  "participantId": 0,
  "timestamp": 1406,
  "type": "LEVEL_UP"
}
```

**Context**: Generated every time a champion gains enough experience to increase level (levels 1-18).

---

### ITEM_PURCHASED
**Description**: A champion purchased an item.

**Fields**:
- `participantId` (int): Champion who purchased
- `itemId` (int): Riot item ID (e.g., 3865 = Plated Steelcaps)
- `timestamp` (int): When item was purchased
- `type` (string): "ITEM_PURCHASED"

**Example**:
```json
{
  "itemId": 3865,
  "participantId": 0,
  "timestamp": 0,
  "type": "ITEM_PURCHASED"
}
```

**Context**: Multiple purchases possible in same timestamp. Includes initial items and all later purchases.

---

### ITEM_SOLD
**Description**: A champion sold an item back to the shop.

**Fields**:
- `participantId` (int): Champion who sold item
- `itemId` (int): Riot item ID
- `timestamp` (int): When item was sold
- `type` (string): "ITEM_SOLD"

**Example**:
```json
{
  "itemId": 3089,
  "participantId": 2,
  "timestamp": 5400,
  "type": "ITEM_SOLD"
}
```

**Context**: Occurs when champion sells inventory items. Less frequent than purchases.

---

### ITEM_DESTROYED
**Description**: An item in a champion's inventory was destroyed (e.g., by an effect).

**Fields**:
- `participantId` (int): Champion whose item was destroyed
- `itemId` (int): Riot item ID
- `timestamp` (int): When item was destroyed
- `type` (string): "ITEM_DESTROYED"

**Example**:
```json
{
  "itemId": 3020,
  "participantId": 4,
  "timestamp": 1200,
  "type": "ITEM_DESTROYED"
}
```

**Context**: Rare event; occurs with specific champion abilities or map mechanics.

---

### ITEM_UNDO
**Description**: A champion used a refund mechanic to undo an item purchase.

**Fields**:
- `participantId` (int): Champion using undo
- `itemId` (int): Riot item ID that was refunded
- `timestamp` (int): When undo was used
- `type` (string): "ITEM_UNDO"

**Example**:
```json
{
  "itemId": 3057,
  "participantId": 1,
  "timestamp": 300,
  "type": "ITEM_UNDO"
}
```

**Context**: Very rare in competitive play; appears only if refund mechanic is used (typically within first few minutes).

---

### CHAMPION_KILL
**Description**: A champion was killed by another champion.

**Fields**:
- `killerId` (int): Champion who delivered final blow
- `victimId` (int): Champion who was killed
- `timestamp` (int): When kill occurred
- `assistingParticipantIds` (int[], optional): Participants who assisted
- `type` (string): "CHAMPION_KILL"

**Example**:
```json
{
  "killerId": 1,
  "victimId": 3,
  "assistingParticipantIds": [0, 2],
  "timestamp": 4500,
  "type": "CHAMPION_KILL"
}
```

**Context**: Critical event for game analysis. Kill count directly tied to victory.

---

### ELITE_MONSTER_KILL
**Description**: A team killed a major objective (Dragon, Baron, Rift Herald).

**Fields**:
- `killerId` (int): Champion delivering final blow (or team representative)
- `monsterType` (string): Type of monster
  - "DRAGON": Summoner's Rift dragon
  - "BARON_NASHOR": Baron Nashor
  - "RIFTHERALD": Rift Herald
  - "HORDE_BREAKER": Horde of the Void (Ultimate Spellbook)
- `monsterSubType` (string, optional): Specific dragon type
  - "CHEMTECH": Chemtech Dragon
  - "CLOUD": Cloud Dragon
  - "FIRE": Infernal Dragon
  - "MOUNTAIN": Mountain Dragon
  - "OCEAN": Ocean Dragon
  - "HEXTECH": Hextech Dragon (Ultimate Spellbook)
  - "SPECTRAL": Spectral Dragon
- `timestamp` (int): When monster was killed
- `type` (string): "ELITE_MONSTER_KILL"

**Example**:
```json
{
  "killerId": 0,
  "monsterType": "DRAGON",
  "monsterSubType": "FIRE",
  "timestamp": 8100,
  "type": "ELITE_MONSTER_KILL"
}
```

**Context**: Major gold generation and buff events. Dragon type determines team-wide buffs.

---

### BUILDING_KILL
**Description**: A team destroyed an enemy structure (tower, inhibitor, nexus).

**Fields**:
- `killerId` (int): Champion who delivered final blow
- `buildingType` (string): Type of structure
  - "TURRET": Tower
  - "INHIBITOR": Inhibitor
  - "NEXUS": Nexus (game ending structure)
- `laneType` (string, optional): Map lane for towers/inhibitors
  - "BOT_LANE": Bottom lane
  - "MID_LANE": Middle lane
  - "TOP_LANE": Top lane
- `towerType` (string, optional): Specific tower type
  - "INNER_TURRET": Inner tower
  - "OUTER_TURRET": Outer tower
  - "BASE_TURRET": Base tower
- `timestamp` (int): When structure was destroyed
- `type` (string): "BUILDING_KILL"

**Example**:
```json
{
  "killerId": 1,
  "buildingType": "TURRET",
  "towerType": "OUTER_TURRET",
  "laneType": "MID_LANE",
  "timestamp": 6000,
  "type": "BUILDING_KILL"
}
```

**Context**: Progression event; towers provide safety and control.

---

### TURRET_PLATE_DESTROYED
**Description**: A turret lost a plating segment (removed 2022, but may exist in historical data).

**Fields**:
- `killerId` (int): Champion who destroyed plate
- `laneType` (string): Lane location
  - "BOT_LANE"
  - "MID_LANE"
  - "TOP_LANE"
- `timestamp` (int): When plate was destroyed
- `type` (string): "TURRET_PLATE_DESTROYED"

**Example**:
```json
{
  "killerId": 2,
  "laneType": "TOP_LANE",
  "timestamp": 3600,
  "type": "TURRET_PLATE_DESTROYED"
}
```

**Context**: Early game objective (plates removed before 15 minutes). No longer appears in current Patch.

---

### WARD_PLACED
**Description**: A control ward or stealth ward was placed on the map.

**Fields**:
- `creatorId` (int): Champion who placed ward
- `wardType` (string): Type of ward
  - "CONTROL_WARD": Red control ward
  - "STEALTH_WARD": Yellow trinket ward
  - "TRINKET_WARD": Trinket-placed ward
- `timestamp` (int): When ward was placed
- `type` (string): "WARD_PLACED"

**Example**:
```json
{
  "creatorId": 1,
  "wardType": "CONTROL_WARD",
  "timestamp": 2100,
  "type": "WARD_PLACED"
}
```

**Context**: Vision control mechanic. High ward placement correlates with map pressure.

---

### WARD_KILL
**Description**: An enemy ward was destroyed or expired.

**Fields**:
- `killerId` (int): Champion who destroyed ward (or -1 if expired)
- `wardType` (string): Type of ward
  - "CONTROL_WARD"
  - "STEALTH_WARD"
  - "TRINKET_WARD"
- `timestamp` (int): When ward was destroyed
- `type` (string): "WARD_KILL"

**Example**:
```json
{
  "killerId": 3,
  "wardType": "STEALTH_WARD",
  "timestamp": 4200,
  "type": "WARD_KILL"
}
```

**Context**: Vision denial. Frequent in coordinated play.

---

### CHAMPION_SPECIAL_KILL
**Description**: A special kill type beyond normal champion kills.

**Fields**:
- `killerId` (int): Champion who delivered killing blow
- `victimId` (int): Champion who was killed
- `killType` (string): Specific kill type
  - "KILL_ACE": Team elimination (Ace)
  - "TURRET_KILL": Killed by turret
  - "MINION_KILL": Killed by minion (very rare)
  - "TOTAL_KILL": Any kill event (legacy)
  - "ELITE_MONSTER_KILL": Killed by elite monster (very rare)
  - "PET_KILL": Killed by pet/minion
- `assistingParticipantIds` (int[], optional): Assist participants
- `timestamp` (int): When kill occurred
- `type` (string): "CHAMPION_SPECIAL_KILL"

**Example**:
```json
{
  "killerId": 2,
  "victimId": 7,
  "killType": "KILL_ACE",
  "timestamp": 9000,
  "type": "CHAMPION_SPECIAL_KILL"
}
```

**Context**: Aces are critical team fight outcomes. Game often won after team ace.

---

### CHAMPION_TRANSFORM
**Description**: A champion transformed or evolved (e.g., Kayle, Yasuo, Udyr transforms).

**Fields**:
- `participantId` (int): Champion who transformed
- `transformType` (string): Type of transformation
  - "KAYLE_TRANSFORM": Kayle reaches 11 (gains flight)
  - "YASUO_TRANSFORM": Power-up transformation
  - "UDYR_TRANSFORM": Udyr spiritual form (post-rework)
  - "AQUA_DRAGON_TRANSFORM": Rek'Sai R activation
  - "SHYVANA_TRANSFORM": Shyvana dragon form
  - "PROTOBELT_TRANSFORM": Hextech Protobelt effect
- `timestamp` (int): When transformation occurred
- `type` (string): "CHAMPION_TRANSFORM"

**Example**:
```json
{
  "participantId": 4,
  "transformType": "KAYLE_TRANSFORM",
  "timestamp": 10800,
  "type": "CHAMPION_TRANSFORM"
}
```

**Context**: Power spike indicators. Transforms typically improve champion combat effectiveness.

---

## Event Frequency Analysis

Based on reference timeline data:

| Event Type | Frequency | Notes |
|---|---|---|
| ITEM_PURCHASED | Very High | Multiple per champion per game |
| SKILL_LEVEL_UP | High | 4 per level up (Q, W, E, R) |
| LEVEL_UP | High | 18 total per champion |
| PAUSE_END | Low | Depends on pause frequency |
| CHAMPION_KILL | Medium | ~20-30 total per game |
| BUILDING_KILL | Medium | ~10-20 per game |
| ITEM_SOLD | Low | ~2-5 per champion |
| WARD_PLACED | Medium | ~30-50 per game |
| WARD_KILL | Medium | ~10-20 per game |
| ELITE_MONSTER_KILL | Low | 4-7 dragons, 1-2 barons |
| CHAMPION_TRANSFORM | Very Low | Only specific champions |
| Other | Rare | Game-specific mechanics |

---

## Usage Examples

### Querying by Event Type
```python
# Filter timeline events to get all item purchases
item_purchases = [e for e in timeline.events if e['type'] == 'ITEM_PURCHASED']

# Get all champion kills
kills = [e for e in timeline.events if e['type'] == 'CHAMPION_KILL']

# Get kills by participant
kills_by_player = [e for e in timeline.events 
                   if e['type'] == 'CHAMPION_KILL' and e['killerId'] == participant_id]
```

### Database Query Examples
```sql
-- Get all champion kills from stored timeline
SELECT event 
FROM timeline_event 
WHERE event->>'type' = 'CHAMPION_KILL'
AND match_id = 'EUW1_7696919800';

-- Get item purchases by participant
SELECT COUNT(*), (event->>'participantId')::int AS participant
FROM timeline_event
WHERE event->>'type' = 'ITEM_PURCHASED'
AND match_id = 'EUW1_7696919800'
GROUP BY participant;

-- Track ward placement over time
SELECT (event->>'timestamp')::int / 60000 AS minute,
       COUNT(*) AS wards_placed
FROM timeline_event
WHERE event->>'type' = 'WARD_PLACED'
AND match_id = 'EUW1_7696919800'
GROUP BY minute;
```

---

## Field References

### Common Field Types
- **participantId** (0-9): Champion index in match
- **killerId** (-1 if unknown, 0-9 for champion)
- **victimId** (0-9): Killed champion index
- **assistingParticipantIds** (int[]): Contributors to kill
- **timestamp** (milliseconds): 0 = game start
- **realTimestamp** (Unix ms): Absolute time

### Item IDs
Common item IDs (use Riot Data Dragon for complete list):
- 1001: Boots
- 3020: Abyssal Mask
- 3089: Spirit Visage
- 3865: Plated Steelcaps
- 6609: Kaenic Rookern
- 6670: Hollow Radiance

See [Item Data Dragon](https://ddragon.leagueoflegends.com/cdn/en_US/img/sprite/item0.png)

---

## Notes on Data Completeness

- Not all event types appear in every match
- Event presence depends on game state and champion selection
- Some events (CHAMPION_TRANSFORM) only occur with specific champions
- Special game modes (ARAM, Ultimate Spellbook) may have unique event types
- Historical data may have deprecated event types

---

## API Documentation Reference

For official Riot API documentation on timeline events, see:
https://developer.riotgames.com/api-methods/#match-v5/GET_match

