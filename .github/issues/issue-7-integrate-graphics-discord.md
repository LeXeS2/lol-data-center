# Integrate Graphics into Discord Commands

**Labels:** `enhancement`, `discord`, `visualization`

## Description

Enhance Discord commands to include visual charts and graphs alongside text-based statistics.

## Acceptance Criteria

- [ ] Update `/stats` commands to include optional `--chart` flag
- [ ] When `--chart` is enabled, attach generated chart image to the response
- [ ] Add `/trend <stat> [timeframe]` command - shows line chart of stat over time
- [ ] Add `/compare <category>` command - shows bar chart comparing performance across roles/champions
- [ ] Charts upload correctly to Discord as image attachments
- [ ] Add error handling for chart generation failures
- [ ] Ensure temporary chart files are cleaned up

## Technical Notes

- Use Discord's file upload feature: `discord.File()`
- Attach charts to embeds using `embed.set_image()`
- Consider adding caching to avoid regenerating identical charts
- Add command cooldowns to prevent abuse/spam
- Provide text fallback if chart generation fails

## Dependencies

- Issue #3 (Stats Aggregation Service)
- Issue #4 (Discord Commands for Aggregated Stats)
- Issue #6 (Stats Visualization Service)

## Estimated Effort

Small (3-4 hours)
