# Discord Stats Feature - Sub-Issues

This document breaks down the large Discord stats feature request into manageable sub-issues. Each sub-issue can be created as a separate GitHub issue.

## Quick Start

**To create these issues in GitHub:**

1. Navigate to the `.github/issues/` directory in this repository
2. Each issue is prepared as a separate markdown file
3. Use the provided script to create all issues at once:
   ```bash
   cd .github/issues
   ./create-issues.sh
   ```
4. Or manually create issues by copying content from the markdown files

See `.github/issues/README.md` for detailed instructions.

---

## Issue #1: Add Match Timeline Data to Database

**Priority:** High (Prerequisite for other features)

**Description:**
Add support for storing match timeline data from the Riot API. Timeline data contains detailed event information about what happened during a match (kills, objectives, item purchases, etc.). Since timeline events have varying structures, store them as JSON in the database.

**Acceptance Criteria:**
- [ ] Add new database table/column to store match timeline data as JSON
- [ ] Update `RiotApiClient` to fetch timeline data via `/lol/match/v5/matches/{matchId}/timeline` endpoint
- [ ] Create Pydantic schemas for timeline response validation
- [ ] Update `MatchService.save_match()` to fetch and store timeline data when saving a match
- [ ] Add database migration for the schema changes
- [ ] Timeline data is fetched during both polling and backfill operations
- [ ] Handle cases where timeline data is unavailable (older matches)

**Technical Notes:**
- Timeline API endpoint: `GET /lol/match/v5/matches/{matchId}/timeline`
- Store entire timeline JSON in a new `match_timeline` column (PostgreSQL JSONB type)
- Add error handling for timeline fetch failures (should not prevent match from being saved)
- Consider adding timeline fetch as an optional/async operation to avoid blocking match saves

**Dependencies:**
None

**Estimated Effort:** Medium (4-6 hours)

---

## Issue #2: Add Champion Reference Data Table

**Priority:** High (Prerequisite for stats aggregation)

**Description:**
Create a reference table for champion data that maps champion IDs to champion names and other relevant information. Currently, the system relies on champion names from match data, but a reference table will enable better querying and ensure consistency.

**Acceptance Criteria:**
- [ ] Add `champions` reference table with: `champion_id`, `name`, `title`, `key` (string identifier)
- [ ] Create a data seeding mechanism to populate champion data (from Riot Data Dragon or static JSON)
- [ ] Add database migration for the new table
- [ ] (Optional) Add periodic update mechanism to fetch latest champion data
- [ ] Update queries to use champion reference table where appropriate

**Technical Notes:**
- Champion data source: Riot Data Dragon (e.g., `https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json`)
- Store champion key (string like "Ahri"), name, and title
- Consider versioning if champion data changes over time
- Add a CLI command to seed/update champion data: `lol-data-center update-champion-data`

**Dependencies:**
None

**Estimated Effort:** Small (2-3 hours)

---

## Issue #3: Create Stats Aggregation Service

**Priority:** High (Core feature)

**Description:**
Implement a service that calculates aggregated statistics grouped by role or champion. This service should compute average, minimum, maximum, and standard deviation for relevant stats.

**Acceptance Criteria:**
- [ ] Create `StatsAggregationService` with methods:
  - `get_stats_by_role(puuid, role, stat_fields)` → returns aggregated stats for a player in a specific role
  - `get_stats_by_champion(puuid, champion_id, stat_fields)` → returns aggregated stats for a player with a specific champion
  - `get_overall_stats(puuid, stat_fields)` → returns aggregated stats across all games
- [ ] Calculate average, min, max, and standard deviation for specified stat fields
- [ ] Support filtering by time range (e.g., last 30 days, season, all time)
- [ ] Optimize queries for performance (use database aggregation functions where possible)
- [ ] Add unit tests for aggregation logic
- [ ] Include game count for each aggregation group

**Technical Notes:**
- Use SQLAlchemy's aggregation functions: `func.avg()`, `func.min()`, `func.max()`, `func.stddev_samp()`
- For SQLite compatibility in tests, may need to compute standard deviation in Python
- Common stat fields: kills, deaths, assists, kda, gold_earned, total_damage_dealt_to_champions, vision_score, total_minions_killed
- Consider caching aggregations for frequently requested data

**Dependencies:**
- Issue #2 (Champion Reference Data) - Optional but recommended for better querying

**Estimated Effort:** Medium (5-7 hours)

---

## Issue #4: Add Discord Command for Viewing Aggregated Stats

**Priority:** Medium

**Description:**
Create Discord slash commands that allow users to view their aggregated statistics grouped by role or champion.

**Acceptance Criteria:**
- [ ] Add `/stats role <role>` command - shows aggregated stats for a specific role (TOP, JUNGLE, MID, ADC, SUPPORT)
- [ ] Add `/stats champion <champion_name>` command - shows aggregated stats for a specific champion
- [ ] Add `/stats overall` command - shows aggregated stats across all games
- [ ] Display stats in a formatted Discord embed with:
  - Average, min, max, std deviation for key stats
  - Game count for the filter
  - Time period (if applicable)
