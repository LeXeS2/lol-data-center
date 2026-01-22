# Create Stats Aggregation Service

**Labels:** `enhancement`, `feature`, `high-priority`

## Description

Implement a service that calculates aggregated statistics grouped by role or champion. This service should compute average, minimum, maximum, and standard deviation for relevant stats.

## Acceptance Criteria

- [ ] Create `StatsAggregationService` with methods:
  - `get_stats_by_role(puuid, role, stat_fields)` → returns aggregated stats for a player in a specific role
  - `get_stats_by_champion(puuid, champion_id, stat_fields)` → returns aggregated stats for a player with a specific champion
  - `get_overall_stats(puuid, stat_fields)` → returns aggregated stats across all games
- [ ] Calculate average, min, max, and standard deviation for specified stat fields
- [ ] Support filtering by time range (e.g., last 30 days, season, all time)
- [ ] Optimize queries for performance (use database aggregation functions where possible)
- [ ] Add unit tests for aggregation logic
- [ ] Include game count for each aggregation group

## Technical Notes

- Use SQLAlchemy's aggregation functions: `func.avg()`, `func.min()`, `func.max()`, `func.stddev_samp()`
- For SQLite compatibility in tests, may need to compute standard deviation in Python
- Common stat fields: kills, deaths, assists, kda, gold_earned, total_damage_dealt_to_champions, vision_score, total_minions_killed
- Consider caching aggregations for frequently requested data

## Dependencies

- Issue #2 (Champion Reference Data) - Optional but recommended for better querying

## Estimated Effort

Medium (5-7 hours)
