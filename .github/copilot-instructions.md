# LoL Data Center - AI Coding Agent Instructions

## Environment Setup

### Prerequisites
- **Python 3.11+** (strict requirement - uses modern type hints and async features)
- **PostgreSQL 16+** for production (SQLite for tests)
- **Docker & Docker Compose** (optional, for containerized development)

### Quick Start
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# 2. Install with dev dependencies
pip install -e ".[dev]"

# 3. Copy and configure .env
cp .env.example .env
# Edit .env with your RIOT_API_KEY, DATABASE_URL, DISCORD_WEBHOOK_URL

# 4. Start database (Docker) or use local PostgreSQL
docker-compose up -d db

# 5. Run migrations
alembic upgrade head

# 6. Start application
lol-data-center run
```

### Linting & Code Quality
**Always run before committing:**
```bash
# Format and lint code
ruff check src/ tests/           # Check for issues
ruff check --fix src/ tests/     # Auto-fix issues
ruff format src/ tests/          # Format code

# Type checking (strict mode)
mypy src/                        # Must pass with no errors

# Run all quality checks
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/
```

**Linting rules (configured in pyproject.toml):**
- Line length: 100 characters
- Target: Python 3.11
- Selected rules: E, F, I, N, W, UP, ANN, B, C4, SIM
- Ignored: ANN101, ANN102 (self/cls annotations)

## Architecture Overview

This is an **event-driven, async Python application** that polls Riot API for League of Legends match data, evaluates achievements, and sends Discord notifications.

### Core Components & Data Flow
1. **PollingService** (`services/polling_service.py`) - Main loop that fetches matches for tracked players every 5 minutes
2. **EventBus** (`events/event_bus.py`) - Pub/sub pattern: `PollingService` publishes `NewMatchEvent`, multiple components subscribe
3. **AchievementEvaluator** (`achievements/evaluator.py`) - Subscribes to `NewMatchEvent`, evaluates YAML-defined achievements, sends Discord notifications
4. **RiotApiClient** (`api_client/riot_client.py`) - Rate-limited async HTTP client (100 req/2min) with response validation
5. **Services Layer** (`services/`) - `PlayerService`, `MatchService` handle DB operations using async SQLAlchemy

### Key Structural Decisions
- **Why event bus?** Decouples match processing from achievement evaluation - can add more subscribers (analytics, webhooks) without modifying polling logic
- **Why async?** Riot API calls and DB operations are I/O-bound; async enables concurrent processing of multiple players
- **Global singletons** (`get_event_bus()`, `get_settings()`) use `@lru_cache` for dependency injection without frameworks

## Riot API Integration

### Schema Changes (Critical!)
**Recent API change:** `SummonerDto` no longer returns `accountId` and `id` fields - they are **optional** in schemas. `ParticipantDto.summonerId` is also optional.
- When creating fixtures/tests, use `None` for these fields
- Database models have these as nullable: `TrackedPlayer.summoner_id`, `MatchParticipant.summoner_id`

### API Response Handling
- **Validation:** All API responses use Pydantic DTOs in `schemas/riot_api.py` with `validate_response()` wrapper
- **Invalid responses:** Saved to `data/invalid_responses/{timestamp}_{endpoint}.json` for debugging
- **Rate limiting:** Managed by `RateLimiter` (token bucket algorithm) - respect `Retry-After` headers

## Database Patterns

### Async Session Management
```python
# ALWAYS use context manager pattern
async with get_async_session() as session:
    result = await session.execute(select(TrackedPlayer).where(...))
    # Auto-commit on success, rollback on exception
```

### Service Layer Pattern
All DB logic goes through service classes (not direct model access):
- `PlayerService.get_or_create_player()` - Idempotent player creation
- `MatchService.save_match()` - Idempotent match saving (checks existence first)
- Services handle business logic + `event_bus.publish()` calls

### Migrations
- **Alembic** for schema changes: `alembic revision --autogenerate -m "description"`
- Database `init_db()` creates tables, but production uses migrations
- Migration naming: `YYYYMMDD_description.py` (e.g., `20260120_make_summoner_id_nullable.py`)

## Achievement System

### Configuration (`achievements.yaml`)
5 condition types: `absolute`, `personal_max`, `personal_min`, `population_percentile`, `player_percentile`

Example:
```yaml
- id: high_kills
  stat_field: kills  # Must match ParticipantDto field name
  condition_type: absolute
  operator: ">="
  threshold: 10
  message_template: "🎯 **{player_name}** got {value} kills!"
```

### Implementation Details
- **Evaluator** loads YAML on startup, evaluates ALL achievements for each new match
- **Conditions** (`achievements/conditions.py`) - Factory pattern creates condition objects from YAML
- **Personal records** stored in `PlayerRecord` table (max/min tracking per stat)

## Development Workflows

### Running Locally
```bash
# Setup (one-time)
docker-compose up -d db  # Start PostgreSQL
alembic upgrade head     # Run migrations

