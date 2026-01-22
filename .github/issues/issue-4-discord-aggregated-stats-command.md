# Add Discord Command for Viewing Aggregated Stats

**Labels:** `enhancement`, `discord`, `feature`

## Description

Create Discord slash commands that allow users to view their aggregated statistics grouped by role or champion.

## Acceptance Criteria

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

## Technical Notes

- Use Discord.py's application commands framework
- Create rich embeds using `discord.Embed`
- Format numbers appropriately (e.g., round to 2 decimal places, format large numbers)
- Consider pagination if stats exceed embed limits
- Use the champion reference table for auto-complete suggestions

## Dependencies

- Issue #2 (Champion Reference Data)
- Issue #3 (Stats Aggregation Service)

## Estimated Effort

Medium (4-5 hours)