- [ ] Add optional time filter parameter: `--period <last_7_days|last_30_days|season|all_time>`
- [ ] Show user-friendly error messages when no data is found
- [ ] Add auto-complete for champion names

**Technical Notes:**
- Use Discord.py's application commands framework
- Create rich embeds using `discord.Embed`
- Format numbers appropriately (e.g., round to 2 decimal places, format large numbers)
- Consider pagination if stats exceed embed limits
- Use the champion reference table for auto-complete suggestions

**Dependencies:**
- Issue #2 (Champion Reference Data)
- Issue #3 (Stats Aggregation Service)

**Estimated Effort:** Medium (4-5 hours)

---

## Issue #5: Add Discord Command for Viewing N-th Past Game

**Priority:** Medium

**Description:**
Create a Discord command that displays the stats from the n-th most recent game for a player.

**Acceptance Criteria:**
- [ ] Add `/game <n>` command - shows stats from the n-th most recent game (1 = most recent)
- [ ] Display comprehensive game information in Discord embed:
  - Match ID, date/time, duration
  - Champion played, role
  - KDA, damage, gold, CS, vision score
  - Items (with item icons if possible)
  - Win/Loss status
  - Link to match details (if applicable)
- [ ] Handle invalid input (n too large, negative numbers, etc.)
- [ ] Show error if player has no games recorded

**Technical Notes:**
- Query `MatchParticipant` ordered by `game_creation` DESC with offset
- Use Discord embeds with appropriate colors (green for win, red for loss)
- Consider adding reactions for navigation (◀️ ▶️) to browse through games
- Item icons can be fetched from Riot Data Dragon if desired

**Dependencies:**
None

**Estimated Effort:** Small (3-4 hours)

---

## Issue #6: Add Stats Visualization Service

**Priority:** Low (Enhancement)

**Description:**
Implement a service that generates charts and graphs to visualize player statistics. Support line diagrams (for trends over time) and column/bar charts (for comparing categories).

**Acceptance Criteria:**
- [ ] Add `matplotlib` or similar charting library to dependencies
- [ ] Create `StatsVisualizationService` with methods:
  - `generate_line_chart(x_data, y_data, labels)` → creates line chart showing stat progression
  - `generate_bar_chart(categories, values, labels)` → creates bar chart comparing values
  - `generate_multi_stat_chart(data, labels)` → creates chart with multiple stats
- [ ] Charts saved as PNG images to temporary files or in-memory buffers
- [ ] Include proper labels, legends, and titles
- [ ] Use appropriate colors and styling
- [ ] Clean up temporary files after use

**Technical Notes:**
- Libraries: `matplotlib` (robust, feature-rich) or `plotly` (modern, interactive)
- For Discord, generate static PNG images
- Consider color schemes that work well in Discord (both light/dark themes)
- Chart dimensions should fit well in Discord messages (recommended: 800x600 or 1200x800)
- Save to `/tmp` directory or use `BytesIO` for in-memory handling

**Dependencies:**
- Issue #3 (Stats Aggregation Service) - for data to visualize

**Estimated Effort:** Medium (6-8 hours)

---

## Issue #7: Integrate Graphics into Discord Commands

**Priority:** Low (Enhancement)

**Description:**
Enhance Discord commands to include visual charts and graphs alongside text-based statistics.

**Acceptance Criteria:**
- [ ] Update `/stats` commands to include optional `--chart` flag
- [ ] When `--chart` is enabled, attach generated chart image to the response
- [ ] Add `/trend <stat> [timeframe]` command - shows line chart of stat over time
- [ ] Add `/compare <category>` command - shows bar chart comparing performance across roles/champions
- [ ] Charts upload correctly to Discord as image attachments
- [ ] Add error handling for chart generation failures
- [ ] Ensure temporary chart files are cleaned up

**Technical Notes:**
- Use Discord's file upload feature: `discord.File()`
- Attach charts to embeds using `embed.set_image()`
- Consider adding caching to avoid regenerating identical charts
- Add command cooldowns to prevent abuse/spam
- Provide text fallback if chart generation fails

**Dependencies:**
- Issue #3 (Stats Aggregation Service)
- Issue #4 (Discord Commands for Aggregated Stats)
- Issue #6 (Stats Visualization Service)

**Estimated Effort:** Small (3-4 hours)

---

## Implementation Order Recommendation

1. **Phase 1 - Data Foundation** (Issues #1, #2)
   - Add timeline data storage
   - Add champion reference table
   
2. **Phase 2 - Core Stats Features** (Issues #3, #4, #5)
   - Implement stats aggregation service
   - Add Discord commands for stats viewing
   - Add command for n-th game viewing
   
3. **Phase 3 - Visualization Enhancement** (Issues #6, #7)
   - Implement visualization service
   - Integrate charts into Discord commands

---

## Total Estimated Effort

- High Priority: 11-16 hours
- Medium Priority: 11-14 hours  
- Low Priority: 9-12 hours
- **Total: 31-42 hours** (approximately 1-2 weeks for a single developer)

---

## Notes

- Each issue should be independently testable
- Consider feature flags for gradual rollout
- Update documentation as features are completed
- Add rate limiting to prevent Discord API abuse
- Consider adding analytics/metrics for feature usage
