#!/bin/bash
# Bazaar of Lies — One-command match start.
# Usage: ./tools/start-match.sh

set -euo pipefail

# Change to the arena root
cd "$(dirname "$0")/.."

# Reset the arena (keep match counter)
echo "Resetting the arena (keeping match counter)..."
uv run src/town-reset.py --keep-match <<< "y\ny\n"

# Pull the latest bot code
echo "Pulling the latest bot code..."
uv run tools/seats-pull.py

# Extract API key from env.sh
echo "Starting the match..."
export MISTRAL_API_KEY="$(sed -n 's/^export MISTRAL_API_KEY="\(.*\)"$/\1/p' ../env.sh)"

# Launch all bots
tools/bazaar-launch.sh start

# Notify user
echo "Match started. Attach to tmux: tmux attach -t bazaar"