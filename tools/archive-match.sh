#!/bin/bash
# Bazaar of Lies — Archive a completed match.
# Usage: ./tools/archive-match.sh <match-number>

set -euo pipefail

MATCH=$1
ARENA_ROOT="$(dirname "$0")/.."
ARCHIVE_DIR="$ARENA_ROOT/archive/match-$MATCH"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Copy match artifacts
cp -r "$ARENA_ROOT/gameplay/library/"* "$ARCHIVE_DIR/"
cp "$ARENA_ROOT/gameplay/village/match-$MATCH-*" "$ARCHIVE_DIR/"

# Compress the archive
cd "$ARENA_ROOT/archive"
tar -czf "match-$MATCH.tar.gz" "match-$MATCH"

# Clean up
rm -rf "$ARCHIVE_DIR"

# Notify user
echo "Archived match $MATCH to $ARENA_ROOT/archive/match-$MATCH.tar.gz"