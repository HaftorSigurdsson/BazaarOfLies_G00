# Arena Operations — Bazaar of Lies

This guide covers the **operational tooling** around the arena: the Herald newspaper bot, the GM heartbeat, signing keys, and the match reset script.

---

## **1. Tooling Overview**
| Tool | Location | Purpose |
|---|---|---|
| **Bot** | `src/villager.py` | The autonomous merchant (one process per seat). |
| **The Herald** | `src/town-herald.py` | Facts-only newspaper bot; prints morning/evening editions to `gameplay/herald/`. |
| **The Press** | `src/town-press.py` | Compiles each edition into a one-page A4 newspaper-front-page **PDF** for the humans. |
| **GM heartbeat** | `src/town-clock.py` | Locally dispatches the GM workflow on an interval and prints live status. |
| **Arena reset** | `src/town-reset.py` | One-command full arena reset in Python (artifacts + boards + state template + journals + `.gitkeep` repairs). |
| **Seat keypairs** | `src/town-setup.py` | Generates per-seat encryption keypairs and populates `setup/seats.json`. |
| **Signing keys** | `setup/make_signing_keys.py` | One-time generation of per-seat Ed25519 signing keys. |
| **Match reset (bash)** | `setup/reset_match.sh` | The original one-command full arena reset. |
| **Game Master** | `.github/workflows/gm.yml` + `gm/run.py` | Neutral referee (state machine, tallies, night resolution). |

---

## **2. The Herald (`src/town-herald.py`)**
An **eleventh voice** in the arena: the bazaar's only newspaper, printed twice daily. The Herald is **facts-only**:

- Sources are exclusively **public**: announcements, the graveyard, the current cycle's public statements, and the list of living seats.
- It **never speculates** about the roles of living merchants.
- It **never invents** statements, deaths, or events.
- Roles may only be restated from **official obituaries** (the GM reveals roles at death).
- Every edition carries a **"By the Numbers"** section (machine-counted public figures: seats alive/dead, per-seat statement counts, who is silent this cycle, the quiet-night streak, and per-seat vote participation once ballot tables exist) and, when the GM has published ballot tables, a **"The Voting Record"** section (the last two tallies, exactly as published — no editorialising).
- When public statements exist, the paper closes with a **"Letter to the Editor"**: one statement quoted verbatim, attributed to its seat, with at most a one-line neutral introduction.

### **Editions**
| Edition | Trigger | Villagers read it | Output |
|---|---|---|---|
| Morning | Phase becomes `discussion` | Over tea, when they wake — included in the discussion prompt | `gameplay/herald/herald-cXXX-morning.md` (+ `.pdf`) |
| Evening | Phase becomes `night` | By lamplight, before they sleep — included in the night prompt | `gameplay/herald/herald-cXXX-evening.md` (+ `.pdf`) |

Each edition is journal-guarded against double printing, and the villagers' own reading is the plain markdown (facts-only, public repo content).

### **The Press (PDF for the humans)**
After each edition is printed, `src/town-press.py` compiles it into a **one-page A4 PDF styled as an old newspaper front page**, committed next to the markdown as `herald-cXXX-{morning,evening}.pdf`.

- **LaTeX engine** (`tectonic` or `pdflatex`, checked in that order) produces the fine edition in the style of the classic newspaper template: Times-like type with hyphenation and microtype, a double-rule masthead and dateline, a bold headline, a **woodcut-style engraving plate** at the head of the first column, a **drop cap** on the opening paragraph, thin-ruled centred section heads, and two balanced columns with a hairline rule between them. If the edition is long, the type steps down (10pt → 8pt) until it fits **exactly one page**; an overlong edition prints at two pages rather than not at all.
- **fpdf2 fallback**: if no LaTeX engine is on `PATH`, a plainer pure-Python edition is pressed instead (the paper never fails to appear).
- **PDF-only flourish** (never enters the markdown the merchants read, so it cannot become game input): the engraving plate (`docs/assets/images/bazaar-engraving.png`, generated once from the bazaar banner; a missing plate never breaks a paper), plus two deterministic filler boxes at the foot of the page — **"The Weather & The Market"** and **"The Bazaar Whisper"** humour column — each picked per edition (match/cycle/part) so every paper differs but always re-presses the same.
- Install the engine once, e.g. the self-contained [tectonic](https://tectonic-typesetting.github.io/) binary in `~/.local/bin`, or TeX Live's `pdflatex`.

See a [sample pressed front page](./assets/herald-sample-morning.pdf) ([markdown source](./assets/herald-sample-morning.md)).

### **Run It**
Run from any clone of the arena repo with push access, in its own window:
```bash
uv run src/town-herald.py
# or with an explicit journal:
uv run src/town-herald.py --journal ~/.bazaar/herald-journal.json
```

---

## **3. GM Heartbeat (`src/town-clock.py`)**
A local heartbeat that **dispatches the GM workflow** (`gm.yml`) every interval and prints a live status line each tick:
- Dispatch result (skipped if a GM run is still in progress).
- Live **phase + cycle**, read from the repo via the GitHub API.
- Latest GM run status.

`Ctrl-C` stops it cleanly.

### **Run It**
```bash
python3 src/town-clock.py          # default: every 300 seconds
python3 src/town-clock.py 120      # custom interval, e.g. 2 minutes
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

## **5. Match Reset (`src/town-reset.py`)**
The **official way** to reset the arena between matches. A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order. Always use the script.

### **What It Does**
- Clears **match artifacts** (keeping the directories): `gameplay/votes/`, `gameplay/night/`, `gameplay/dossiers/`, `gameplay/deals/`, `gameplay/herald/`, `gameplay/usage/`, `gameplay/village/statements/`, `gameplay/village/day-*.jsonl`.
- Rewrites the public boards fresh: `graveyard.md`, `announcements.md`.
- Resets `gameplay/state.json` to a **pristine template** with `phase: setup` (⚠️ it does **not** delete `gameplay/state.json` — the GM crashes without it; the next GM tick deals Match 1 with a fresh epoch).
- Clears **local journals** (seat journals + Herald journal) from the vault (`$VAULT`, default `~/.bazaar`) — keys and signing keys are untouched.
- Repairs the arena's shape: every folder that is supposed to exist is recreated if missing and gets a **`.gitkeep`** if it doesn't have one.
- Commits the reset — **only after asking**: the script confirms before removing anything, before committing, and before pushing (`--push`).

**Match recaps (`gameplay/village/match-XX-recap.md`) are kept** — they are history and cannot interfere with a fresh match (the new epoch namespaces everything).

### **Usage**
```bash
./bazaar-launch.sh stop            # bots must be down first
python3 src/town-reset.py              # asks "Are you sure?" (y/n) before wiping
python3 src/town-reset.py --dry-run    # preview: show what would be wiped, touch nothing, no prompts
python3 src/town-reset.py --push       # after committing, asks before pushing
./bazaar-launch.sh start           # bots + Herald back up
gh workflow run gm.yml             # optional: immediate GM tick
```

The original bash version (`setup/reset_match.sh`) does the same wipe; `src/town-reset.py` adds the dry-run, the `.gitkeep` repairs, and a push-only-on-request commit.

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
