## Implementation Plan for /show-stats Command

### Overview
Implement a Discord slash command `/show-stats` that displays current season ranked statistics for a given League of Legends player.

### Requirements Analysis
- **Input**: `player_riot_id` (format: GameName#TagLine)
- **Output**: Embedded message displaying:
  - Win rate (wins/total games)
  - Total ranked games played
  - Top 3 most played champions with game counts

### Implementation Steps

#### 1. API Integration
- **Riot API Endpoints needed**:
  - `/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` - Get PUUID from Riot ID
  - `/lol/summoner/v4/summoners/by-puuid/{puuid}` - Get summoner data
  - `/lol/league/v4/entries/by-summoner/{summonerId}` - Get ranked stats
  - `/lol/match/v5/matches/by-puuid/{puuid}/ids` - Get match IDs for current season
  - `/lol/match/v5/matches/{matchId}` - Get match details for champion analysis

#### 2. Data Processing
- Filter matches by current season (2026 Season 1)
- Filter for ranked queue types (RANKED_SOLO_5x5, RANKED_FLEX_SR)
- Calculate win rate: `(wins / total_games) * 100`
- Aggregate champion play counts
- Sort champions by games played and select top 3

#### 3. Discord Command Structure
```python
@bot.tree.command(name="show-stats", description="Display ranked stats for a player")
async def show_stats(interaction: discord.Interaction, player_riot_id: str):
    # Parse riot_id (GameName#TagLine)
    # Fetch player data from Riot API
    # Calculate statistics
    # Create and send Discord embed
```

#### 4. Error Handling
- Invalid Riot ID format
- Player not found
- No ranked games this season
- API rate limiting
- Network errors

#### 5. Discord Embed Design
```
┌─────────────────────────────────────┐
│ 📊 Ranked Stats - [GameName#Tag]   │
├─────────────────────────────────────┤
│ 🎮 Games Played: XXX                │
│ 📈 Win Rate: XX.X% (W-L)            │
│                                     │
│ 🏆 Top Champions:                   │
│ 1. Champion1 - XX games             │
│ 2. Champion2 - XX games             │
│ 3. Champion3 - XX games             │
└─────────────────────────────────────┘
```

#### 6. Caching Considerations
- Cache player PUUID mappings to reduce API calls
- Cache match data temporarily
- Implement cache expiration (e.g., 5-10 minutes)

#### 7. Testing Plan
- Test with valid Riot IDs
- Test with invalid inputs
- Test with accounts having no ranked games
- Test API rate limit handling
- Test with different region configurations

### Technical Considerations
- **Region handling**: Need to determine player region or make it configurable
- **Rate limiting**: Implement exponential backoff for Riot API
- **Performance**: For players with many games, consider limiting match history fetch
- **Season detection**: Implement logic to identify current season start date

### Suggested File Structure
```
/commands/show_stats.py - Command implementation
/utils/riot_api.py - Riot API wrapper functions
/utils/stats_calculator.py - Statistics calculation logic
/utils/cache.py - Caching mechanism (optional)
```

### Dependencies
- Discord.py (slash commands support)
- Requests or aiohttp (for Riot API calls)
- Python-dotenv (for API key management)
- Riot API key with appropriate rate limits

### Estimated Effort
- API integration: 2-3 hours
- Data processing logic: 2 hours
- Discord command implementation: 1-2 hours
- Error handling & testing: 2 hours
- **Total**: ~7-9 hours

---

Ready to start implementation? Let me know if you'd like me to create a PR for this feature!