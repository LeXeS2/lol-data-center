# Add Stats Visualization Service

**Labels:** `enhancement`, `feature`, `visualization`

## Description

Implement a service that generates charts and graphs to visualize player statistics. Support line diagrams (for trends over time) and column/bar charts (for comparing categories).

## Acceptance Criteria

- [ ] Add `matplotlib` or similar charting library to dependencies
- [ ] Create `StatsVisualizationService` with methods:
  - `generate_line_chart(x_data, y_data, labels)` → creates line chart showing stat progression
  - `generate_bar_chart(categories, values, labels)` → creates bar chart comparing values
  - `generate_multi_stat_chart(data, labels)` → creates chart with multiple stats
- [ ] Charts saved as PNG images to temporary files or in-memory buffers
- [ ] Include proper labels, legends, and titles
- [ ] Use appropriate colors and styling
- [ ] Clean up temporary files after use

## Technical Notes

- Libraries: `matplotlib` (robust, feature-rich) or `plotly` (modern, interactive)
- For Discord, generate static PNG images
- Consider color schemes that work well in Discord (both light/dark themes)
- Chart dimensions should fit well in Discord messages (recommended: 800x600 or 1200x800)
- Save to `/tmp` directory or use `BytesIO` for in-memory handling

## Dependencies

- Issue #3 (Stats Aggregation Service) - for data to visualize

## Estimated Effort

Medium (6-8 hours)
