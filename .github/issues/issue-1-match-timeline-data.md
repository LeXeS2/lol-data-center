# Add Match Timeline Data to Database

**Labels:** `enhancement`, `database`, `high-priority`

## Description

Add support for storing match timeline data from the Riot API. Timeline data contains detailed event information about what happened during a match (kills, objectives, item purchases, etc.). Since timeline events have varying structures, store them as JSON in the database.

## Acceptance Criteria

- [ ] Add new database table/column to store match timeline data as JSON
- [ ] Update `RiotApiClient` to fetch timeline data via `/lol/match/v5/matches/{matchId}/timeline` endpoint
- [ ] Create Pydantic schemas for timeline response validation
- [ ] Update `MatchService.save_match()` to fetch and store timeline data when saving a match
- [ ] Add database migration for the schema changes
- [ ] Timeline data is fetched during both polling and backfill operations
- [ ] Handle cases where timeline data is unavailable (older matches)

## Technical Notes

- Timeline API endpoint: `GET /lol/match/v5/matches/{matchId}/timeline`
- Store entire timeline JSON in a new `match_timeline` column (PostgreSQL JSONB type)
- Add error handling for timeline fetch failures (should not prevent match from being saved)
- Consider adding timeline fetch as an optional/async operation to avoid blocking match saves

## Dependencies

None

## Estimated Effort

Medium (4-6 hours)
