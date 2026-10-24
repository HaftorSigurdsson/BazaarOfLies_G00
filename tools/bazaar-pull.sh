#!/usr/bin/env bash
# bazaar-pull.sh — thin wrapper: pull every seat clone and report state.
# See seats-pull.py (same directory) for the implementation.
set -euo pipefail
exec python3 "$(dirname "$0")/seats-pull.py" "$@"
