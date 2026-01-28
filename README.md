# LoL Data Center

A League of Legends match data collection and achievement evaluation system.

## Features

- **Match Data Collection**: Automatically polls and stores match data for tracked players
- **Rank Tracking**: Monitors player rank changes every 30 minutes and saves history
- **ELO Graph Visualization**: Generate progression graphs showing rank changes over time
- **Event-Driven Architecture**: Multiple components can listen for new match events
- **Achievement Evaluation**: Flexible achievement system with multiple condition types:
  - Absolute thresholds (e.g., kills > 10)
  - Personal records (new max/min)
  - Population percentiles (top X% of all players)
  - Player percentiles (top X% of own games)
- **Discord Notifications**: Sends achievement notifications to Discord
- **Discord Bot Commands**: Interactive slash commands for managing players directly from Discord
- **Rate Limiting**: Respects Riot API rate limits (100 requests / 2 minutes)
- **Async Architecture**: Non-blocking API interactions

## Requirements

- Python 3.11+
- PostgreSQL 16+
- Docker & Docker Compose (optional, for deployment)

## Quick Start

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/lol-data-center.git
   cd lol-data-center
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or: source .venv/bin/activate  # Linux/Mac
   pip install -e ".[dev]"
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

4. Start PostgreSQL (or use Docker):
   ```bash
   docker-compose up -d db
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the application:
   ```bash
   lol-data-center run
   ```

### Docker Deployment

1. Configure your `.env` file with required values

2. Start all services:
   ```bash
   docker-compose up -d
   ```

3. (Optional) Start with Adminer for database management:
   ```bash
   docker-compose --profile tools up -d
   ```

## CLI Commands

```bash
# Start the polling service
lol-data-center run

# Add a player to track
lol-data-center add-player "GameName#TAG" --region europe

# Remove a player
lol-data-center remove-player "GameName#TAG"

# List tracked players
lol-data-center list-players

# Run database migrations
lol-data-center migrate
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `RIOT_API_KEY` | Riot Games API Key | (required) |
| `DATABASE_URL` | PostgreSQL connection string | (required) |
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications | (required) |
| `DISCORD_BOT_TOKEN` | Discord bot token for slash commands | (optional) |
| `POLLING_INTERVAL_SECONDS` | Interval between polling cycles | 300 |
| `LOG_LEVEL` | Logging level | INFO |
| `DEFAULT_REGION` | Default region for API calls | europe |

### Discord Bot Setup (Optional)

The Discord bot enables interactive slash commands for managing players directly from Discord. To set it up:

1. **Create a Discord Bot**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token and add it to your `.env` file as `DISCORD_BOT_TOKEN`

2. **Set Bot Permissions**:
   - In the "OAuth2" > "URL Generator" section:
     - Select scope: `bot`, `applications.commands`
     - Select bot permissions: `Send Messages`, `Use Slash Commands`
   - Use the generated URL to invite the bot to your server

3. **Available Slash Commands**:
   - `/add-player` - Add a player to track (includes automatic match history backfill with progress notifications)
   - `/remove-player` - Remove a player from tracking
   - `/list-players` - List all tracked players
   - `/register` - Register your Riot ID to avoid typing it for every command
   - `/unregister` - Remove your registered Riot ID
   - `/show-stats` - Show ranked statistics for current season
   - `/player-map-position` - Visualize player movement on the map for a specific match
   - `/elo-graph` - Generate ELO progression graph showing rank changes over time
     - Optional `last_weeks` parameter to limit time range
     - Optional `queue` parameter: `solo` (default) or `flex`

Note: The Discord bot is optional. The application will run without it if `DISCORD_BOT_TOKEN` is not configured.

## Rank Tracking

The rank tracking system automatically polls for player rank changes every 30 minutes. Rank data is saved to the database only when changes are detected. This enables:

- **ELO Progression Graphs**: Visualize rank changes over time with `/elo-graph` command
- **Historical Data**: Track rank history across the entire season
- **Queue-Specific Tracking**: Separate tracking for Ranked Solo/Duo and Ranked Flex queues

The ELO calculation converts League ranks to a numeric scale:
- Each tier (Iron, Bronze, Silver, etc.) has a base ELO value
- Divisions (I-IV) add incremental values
- League Points directly add to the ELO
- Master+ tiers only use League Points (no divisions)

## Achievement Configuration

Achievements are defined in `achievements.yaml`. See the file for examples of all condition types.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lol_data_center --cov-report=html
```

## License

MIT
