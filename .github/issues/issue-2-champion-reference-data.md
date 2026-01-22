# Add Champion Reference Data Table

**Labels:** `enhancement`, `database`, `high-priority`

## Description

Create a reference table for champion data that maps champion IDs to champion names and other relevant information. Currently, the system relies on champion names from match data, but a reference table will enable better querying and ensure consistency.

## Acceptance Criteria

- [ ] Add `champions` reference table with: `champion_id`, `name`, `title`, `key` (string identifier)
- [ ] Create a data seeding mechanism to populate champion data (from Riot Data Dragon or static JSON)
- [ ] Add database migration for the new table
- [ ] (Optional) Add periodic update mechanism to fetch latest champion data
- [ ] Update queries to use champion reference table where appropriate

## Technical Notes

- Champion data source: Riot Data Dragon (e.g., `https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json`)
- Store champion key (string like "Ahri"), name, and title
- Consider versioning if champion data changes over time
- Add a CLI command to seed/update champion data: `lol-data-center update-champion-data`

## Dependencies

None

## Estimated Effort

Small (2-3 hours)
