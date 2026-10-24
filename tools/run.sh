#!/usr/bin/env bash
# run.sh — run the NEUTRAL side on this clone: the Herald (morning/evening
# newspaper) and, optionally, the local GM heartbeat (town-clock.py, which
# dispatches the GitHub Action every 5 minutes). The bots themselves are
# launched by bazaar-launch.sh from the seat clones.
#
# Usage:
#   ./run.sh [start]   # Herald + GM heartbeat in tmux session "bazaar-neutrals"
#   ./run.sh stop
#   ./run.sh status
#
# MISTRAL_API_KEY must be exported in this shell (the Herald needs it).
# NOTE: if the GitHub Action gm.yml is scheduled, do not also run
# town-clock.py — pick one GM driver. Edit the new-window line below to
# drop the clock window.
set -euo pipefail

SESSION="bazaar-neutrals"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CMD="${1:-start}"

cmd_start() {
    if [[ -z "${MISTRAL_API_KEY:-}" ]]; then
        echo "ERROR: MISTRAL_API_KEY is not set in this shell." >&2
        echo '       export MISTRAL_API_KEY="..." and retry.' >&2
        exit 1
    fi
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "ERROR: tmux session '$SESSION' already exists — run '$0 stop' first." >&2
        exit 1
    fi
    tmux new-session -d -s "$SESSION" -n dummy
    tmux set-environment -t "$SESSION" MISTRAL_API_KEY "$MISTRAL_API_KEY"
    tmux new-window -d -t "$SESSION" -n herald -c "$REPO_ROOT" \
        "uv run src/town-herald.py"
    tmux new-window -d -t "$SESSION" -n clock -c "$REPO_ROOT" \
        "uv run src/town-clock.py"
    tmux kill-window -t "$SESSION:dummy"
    echo "neutral side up: Herald + GM heartbeat (tmux attach -t $SESSION)"
}

cmd_stop() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
        echo "stopped '$SESSION'"
    else
        echo "no session '$SESSION' running"
    fi
}

cmd_status() {
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "no session '$SESSION' running"
        exit 1
    fi
    tmux list-windows -t "$SESSION" -F '#W' | while read -r w; do
        last=$(tmux capture-pane -p -t "$SESSION:$w" -S -50 2>/dev/null \
               | grep -v '^[[:space:]]*$' | tail -1)
        printf '%-10s %s\n' "$w" "${last:-<no output yet>}"
    done
}

case "$CMD" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    *)      echo "usage: $0 [start|stop|status]" >&2; exit 1 ;;
esac
