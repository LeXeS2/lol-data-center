# Timeline Data Usage Examples

## Querying Timeline Data

### Get Timeline for a Match

```python
from lol_data_center.database.engine import get_async_session
from lol_data_center.services.timeline_service import TimelineService

async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    # Get timeline
    timeline = await timeline_service.get_timeline("EUW1_7696919800")
    
    if timeline:
        print(f"Frame interval: {timeline.frame_interval}ms")
        print(f"Total events: {len(timeline.events['events'])}")
        print(f"Events filtered: {timeline.events_filtered}")
```

### Get Player Progression Over Time

```python
async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    # Get all frames for a specific player
    frames = await timeline_service.get_participant_frames(
        match_id="EUW1_7696919800",
        puuid="your-player-puuid"
    )
    
    # Print gold and CS progression
    for frame in frames:
        minutes = frame.timestamp // 60000
        cs = frame.minions_killed + frame.jungle_minions_killed
        print(f"{minutes:2d}min: {frame.total_gold:5d}g, {cs:3d}cs, Level {frame.level}")
```

### Analyze Events

```python
async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    timeline = await timeline_service.get_timeline("EUW1_7696919800")
    events = timeline.events["events"]
    
    # Count kills
    kills = [e for e in events if e["type"] == "CHAMPION_KILL"]
    print(f"Total kills: {len(kills)}")
    
    # Find first blood
    first_kill = kills[0] if kills else None
    if first_kill:
        print(f"First blood at {first_kill['timestamp']/1000:.1f}s")
        print(f"Killer: Participant {first_kill['killerId']}")
        print(f"Victim: Participant {first_kill['victimId']}")
    
    # Count objective takes
    barons = [e for e in events if e["type"] == "ELITE_MONSTER_KILL" and 
              e.get("monsterType") == "BARON_NASHOR"]
    dragons = [e for e in events if e["type"] == "ELITE_MONSTER_KILL" and 
               e.get("monsterType") == "DRAGON"]
    
    print(f"Barons: {len(barons)}, Dragons: {len(dragons)}")
```

### Calculate Gold Lead

```python
async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    # Get frames for both players
    player1_frames = await timeline_service.get_participant_frames(
        match_id="EUW1_7696919800",
        puuid="player1-puuid"
    )
    player2_frames = await timeline_service.get_participant_frames(
        match_id="EUW1_7696919800",
        puuid="player2-puuid"
    )
    
    # Calculate gold difference at each timestamp
    gold_lead = {}
    for f1, f2 in zip(player1_frames, player2_frames):
        if f1.timestamp == f2.timestamp:
            minutes = f1.timestamp // 60000
            diff = f1.total_gold - f2.total_gold
            gold_lead[minutes] = diff
    
    # Print
    for minute, diff in gold_lead.items():
        sign = "+" if diff >= 0 else ""
        print(f"{minute:2d}min: {sign}{diff:5d}g")
```

### Track Champion Position (Heatmap Data)

```python
async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    frames = await timeline_service.get_participant_frames(
        match_id="EUW1_7696919800",
        puuid="player-puuid"
    )
    
    # Extract positions
    positions = [(f.position_x, f.position_y, f.timestamp) for f in frames]
    
    # Could be used to generate a heatmap showing where the player spent time
    for x, y, timestamp in positions:
        print(f"At {timestamp/60000:.1f}min: ({x}, {y})")
```

### Compare CS Per Minute

```python
async with get_async_session() as session:
    timeline_service = TimelineService(session)
    
    frames = await timeline_service.get_participant_frames(
        match_id="EUW1_7696919800",
        puuid="player-puuid"
    )
    
    # Calculate CS/min
    for frame in frames:
        if frame.timestamp > 0:  # Skip initial frame
            minutes = frame.timestamp / 60000
            total_cs = frame.minions_killed + frame.jungle_minions_killed
            cs_per_min = total_cs / minutes
            print(f"{minutes:5.1f}min: {total_cs:3d} CS ({cs_per_min:.1f} CS/min)")
```

## SQL Queries

### Get Match with Most Events

```sql
SELECT 
    match_id,
    jsonb_array_length(events->'events') as event_count,
    events_filtered
FROM match_timelines
ORDER BY event_count DESC
LIMIT 10;
```

### Get Player's Gold Progression

```sql
SELECT 
    timestamp / 60000 as minutes,
    total_gold,
    current_gold,
    minions_killed + jungle_minions_killed as cs,
    level
FROM timeline_participant_frames
WHERE match_id = 'EUW1_7696919800'
    AND puuid = 'your-player-puuid'
ORDER BY timestamp;
```

### Find All Pentakills in Timeline Events

