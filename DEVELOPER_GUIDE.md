# Discord Stats Feature - Developer Quick Start Guide

This guide helps developers get started with implementing the Discord stats feature sub-issues.

## Before You Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Discord developer account (for bot testing)
- Riot API key
- Familiarity with the codebase (see README.md)

### Development Environment Setup
```bash
# Clone and setup
git clone https://github.com/LeXeS2/lol-data-center.git
cd lol-data-center
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your RIOT_API_KEY, DATABASE_URL, etc.

# Setup database
docker-compose up -d db
alembic upgrade head

# Run tests to verify setup
pytest
```

### Key Directories
- `src/lol_data_center/` - Main application code
  - `database/models.py` - ORM models
  - `schemas/riot_api.py` - Pydantic schemas
  - `services/` - Business logic services
  - `api_client/riot_client.py` - Riot API client
  - `notifications/` - Discord integration
- `tests/` - Test suite
- `alembic/versions/` - Database migrations

## Implementation Guide by Issue

### Issue #1: Match Timeline Data

**Files to modify:**
- `src/lol_data_center/database/models.py` - Add timeline column to Match model
- `src/lol_data_center/schemas/riot_api.py` - Add TimelineDto
- `src/lol_data_center/api_client/riot_client.py` - Add get_timeline() method
- `src/lol_data_center/services/match_service.py` - Update save_match()
- Create migration: `alembic revision --autogenerate -m "add_match_timeline"`

**Example timeline column:**
```python
# In Match model
from sqlalchemy.dialects.postgresql import JSONB

timeline_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

**Testing:**
```bash
pytest tests/services/test_match_service.py -v
```

### Issue #2: Champion Reference Data

**Files to create/modify:**
- `src/lol_data_center/database/models.py` - Add Champion model
- `src/lol_data_center/services/champion_service.py` - Create new service
- `src/lol_data_center/cli.py` - Add update-champion-data command
- `src/lol_data_center/data/champions.json` - Static champion data (optional)
- Create migration: `alembic revision --autogenerate -m "add_champions_table"`

**Example Champion model:**
```python
class Champion(Base):
    __tablename__ = "champions"
    
    champion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
```

**Data source:**
```
https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/champion.json
```

**Testing:**
```bash
lol-data-center update-champion-data
pytest tests/services/test_champion_service.py -v
```

### Issue #3: Stats Aggregation Service

**Files to create:**
- `src/lol_data_center/services/stats_aggregation_service.py` - New service
- `tests/services/test_stats_aggregation_service.py` - Tests

**Example service structure:**
```python
class StatsAggregationService:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_stats_by_role(
        self,
        puuid: str,
        role: str,
        stat_fields: list[str],
        time_filter: TimeFilter | None = None,
    ) -> StatsAggregation:
        # Use SQLAlchemy func.avg(), func.min(), func.max()
        # For std dev, use func.stddev_samp() or compute in Python
        pass
```

**Testing:**
```bash
pytest tests/services/test_stats_aggregation_service.py -v
```

### Issue #4: Discord Aggregated Stats Command

**Files to modify/create:**
- Find Discord bot implementation (likely in `src/lol_data_center/notifications/`)
- Add new cog or commands module
- Use discord.py's app_commands

**Example command:**
```python
@app_commands.command()
@app_commands.describe(
    role="The role to view stats for (TOP, JUNGLE, MID, ADC, SUPPORT)"
)
async def stats_role(interaction: discord.Interaction, role: str):
    # Get player PUUID from interaction.user or database
    # Use StatsAggregationService
    # Create discord.Embed with results
    await interaction.response.send_message(embed=embed)
```

**Testing:**
- Manual testing in a Discord test server
- Consider adding unit tests for embed formatting

### Issue #5: N-th Past Game Command

**Files to modify:**
- Discord bot implementation

**Example command:**
```python
@app_commands.command()
@app_commands.describe(n="Game number (1 = most recent)")
async def game(interaction: discord.Interaction, n: int):
    # Validate n > 0
    # Query MatchParticipant with offset
    # Create rich embed with game details
    await interaction.response.send_message(embed=embed)
