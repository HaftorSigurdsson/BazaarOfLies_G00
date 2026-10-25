#!/bin/bash
# Bazaar of Lies — Spectator mode.
# Usage: ./tools/spectator.sh

set -euo pipefail

# Create a read-only tmux session
SESSION_NAME="bazaar-spectator"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Attaching to existing spectator session..."
    tmux attach -t "$SESSION_NAME"
    exit 0
fi

# Start a new session
TMUX_CMD="tmux new-session -d -s $SESSION_NAME"

# Window 1: Live Herald PDFs
$TMUX_CMD "echo '=== Live Herald PDFs ==='; 
           while true; do
               ls -t gameplay/library/herald-*.pdf 2>/dev/null | head -5 | xargs -I {} echo "{}"; 
               sleep 10;
           done"

# Window 2: Real-time statements
$TMUX_CMD "split-window -h 'echo "=== Real-Time Statements ==="; 
           tail -f gameplay/village/statements/*.jsonl 2>/dev/null || echo "No statements yet"'

# Window 3: Night chat (REAL + decoys, labeled)
$TMUX_CMD "split-window -v 'echo "=== Night Chat (REAL + Decoys) ==="; 
           while true; do
               for file in gameplay/night/chat/*.enc; do
                   echo "--- $file ---";
                   if [[ $file == *"seat-01"* ]] || [[ $file == *"seat-02"* ]] || [[ $file == *"seat-10"* ]]; then
                       echo "[REAL]";
                   else
                       echo "[DECOY]";
                   fi;
                   cat "$file" 2>/dev/null || echo "Sealed";
                   echo;
               done;
               sleep 15;
           done'

# Window 4: Game state
$TMUX_CMD "select-pane -t 0; split-window -v 'echo "=== Game State ==="; 
           while true; do
               cat gameplay/state.json 2>/dev/null || echo "No state yet"; 
               sleep 10;
           done'

# Attach to the session
echo "Spectator session started. Attach with: tmux attach -t $SESSION_NAME"
tmux attach -t "$SESSION_NAME"