```sql
SELECT 
    mt.match_id,
    event->>'timestamp' as timestamp,
    event->>'killerId' as killer_participant_id
FROM match_timelines mt,
     jsonb_array_elements(mt.events->'events') as event
WHERE event->>'type' = 'CHAMPION_KILL'
    AND jsonb_array_length(
        COALESCE(event->'victimDamageReceived', '[]'::jsonb)
    ) >= 5;
```

### Get Average Gold at 10 Minutes for a Player

```sql
SELECT 
    AVG(total_gold) as avg_gold_10min,
    AVG(minions_killed + jungle_minions_killed) as avg_cs_10min
FROM timeline_participant_frames
WHERE puuid = 'your-player-puuid'
    AND timestamp = 600000  -- 10 minutes
;
```

### Find Games Where Player Got First Blood

```sql
SELECT 
    mt.match_id,
    event->>'timestamp' as fb_timestamp,
    event->>'victimId' as victim
FROM match_timelines mt,
     jsonb_array_elements(mt.events->'events') as event,
     timeline_participant_frames tpf
WHERE event->>'type' = 'CHAMPION_KILL'
    AND event->>'killerId' = tpf.participant_id::text
    AND tpf.puuid = 'your-player-puuid'
    AND tpf.match_id = mt.match_id
    -- First kill is the one with lowest timestamp
    AND (event->>'timestamp')::int = (
        SELECT MIN((e->>'timestamp')::int)
        FROM jsonb_array_elements(mt.events->'events') as e
        WHERE e->>'type' = 'CHAMPION_KILL'
    );
```

## Advanced Analytics

### Calculate XP Lead/Deficit

```python
from collections import defaultdict

async def calculate_xp_advantage(match_id: str, team_id: int):
    """Calculate XP advantage/disadvantage for a team over time."""
    async with get_async_session() as session:
        timeline_service = TimelineService(session)
        
        all_frames = await timeline_service.get_participant_frames(match_id)
        
        # Group by timestamp
        by_timestamp = defaultdict(lambda: {"team": 0, "enemy": 0})
        
        for frame in all_frames:
            # Assuming participants 1-5 are team 100, 6-10 are team 200
            is_our_team = (team_id == 100 and frame.participant_id <= 5) or \
                         (team_id == 200 and frame.participant_id > 5)
            
            if is_our_team:
                by_timestamp[frame.timestamp]["team"] += frame.xp
            else:
                by_timestamp[frame.timestamp]["enemy"] += frame.xp
        
        # Calculate advantage
        for timestamp, data in sorted(by_timestamp.items()):
            advantage = data["team"] - data["enemy"]
            minutes = timestamp // 60000
            print(f"{minutes:2d}min: {advantage:+6d} XP")
```

### Detect Invades/Jungle Tracking

```python
async def detect_early_jungle_activity(match_id: str, puuid: str):
    """Detect if player invaded enemy jungle early."""
    async with get_async_session() as session:
        timeline_service = TimelineService(session)
        
        frames = await timeline_service.get_participant_frames(match_id, puuid)
        
        # Check position in first 5 minutes
        early_frames = [f for f in frames if f.timestamp <= 300000]
        
        for frame in early_frames:
            # Jungle quadrant detection (simplified)
            # Top side: y > 7000, Bot side: y < 7000
            # Blue side: x < 7000, Red side: x > 7000
            
            in_enemy_jungle = False
            if frame.participant_id <= 5:  # Blue side
                in_enemy_jungle = frame.position_x > 7000
            else:  # Red side
                in_enemy_jungle = frame.position_x < 7000
            
            if in_enemy_jungle:
                print(f"Enemy jungle at {frame.timestamp/1000:.0f}s: ({frame.position_x}, {frame.position_y})")
```

## Event Type Reference

Common event types in timeline data:

- `CHAMPION_KILL` - Champion kill
- `ELITE_MONSTER_KILL` - Baron, Dragon, Rift Herald
- `BUILDING_KILL` - Tower, Inhibitor, Nexus
- `TURRET_PLATE_DESTROYED` - Turret plate broken
- `ITEM_PURCHASED` - Item bought
- `ITEM_SOLD` - Item sold
- `ITEM_DESTROYED` - Item consumed/destroyed
- `ITEM_UNDO` - Purchase undone
- `SKILL_LEVEL_UP` - Ability leveled up
- `LEVEL_UP` - Champion level up
- `WARD_PLACED` - Ward placed
- `WARD_KILL` - Ward destroyed
- `PAUSE_END` - Game unpaused
- `CHAMPION_SPECIAL_KILL` - Multikill, shutdown, etc.
- `CHAMPION_TRANSFORM` - Champion transformation (e.g., Kayn)

Check the `type` field in each event to determine what happened!