```

**Item icons:**
```
https://ddragon.leagueoflegends.com/cdn/14.1.1/img/item/{item_id}.png
```

### Issue #6: Stats Visualization Service

**Files to create:**
- `src/lol_data_center/services/stats_visualization_service.py`
- `tests/services/test_stats_visualization_service.py`

**Dependencies:**
Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing ...
    "matplotlib>=3.8.0",
    "pillow>=10.1.0",
]
```

**Example service:**
```python
from io import BytesIO
import matplotlib.pyplot as plt

class StatsVisualizationService:
    def generate_line_chart(
        self,
        x_data: list,
        y_data: list,
        title: str,
        x_label: str,
        y_label: str,
    ) -> BytesIO:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(x_data, y_data)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close(fig)
        return buffer
```

### Issue #7: Integrate Graphics

**Files to modify:**
- Discord bot commands from Issue #4

**Example integration:**
```python
@app_commands.command()
async def trend(interaction: discord.Interaction, stat: str):
    # Get data using StatsAggregationService
    # Generate chart using StatsVisualizationService
    chart_buffer = viz_service.generate_line_chart(...)
    
    file = discord.File(chart_buffer, filename="trend.png")
    embed = discord.Embed(title=f"{stat} Trend")
    embed.set_image(url="attachment://trend.png")
    
    await interaction.response.send_message(embed=embed, file=file)
```

## Development Workflow

### For Each Issue

1. **Create feature branch:**
   ```bash
   git checkout -b feature/issue-X-description
   ```

2. **Implement the feature:**
   - Write code following existing patterns
   - Add type hints (required for mypy)
   - Follow ruff style guidelines

3. **Add tests:**
   ```bash
   pytest tests/path/to/test_file.py -v
   ```

4. **Run linting:**
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   mypy src/
   ```

5. **Create migration (if database changes):**
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

6. **Run full test suite:**
   ```bash
   pytest --cov=lol_data_center
   ```

7. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: implement issue #X - description"
   git push origin feature/issue-X-description
   ```

8. **Create pull request**

## Code Style Guidelines

### Follow existing patterns:
- **Async/await** for I/O operations
- **Type hints** on all functions
- **Dependency injection** via constructor
- **Service layer** for business logic
- **Structured logging** using structlog
- **Error handling** with specific exceptions

### Example service pattern:
```python
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

class MyService:
    """Service description."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.
        
        Args:
            session: Database session
        """
        self._session = session
    
    async def my_method(self, param: str) -> ReturnType:
        """Method description.
        
        Args:
            param: Parameter description
            
        Returns:
            Return value description
        """
        logger.info("Doing something", param=param)
        # Implementation
        return result
```

## Common Pitfalls

1. **Database sessions:** Always use async context manager
   ```python
   async with get_async_session() as session:
       # Use session
   ```

2. **Discord rate limits:** Add cooldowns to commands
   ```python
   @app_commands.checks.cooldown(1, 10.0)  # 1 use per 10 seconds
   ```

3. **Memory leaks:** Close matplotlib figures
   ```python
   plt.close(fig)
   ```

4. **Timezone issues:** Use UTC for timestamps
   ```python
   from datetime import datetime, timezone
   now = datetime.now(timezone.utc)
   ```

5. **SQL injection:** Always use SQLAlchemy's parameter binding
   ```python
   # Good
   stmt = select(Model).where(Model.field == value)
   # Bad
   stmt = text(f"SELECT * FROM model WHERE field = {value}")
   ```

## Getting Help

- **Codebase questions:** Check `copilot-instructions.md`
- **Discord.py:** https://discordpy.readthedocs.io/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Riot API:** https://developer.riotgames.com/

## Useful Commands

```bash
# Run specific test
pytest tests/path/to/test.py::test_function -v

# Watch mode for development
pytest-watch tests/

# Database console (if using Docker)
docker-compose exec db psql -U postgres lol_data_center

# Check migration status
alembic current
alembic history

# Format code
ruff format src/ tests/

# Type check
mypy src/

# Start application
lol-data-center run
```

Good luck with the implementation! 🚀
