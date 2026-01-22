# Add Discord Command for Viewing N-th Past Game

**Labels:** `enhancement`, `discord`, `feature`

## Description

Create a Discord command that displays the stats from the n-th most recent game for a player.

## Acceptance Criteria

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

## Technical Notes

- Query `MatchParticipant` ordered by `game_creation` DESC with offset
- Use Discord embeds with appropriate colors (green for win, red for loss)
- Consider adding reactions for navigation (◀️ ▶️) to browse through games
- Item icons can be fetched from Riot Data Dragon if desired

## Dependencies

None

## Estimated Effort

Small (3-4 hours)
