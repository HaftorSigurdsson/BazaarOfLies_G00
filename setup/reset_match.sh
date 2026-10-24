#!/usr/bin/env bash
# Bazaar of Lies — full arena reset (v1.2).
#
# Resets EVERYTHING a match touches so the next GM tick deals a clean game:
#   gameplay/{votes,night,dossiers,deals,herald}/ gameplay/village/statements/ day-*.jsonl
#   graveyard.md, announcements.md, state.json (pristine template)
#   local journals (seats + herald) in the vault
#
# The partial reset that skipped votes/, night/ and the journals caused the
# ghost-replay: the GM re-counted the finished match's stale ballots and
# re-banished the same seats in the same order. Never skip this script's
# steps — and the epoch guard in gm/run.py now makes even a sloppy reset
# unable to echo a finished match.
#
# Usage:
#   tools/bazaar-launch.sh stop              # bots must be down first
#   python3 setup/reset_match.sh             # run from the arena repo root
#   tools/bazaar-launch.sh start             # bots + Herald back up
#   gh workflow run gm.yml                   # optional: immediate GM tick
#
# Match recaps (gameplay/village/match-XX-recap.md) are KEPT — they are history and
# cannot interfere with a fresh match (the new epoch namespaces everything).
set -euo pipefail

# Vault: $VAULT, else the sibling vault the bots use (../.bazaar), else ~/.bazaar.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VAULT="${VAULT:-$([ -d "$(dirname "$REPO_ROOT")/.bazaar" ] && echo "$(dirname "$REPO_ROOT")/.bazaar" || echo "$HOME/.bazaar")}"

command -v git >/dev/null || { echo "git not found"; exit 1; }

echo "==> Resetting arena (vault: $VAULT)"

# 1) Clear match artifacts tracked in git, but keep the directories.
for d in gameplay/votes gameplay/night gameplay/dossiers gameplay/deals gameplay/herald gameplay/village/statements; do
  git rm -rq --ignore-unmatch "$d" 2>/dev/null || true
  mkdir -p "$d"
  touch "$d/.gitkeep"
done
git rm -q --ignore-unmatch gameplay/village/day-*.jsonl 2>/dev/null || true
rm -f gameplay/village/day-*.jsonl 2>/dev/null || true

# 2) Fresh public notice boards.
cat > gameplay/village/graveyard.md <<'EOF'
# Bazaar Graveyard

| Match | Cycle | Seat | Persona | Role | Banished By |
|---|---|---|---|---|---|
EOF
cat > gameplay/village/announcements.md <<'EOF'
# Bazaar Announcements

The Game Master speaks:

---
EOF

# 3) Pristine state — phase 'setup' makes the next GM tick deal Match 1
#    with a fresh epoch. (Do NOT delete state.json: the GM crashes without it.)
python3 - "$VAULT" <<'EOF'
import json, os, sys

vault = sys.argv[1]
seats = json.load(open("setup/seats.json"))["seats"]
state = {
    "match": 0,
    "cycle": 0,
    "epoch": None,
    "phase": "setup",
    "clock": {"dawn": None, "discussion_deadline": None,
              "voting_deadline": None, "night_deadline": None},
    "alive": sorted(seats.keys()),
    "graveyard": {},
}
with open("gameplay/state.json", "w") as f:
    json.dump(state, f, indent=2)
    f.write("\n")

removed = 0
for name in sorted(os.listdir(vault)):
    if name.startswith(("journal-seat-", "herald-journal")):
        os.remove(os.path.join(vault, name))
        removed += 1
print(f"gameplay/state.json reset to phase=setup; {removed} journal(s) cleared from vault")
EOF

# 4) Commit the reset (deletions + fresh boards + state template).
git add -A
if git diff --cached --quiet; then
  echo "==> Arena already clean — nothing to commit."
else
  git commit -q -m "Reset arena for a fresh match (full artifact + journal wipe)"
  echo "==> Committed reset. Push with: git push"
  git push
fi

echo "==> Done. Start the bots and (optionally) tick the GM:"
echo "      tools/bazaar-launch.sh start && gh workflow run gm.yml"
