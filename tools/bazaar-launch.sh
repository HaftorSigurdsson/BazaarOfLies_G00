#!/usr/bin/env bash
# bazaar-launch.sh — thin wrapper: the implementation is cross-platform
# Python (tmux on macOS/Linux, console windows on Windows). See
# bazaar_launch.py for usage and environment variables.
set -euo pipefail
exec python3 "$(dirname "$0")/bazaar_launch.py" "$@"
