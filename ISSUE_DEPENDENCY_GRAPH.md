# Discord Stats Feature - Issue Dependency Graph

This document visualizes the relationships and dependencies between the sub-issues.

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 1: Data Foundation                 │
│                         (High Priority, 4-9 hrs)                 │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────┐         ┌──────────────────────────┐
    │  Issue #1                │         │  Issue #2                │
    │  Match Timeline Data     │         │  Champion Reference Data │
    │  (4-6 hrs)               │         │  (2-3 hrs)               │
    └──────────────────────────┘         └──────────────────────────┘
              │                                     │
              │                                     │
              ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 2: Core Stats Features                  │
│                   (Medium Priority, 12-16 hrs)                   │
└─────────────────────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┴────────────────────┐
              │                                        │
              ▼                                        ▼
    ┌──────────────────────────┐         ┌──────────────────────────┐
    │  Issue #3                │         │  Issue #5                │
    │  Stats Aggregation       │◄────────│  N-th Game Command       │
    │  Service (5-7 hrs)       │         │  (3-4 hrs)               │
    └──────────────────────────┘         └──────────────────────────┘
              │
              │
              ▼
    ┌──────────────────────────┐
    │  Issue #4                │
    │  Aggregated Stats Command│
    │  (4-5 hrs)               │
    └──────────────────────────┘
              │
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 3: Visualization Enhancement              │
│                     (Low Priority, 9-12 hrs)                     │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
    ┌──────────────────────────┐
    │  Issue #6                │
    │  Visualization Service   │
    │  (6-8 hrs)               │
    └──────────────────────────┘
              │
              │
              ▼
    ┌──────────────────────────┐
    │  Issue #7                │
    │  Integrate Graphics      │
    │  (3-4 hrs)               │
    └──────────────────────────┘
```

## Issue Details

### Issue #1: Match Timeline Data
- **Type:** Database Enhancement
- **Priority:** High
- **Dependencies:** None
- **Blocks:** Issue #6 (provides additional data for visualization)
- **Key Deliverables:**
  - New JSONB column in database
  - Timeline API client method
  - Pydantic schemas for validation
  - Migration script

### Issue #2: Champion Reference Data
- **Type:** Database Enhancement
- **Priority:** High
- **Dependencies:** None
- **Blocks:** Issue #3, #4 (better query performance and UX)
- **Key Deliverables:**
  - Champions reference table
  - Data seeding mechanism
  - CLI command for updates
  - Migration script

### Issue #3: Stats Aggregation Service
- **Type:** Core Feature
- **Priority:** High
- **Dependencies:** Optional: Issue #2
- **Blocks:** Issue #4, #6
- **Key Deliverables:**
  - `StatsAggregationService` class
  - Methods for role/champion/overall aggregation
  - Database query optimization
  - Unit tests

### Issue #4: Aggregated Stats Discord Command
- **Type:** Discord Feature
- **Priority:** Medium
- **Dependencies:** Issue #2, #3
- **Blocks:** Issue #7
- **Key Deliverables:**
  - `/stats role` command
  - `/stats champion` command
  - `/stats overall` command
  - Formatted Discord embeds
  - Auto-complete for champions

### Issue #5: N-th Game Discord Command
- **Type:** Discord Feature
- **Priority:** Medium
- **Dependencies:** None
- **Blocks:** None
- **Key Deliverables:**
  - `/game <n>` command
  - Game details embed
  - Error handling
  - Navigation features (optional)

### Issue #6: Stats Visualization Service
- **Type:** Visualization Feature
- **Priority:** Low
- **Dependencies:** Issue #3
- **Blocks:** Issue #7
- **Key Deliverables:**
  - `StatsVisualizationService` class
  - Line chart generation
  - Bar chart generation
  - Proper styling and cleanup

### Issue #7: Integrate Graphics into Discord
- **Type:** Discord Enhancement
- **Priority:** Low
- **Dependencies:** Issue #3, #4, #6
- **Blocks:** None
- **Key Deliverables:**
  - Chart flag for `/stats` commands
  - `/trend` command
  - `/compare` command
  - Image upload to Discord
  - Error handling

## Implementation Strategy

### Parallel Work Opportunities

The following issues can be worked on in parallel:

**Sprint 1:**
- Issue #1 (Timeline Data) + Issue #2 (Champion Data)
- These are independent and can be developed simultaneously

**Sprint 2:**
- Issue #3 (Stats Aggregation) + Issue #5 (N-th Game Command)
- These have no dependency conflicts

**Sprint 3:**
- Issue #4 (Aggregated Stats Command) after Issue #3 is complete

**Sprint 4:**
- Issue #6 (Visualization Service) + Issue #7 (Graphics Integration)
- Issue #7 can start as soon as Issue #6 has the basic API defined

### Critical Path

The critical path for the complete feature:
```
Issue #2 → Issue #3 → Issue #4 → Issue #6 → Issue #7
(2-3 hrs)  (5-7 hrs)  (4-5 hrs)  (6-8 hrs)  (3-4 hrs)
Total: 20-27 hours
```

### Minimum Viable Product (MVP)

For a minimal but useful release, focus on:
```
Issue #2 → Issue #3 → Issue #4
(2-3 hrs)  (5-7 hrs)  (4-5 hrs)
Total: 11-15 hours
```

This provides users with the core stats viewing functionality without graphics.

## Testing Strategy

Each issue should include:
- **Unit tests** for service/business logic
- **Integration tests** for database operations
- **Manual testing** for Discord commands

### Test Dependencies
- Issues #3, #4, #5, #6, #7 require test data (matches in database)
- Consider creating test fixtures or using existing test data
- Discord commands may need a test server for manual verification

## Risk Assessment

### High Risk
- Issue #1: API changes or unavailable timeline data for old matches
- Issue #6: Chart rendering performance on Discord

### Medium Risk
- Issue #3: Database performance with large datasets
- Issue #4: Discord embed size limits with lots of stats

### Low Risk
- Issue #2: Static data that rarely changes
- Issue #5: Simple query with straightforward UI

## Success Metrics

- **Issue #1:** Timeline data successfully stored for 100% of new matches
- **Issue #2:** Champion table populated with all current champions
- **Issue #3:** Aggregation queries execute in < 1 second for typical datasets
- **Issue #4:** Users can view stats grouped by role/champion
- **Issue #5:** Users can navigate through game history
- **Issue #6:** Charts generated in < 2 seconds
- **Issue #7:** Charts successfully uploaded to Discord