# Development
lol-data-center run      # Start polling service
lol-data-center add-player "GameName#TAG" --region europe
```

### Docker Deployment
```bash
docker-compose up -d                    # Start all services
docker-compose --profile tools up -d    # Include Adminer (DB UI)
docker logs -f lol-data-center          # View logs
```

### Testing
```bash
pytest                           # All tests
pytest --cov=lol_data_center     # With coverage
pytest tests/services/           # Specific module
```

**Test patterns:**
- Use fixtures from `tests/conftest.py` (pre-created players, matches, DTOs)
- Async tests use `pytest-asyncio` with `async_session` fixture
- Mock external APIs: `client.get_summoner_by_puuid = AsyncMock(return_value=...)`

## Code Conventions

### Type Hints
- **Strict typing enforced** via `mypy --strict` - all functions need return types and param types
- Use `Optional[T]` for nullable fields (e.g., `summoner_id: Optional[str]`)
- Services return domain models, not DTOs (e.g., `TrackedPlayer`, not `SummonerDto`)

### Logging
- Use structured logging: `logger.info("message", key1=value1, key2=value2)`
- Import: `from lol_data_center.logging_config import get_logger`
- Never use `print()` - all output goes through `structlog`

### Error Handling
- **Riot API errors:** Caught in `PollingService`, logged but don't crash loop
- **Achievement evaluation errors:** Isolated per-achievement (one failure doesn't block others)
- **Validation errors:** Pydantic raises `ValidationError` - caught and logged with response body

### File Organization
- `schemas/` - Pydantic models for API responses (DTOs)
- `database/models.py` - SQLAlchemy ORM models (entities)
- `services/` - Business logic layer (DB + event publishing)
- `api_client/` - External API interaction (Riot)
- `notifications/` - Outbound integrations (Discord)

## Common Tasks

### Adding a New Achievement
1. Edit `achievements.yaml` - add entry with unique `id`
2. Restart app (achievements loaded at startup)
3. No code changes needed unless adding new condition type

### Adding a New Stat Field
1. Update `ParticipantDto` in `schemas/riot_api.py`
2. Update `MatchParticipant` in `database/models.py`
3. Create Alembic migration: `alembic revision --autogenerate`
4. Update `match_service.py` to save new field

### Adding a New Event Subscriber
```python
class MyComponent:
    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus or get_event_bus()
    
    def subscribe(self):
        self._event_bus.subscribe(NewMatchEvent, self._handle_match)
    
    async def _handle_match(self, event: NewMatchEvent) -> None:
        # Your logic here
        pass
```

Register in `main.py` before `polling_service.start()`

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```
asyncpg.exceptions.InvalidCatalogNameError: database "lol_data_center" does not exist
```
Solution: Create the database first:
```bash
docker-compose exec db psql -U postgres -c "CREATE DATABASE lol_data_center;"
```

**2. Riot API Rate Limiting**
```
RiotApiError: 429 Too Many Requests
```
Solution: The `RateLimiter` should handle this automatically. If it persists:
- Check `POLLING_INTERVAL_SECONDS` (default 300s = 5 min)
- Reduce number of tracked players
- Verify rate limit: 100 requests / 2 minutes

**3. Import Errors After Installing**
```
ModuleNotFoundError: No module named 'lol_data_center'
```
Solution: Ensure you installed in editable mode: `pip install -e ".[dev]"`

**4. Alembic Migration Conflicts**
```
alembic.util.exc.CommandError: Target database is not up to date.
```
Solution: Check current revision and upgrade:
```bash
alembic current              # Show current revision
alembic history              # Show all revisions
alembic upgrade head         # Upgrade to latest
```

**5. Invalid API Responses**
If you see validation errors, check `data/invalid_responses/` directory for saved responses. These help debug Riot API schema changes.

### Testing Issues

**Async test failures:**
- Ensure `pytest-asyncio` is installed: `pip install pytest-asyncio`
- Check `pyproject.toml` has `asyncio_mode = "auto"`

**Database test issues:**
- Tests use in-memory SQLite (`sqlite+aiosqlite:///:memory:`)
- Each test gets fresh DB via `async_session` fixture
- If tests fail with DB errors, check fixtures in `tests/conftest.py`

## Security Considerations

### API Key Management
- **NEVER** commit `RIOT_API_KEY` or `DISCORD_WEBHOOK_URL` to source control
- Use `.env` file (already in `.gitignore`)
- Docker Compose reads from `.env` automatically
- In production, use environment variables or secrets management

### Database Security
- Use **strong passwords** for PostgreSQL in production
- Never expose database port (5432) to public internet
- Connection strings with credentials should be in `.env` only

### Rate Limiting
- `RateLimiter` prevents API abuse (token bucket algorithm)
- Respects `Retry-After` headers from Riot API
- Default limit: 100 requests / 2 minutes (configurable)

### Input Validation
- All Riot API responses validated via Pydantic schemas
- Invalid responses logged and saved for debugging
- Discord webhook URLs validated before use

### Error Handling
- Services catch and log errors without exposing sensitive data
- No raw exception messages sent to Discord notifications
- Structured logging redacts sensitive fields

## External Dependencies

### Required APIs
- **Riot Games API** - Get your API key at https://developer.riotgames.com/
  - Free tier: 20 requests/second, 100 requests/2 minutes
  - Development keys expire every 24 hours (need renewal)
  - Production keys require application approval
  
- **Discord Webhooks** - Create in Discord server settings
  - Server Settings → Integrations → Webhooks
  - Copy webhook URL to `.env`

### Python Packages
- **SQLAlchemy 2.0+** - Async ORM (breaking changes from 1.x)
- **Pydantic 2.5+** - Data validation (v2 has different API than v1)
- **aiohttp** - Async HTTP client
- **structlog** - Structured logging
- **Alembic** - Database migrations
