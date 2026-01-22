#!/bin/bash

# Script to create GitHub issues from markdown files
# Requires GitHub CLI (gh) to be installed and authenticated

set -e

REPO="LeXeS2/lol-data-center"
ISSUES_DIR=".github/issues"

echo "Creating GitHub issues for Discord Stats feature..."
echo "Repository: $REPO"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI."
    echo "Please run: gh auth login"
    exit 1
fi

# Function to extract title from markdown file
get_title() {
    grep -m 1 "^# " "$1" | sed 's/^# //'
}

# Function to extract labels from markdown file
get_labels() {
    grep "^\*\*Labels:\*\*" "$1" | sed 's/^**Labels:** //' | sed 's/`//g' | tr -d ' '
}

# Function to extract body (everything after the labels line)
get_body() {
    sed -n '/^## Description/,$p' "$1"
}

# Create issues in order
issues=(
    "issue-1-match-timeline-data.md"
    "issue-2-champion-reference-data.md"
    "issue-3-stats-aggregation-service.md"
    "issue-4-discord-aggregated-stats-command.md"
    "issue-5-discord-nth-game-command.md"
    "issue-6-stats-visualization-service.md"
    "issue-7-integrate-graphics-discord.md"
)

for issue_file in "${issues[@]}"; do
    file_path="$ISSUES_DIR/$issue_file"
    
    if [ ! -f "$file_path" ]; then
        echo "Warning: File not found: $file_path"
        continue
    fi
    
    title=$(get_title "$file_path")
    labels=$(get_labels "$file_path")
    body=$(get_body "$file_path")
    
    echo "Creating issue: $title"
    
    # Create the issue
    gh issue create \
        --repo "$REPO" \
        --title "$title" \
        --body "$body" \
        --label "$labels"
    
    echo "✓ Created"
    echo ""
    
    # Small delay to avoid rate limiting
    sleep 1
done

echo "All issues created successfully!"
echo ""
echo "View issues at: https://github.com/$REPO/issues"
