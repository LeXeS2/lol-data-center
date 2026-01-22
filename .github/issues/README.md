# GitHub Issues for Discord Stats Feature

This directory contains issue templates for the Discord Stats feature breakdown. Each file represents a GitHub issue that should be created.

## How to Create These Issues

Since we cannot directly create GitHub issues programmatically from this environment, you have two options:

### Option 1: Manual Creation (Recommended for Small Number of Issues)

1. Go to https://github.com/LeXeS2/lol-data-center/issues/new
2. Copy the content from each issue file in this directory
3. Paste into the GitHub issue creation form
4. Add the labels specified at the top of each file
5. Submit the issue

### Option 2: Use GitHub CLI (Recommended for Automation)

If you have GitHub CLI installed (`gh`), you can run the provided script:

```bash
# Make sure you're authenticated with GitHub CLI first
gh auth login

# Run the script to create all issues
./create-issues.sh
```

## Issue List

1. **issue-1-match-timeline-data.md** - Add Match Timeline Data to Database (High Priority)
2. **issue-2-champion-reference-data.md** - Add Champion Reference Data Table (High Priority)
3. **issue-3-stats-aggregation-service.md** - Create Stats Aggregation Service (High Priority)
4. **issue-4-discord-aggregated-stats-command.md** - Add Discord Command for Viewing Aggregated Stats
5. **issue-5-discord-nth-game-command.md** - Add Discord Command for Viewing N-th Past Game
6. **issue-6-stats-visualization-service.md** - Add Stats Visualization Service
7. **issue-7-integrate-graphics-discord.md** - Integrate Graphics into Discord Commands

## Implementation Order

It's recommended to tackle these issues in phases:

**Phase 1 - Data Foundation** (Issues #1, #2)
- Start with adding timeline data and champion reference table
- These are prerequisites for later features

**Phase 2 - Core Stats Features** (Issues #3, #4, #5)
- Implement stats aggregation and basic Discord commands
- Users can start viewing their stats

**Phase 3 - Visualization Enhancement** (Issues #6, #7)
- Add charting capabilities
- Enhance Discord commands with graphics

See `SUBISSUES.md` in the root directory for detailed descriptions and planning information.
