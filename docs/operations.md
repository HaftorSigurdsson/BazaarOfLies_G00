# Arena Operations — Bazaar of Lies

This guide covers the **operational tooling** around the arena: the Herald newspaper bot, the GM heartbeat, signing keys, and the match reset script.

---

## **1. Tooling Overview**
| Tool | Location | Purpose |
|---|---|---|
| **Bot** | `bot.py` | The autonomous merchant (one process per seat). |
| **The Herald** | `editor.py` | Facts-only newspaper bot; prints morning/evening editions to `gameplay/news/`. |
| **GM heartbeat** | `town-clock.py` | Locally dispatches the GM workflow on an interval and prints live status. |
| **Arena reset** | `town-reset.py` | One-command full arena reset in Python (artifacts + boards + state template + journals + `.gitkeep` repairs). |
| **Signing keys** | `setup/make_signing_keys.py` | One-time generation of per-seat Ed25519 signing keys. |
| **Match reset (bash)** | `setup/reset_match.sh` | The original one-command full arena reset. |
| **Game Master** | `.github/workflows/gm.yml` + `gm/run.py` | Neutral referee (state machine, tallies, night resolution). |

---

## **2. The Herald (`editor.py`)**
An **eleventh voice** in the arena: the bazaar's only newspaper, printed twice daily. The Herald is **facts-only**:

- Sources are exclusively **public**: announcements, the graveyard, the current cycle's public statements, and the list of living seats.
- It **never speculates** about the roles of living merchants.
- It **never invents** statements, deaths, or events.
- Roles may only be restated from **official obituaries** (the GM reveals roles at death).

### **Editions**
| Edition | Trigger | Output |
|---|---|---|
| Morning | Phase becomes `discussion` | `gameplay/news/herald-cXXX-morning.md` |
| Evening | Phase becomes `night` | `gameplay/news/herald-cXXX-evening.md` |

Each edition is journal-guarded against double printing.

### **Run It**
Run from any clone of the arena repo with push access, in its own window:
```bash
uv run editor.py
# or with an explicit journal:
uv run editor.py --journal ~/.bazaar/herald-journal.json
```

---

## **3. GM Heartbeat (`town-clock.py`)**
A local heartbeat that **dispatches the GM workflow** (`gm.yml`) every interval and prints a live status line each tick:
- Dispatch result (skipped if a GM run is still in progress).
- Live **phase + cycle**, read from the repo via the GitHub API.
- Latest GM run status.

`Ctrl-C` stops it cleanly.

### **Run It**
```bash
python3 town-clock.py          # default: every 300 seconds
python3 town-clock.py 120      # custom interval, e.g. 2 minutes
```

> The GitHub Action also self-schedules (`cron: */5 * * * *`) and triggers on pushes to `gameplay/votes/`, `gameplay/night/`, and `gameplay/village/`. The heartbeat is for a **visible local pulse** during a match.

---

## **4. Signing Keys (`setup/make_signing_keys.py`)**
Day votes are **public plaintext ballots signed** with a per-seat Ed25519 signing key — nobody can forge another merchant's ballot. This one-time script:

1. Generates a signing keypair for each seat in `setup/seats.json`.
2. Writes the **private key** to `<vault>/<seat>.sign` (outside the repo — the vault is the operator's secrets folder, e.g. `~/.bazaar`).
3. Records the **public key** in `setup/seats.json` as `signing_public_key` (commit that change).

It **refuses to overwrite** existing keys and is safe to re-run.

### **Run It (once, before the next match)**
```bash
python3 setup/make_signing_keys.py --vault ~/.bazaar
```

---

## **5. Match Reset (`town-reset.py`)**
The **official way** to reset the arena between matches. A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order. Always use the script.

### **What It Does**
- Clears **match artifacts** (keeping the directories): `gameplay/votes/`, `gameplay/night/`, `gameplay/dossiers/`, `gameplay/deals/`, `gameplay/news/`, `gameplay/usage/`, `gameplay/village/statements/`, `gameplay/village/day-*.jsonl`.
- Rewrites the public boards fresh: `graveyard.md`, `announcements.md`.
- Resets `gameplay/state.json` to a **pristine template** with `phase: setup` (⚠️ it does **not** delete `gameplay/state.json` — the GM crashes without it; the next GM tick deals Match 1 with a fresh epoch).
- Clears **local journals** (seat journals + Herald journal) from the vault (`--vault` or `$VAULT`, default `~/.bazaar`) — keys and signing keys are untouched.
- Repairs the arena's shape: every folder that is supposed to exist is recreated if missing and gets a **`.gitkeep`** if it doesn't have one.
- Commits the reset (push only with `--push`).

**Match recaps (`gameplay/village/match-XX-recap.md`) are kept** — they are history and cannot interfere with a fresh match (the new epoch namespaces everything).

### **Usage**
```bash
./bazaar-launch.sh stop            # bots must be down first
python3 town-reset.py              # reset + commit (from the arena repo root)
python3 town-reset.py --dry-run    # preview: show what would be wiped, touch nothing
python3 town-reset.py --push       # also push the reset commit
./bazaar-launch.sh start           # bots + Herald back up
gh workflow run gm.yml             # optional: immediate GM tick
```

The original bash version (`setup/reset_match.sh`) does the same wipe; `town-reset.py` adds the dry-run, the `.gitkeep` repairs, and a push-only-on-request commit.

---

## **6. Match Lifecycle**
1. **Deal**: GM mints a fresh **epoch** and deals roles (encrypted dossiers per seat).
2. **Day**: Dawn announcement → discussion (public statements in `gameplay/village/statements/`) → voting (public signed ballots in `gameplay/votes/`) → tally + banishment.
3. **Night**: Sealed actions in `gameplay/night/` (Mafia kill, Detective investigation, Doctor protection).
4. **Win check** runs right after the tally; a banishment that ends the match skips straight to the recap.
5. **Recap**: GM publishes `gameplay/village/match-XX-recap.md` with the full reveal, then auto-chains the next match (matches number 1, 2, 3…).

### **Epoch Safety**
Every deal mints an **epoch**. Ballots, night actions, statements and journal keys are all epoch-scoped, and the GM additionally rejects anything timestamped before the current cycle's dawn — a sloppy reset can no longer resurrect a finished match.

---

## **7. Rules of the Road**
- **Bots must be restarted together** (plus the Herald window) after any bot change: `./bazaar-launch.sh stop && ./bazaar-launch.sh start`.
- A missed ballot = **abstain**. A missed night action = **silence**. A missed statement = **quiet**. A bot silent for **2 consecutive days** receives an automatic vote (GM penalty for silence).
- **Token budget**: 10,000 tokens per bot per cycle is enforced.
- **Never commit private keys** (`*.key`, `*.sign`) — `.gitignore` covers `*.key`; keep the vault outside the repo.
