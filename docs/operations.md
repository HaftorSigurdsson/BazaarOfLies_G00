# Arena Operations — Bazaar of Lies

This guide covers the **operational tooling** around the arena: the Herald newspaper bot, the cron-driven Game Master, signing keys, the match reset script, and the Elder Council.

---

## **1. Tooling Overview**
| Tool | Location | Purpose |
|---|---|---|
| **Bot** | `src/villager.py` | The autonomous merchant (one process per seat): two-stage reasoning + a private notebook memory (epoch-scoped, vault-only). |
| **The Herald** | `src/town-herald.py` | Facts-only newspaper bot; prints morning/evening editions to `gameplay/herald/`. |
| **The Press** | `src/town-press.py` | Compiles each edition into a one-page A4 newspaper-front-page **PDF** for the humans. |
| **GM heartbeat (legacy)** | `src/town-clock.py` | Dispatches the GitHub-Action GM on an interval — the retired driver; kept for the Actions-hosted variant of the arena. |
| **Elder Council** | `src/elder-council.py` | Post-match historian-judge: compiles the full record (statements, ballots, graveyard, recap, truth archive, decrypted night actions and Detective results, the Family council) and writes a court-style judgment with per-seat verdicts and awards (`--dry-run` compiles evidence only). |
| **Elder press** | `src/elder-press.py` | Renders a judgment to a multi-page court-document PDF (tectonic). |
| **Arena reset** | `src/town-reset.py` | One-command full arena reset in Python (artifacts + boards + state template + journals + `.gitkeep` repairs). |
| **Seat keypairs** | `src/town-setup.py` | Generates per-seat encryption keypairs and populates `setup/seats.json`. |
| **Signing keys** | `setup/make_signing_keys.py` | One-time generation of per-seat Ed25519 signing keys. |
| **Plate ingestion** | `setup/make_plates.py` | Converts raw Herald plate art into uniform grayscale 3:1 plates. |
| **Bot launcher** | `tools/bazaar-launch.py` (+ `.sh` wrapper) | Cross-platform start/stop/status of all bots + the Herald (tmux on macOS/Linux, console windows on Windows — on Windows invoke the `.py` directly; the retired `.bat` wrapper lives in `tools/STORE/`). |
| **Neutral side (legacy)** | `tools/run.sh` | Runs the Herald + the old Actions-dispatching heartbeat on this clone in tmux — superseded by the launcher (Herald) + the cron (GM). |
| **Seat clone report** | `tools/seats-pull.py` | Pulls every seat clone and reports HEAD + dirty state (the retired `bazaar-pull.sh` wrapper lives in `tools/STORE/`). |
| **Statement mirror** | `tools/statements-assemble.py` | Assembles the per-seat statements of a cycle into ONE local transcript (`_assembled-cXXX.jsonl`, gitignored, always overwritten, never committed) — for monitoring (`--watch` keeps it fresh). Bots assemble the same view into their prompts themselves; the per-seat files remain the single source of truth. |
| **Match reset (bash)** | `setup/reset_match.sh` | The original one-command full arena reset. |
| **Game Master** | `gm/run.py` | The neutral referee (state machine, tallies, night resolution, recap + truth archive) — driven by the operator's own **cron**, once per 5 minutes, from a dedicated clone. The GitHub Action variant (`gm.yml`) still exists for a cloud-hosted arena. |

---

## **2. The Herald (`src/town-herald.py`)**
An **eleventh voice** in the arena: the bazaar's only newspaper, printed twice daily. The Herald is **facts-only**:

- **Display names**: every seat has a public name label (`Gandalf`, from `setup/seats.json`). **All prose — GM announcements, ballot tables, the graveyard, the Herald, the Council's judgments, and every merchant's speech — prints names alone**; seat numbers are bookkeeping and live only in machine files (ballots, dossiers, state, statement records) and the Council's appendices. The shared `gm.utils.seat_from_label` resolves a plain name back to a seat everywhere prose is parsed, and still reads the older `Gandalf (1)` labels of matches 1–2. The names are arbitrary pop-culture labels: the characters they evoke never enter the game, and bots are explicitly instructed never to roleplay them.

- Sources are exclusively **public**: announcements, the graveyard, the current cycle's public statements, and the list of living seats.
- It **never speculates** about the roles of living merchants.
- It **never invents** statements, deaths, or events.
- Roles may only be restated from **official obituaries** (the GM reveals roles at death).
- Every edition carries a **"By the Numbers"** section (machine-counted public figures: seats alive/departed, per-seat statement counts, who is silent this cycle, the quiet-night streak). **Ballot figures (per-seat vote participation, recent tallies) appear in evening editions only** — the morning paper reports the news, the evening paper carries the returns. Voice: a 19th-century town paper — confident, economical, dryly witty; still facts-only, never speculative.
- The **first morning of a match** is an introductory edition: the digest is marked `FIRST MORNING OF THE MATCH` and the paper welcomes the readers and introduces the merchants who have arrived (public facts only — names, no news invented).
- **Evening editions are the fuller paper** (5200 vs. 3600 characters): a "The Word on the Street" section with brief verbatim quotes from two or three of the day's statements, plus a few lines on what the day's discussion turned on.
- When public statements exist, the paper closes with a **"Letter to the Editor"**: one statement quoted verbatim, attributed by name, with at most a one-line neutral introduction.
- **The Tally** is computed by the Herald (never model-written) and appended to **evening editions only** — the morning paper reports the news, the evening paper carries the day's returns: an election-returns chart — solid bars per candidate, ballots and abstentions counted. The press re-renders it in the PDF as an old-style bar graph (ruled frame, small-caps caption, solid black bars), and the masthead carries the motto *"All the facts fit to print — the rumours you may trade elsewhere."*
- **Editorial continuity**: before writing, the Herald re-reads its own last two editions (public record) and may follow up on its own reporting in one brief line ("as we reported at dawn") — or state plainly when today's facts differ from yesterday's paper.
- **Editor's Note**: The Herald now includes a short editorial note summarizing the bazaar's mood each cycle, labeled as the **Editor's Note**. It provides thematic commentary without revealing private information or speculating about roles.
- **PERSONALS** (PDF-only classifieds, never game input): two in-theme ads per edition from a deterministic pool — lost keys, wanted apprentices, slightly singed rugs.
- **The tea clock**: every merchant prompt carries the current in-theme region of the day — *Morning, Morning tea, Lunch, Afternoon tea, Dinner* (the five 5-minute regions of a 25-minute discussion), then *Evening* for the 5-minute vote, and at night the three 5-minute watches (*The night, Night snacks, The night watch*) — computed from the arena clock by `gm.utils.day_region`. The Herald states the time of print in its digest ("printed at Morning tea"). See [The Bazaar — Setting & Tone](./game_mechanics/the_bazaar.md).

### **New Features**

- **Anonymous Statements**: On a random cycle (2–4), all statements are published without seat IDs. Labeled as "Anonymous Merchant" in the Herald to preserve strategic ambiguity while keeping votes public.
- **Last Words**: Banished merchants (non-Family) may leave a final statement, published in the next morning edition under "Last Words". Family members are excluded to avoid metagaming.
- **Historian Role**: A randomly assigned Villager writes a cycle summary for the Herald, published in evening editions under "The Historian's Chronicle". Adds narrative depth without unbalancing core roles.
- **First Morning Edition**: Introduces the merchants and sets the scene for new matches, providing context for readers.

### **Editions**
| Edition | Trigger | Villagers read it | Output |
|---|---|---|---|
| Morning | Phase becomes `discussion` | Over tea, when they wake — included in the discussion prompt | `gameplay/herald/herald-vol<VV>-cXXX-morning.md` |
| Evening | Phase becomes `night` | By lamplight, before they sleep — included in the night prompt | `gameplay/herald/herald-vol<VV>-cXXX-evening.md` |

Each edition is journal-guarded against double printing, and the villagers' own reading is the plain markdown (facts-only, public repo content).

### **The Press (PDF for the humans)**
After each edition is printed, `src/town-press.py` compiles it into a **one-page A4 PDF styled as an old newspaper front page**, shelved in **`gameplay/library/`** as `herald-vol<VV>-cXXX-{morning,evening}.pdf` — the current match's human reading copies (the library is emptied by each reset; copy PDFs out to keep them). The markdown stays beside the bots; the volume rises forever (kept in the vault at `../.bazaar/herald-vol.txt`, surviving resets), and the masthead carries **Vol. N — No. M** with the true volume.

- **LaTeX engine** (`tectonic` or `pdflatex`, checked in that order) produces the fine edition in the style of the classic newspaper template: Times-like type with hyphenation and microtype, a double-rule masthead and dateline, a bold headline, a **woodcut-style engraving plate** at the head of the first column, a **drop cap** on the opening paragraph, thin-ruled centred section heads, and two balanced columns with a hairline rule between them. If the edition is long, the type steps down (10pt → 8pt) until it fits **exactly one page**; an overlong edition prints at two pages rather than not at all.
- **fpdf2 fallback**: if no LaTeX engine is on `PATH`, a plainer pure-Python edition is pressed instead (the paper never fails to appear).
- **PDF-only flourish** (never enters the markdown the merchants read, so it cannot become game input): a **content-keyed woodcut plate** at the head of the first column — chosen from the motif pool in `docs/assets/plates/` by keyword-matching the edition's own text (stall shuttered → sunset-over-stalls, quiet night → moon, banishment → scales/urn/tombstones, persona motifs, with sunrise/sunset as edition defaults and the static engraving as the final fallback; art ingested by `setup/make_plates.py`) — plus two deterministic filler boxes at the foot of the page: **"The Weather & The Market"** and **"The Bazaar Whisper"** humour column.
- Install the engine once, e.g. the self-contained [tectonic](https://tectonic-typesetting.github.io/) binary in `~/.local/bin`, or TeX Live's `pdflatex`.

See a [sample pressed front page](./assets/herald-sample-morning.pdf) ([markdown source](./assets/herald-sample-morning.md)).

### **Run It**
Run from any clone of the arena repo with push access, in its own window:
```bash
uv run src/town-herald.py
# or with an explicit journal:
uv run src/town-herald.py --journal ../.bazaar/herald-journal.json
```

---

## **3. The Game Master (cron-driven)**
The GM (`gm/run.py`) is the neutral referee — the phase machine (deal → discussion → voting → night), the tally, the night resolution, the recap, and (since 2.9.0) the post-match truth archive. In the current architecture it runs **locally, driven by the operator's own cron**, once every 5 minutes from a **dedicated clone** (e.g. `~/Desktop/Game/game_master/`):

```bash
# one-time: a dedicated GM clone + its identity
git clone <arena-url> ~/Desktop/Game/game_master
cd ~/Desktop/Game/game_master && git config user.name "Game Master" \
    && git config user.email "gm@bazaar.local" && uv sync

# the crontab line (one tick every 5 minutes, flock-guarded against overlap)
*/5 * * * * flock -n /path/to/game_master/.gm-lock bash -lc \
  "cd /path/to/game_master && GM_PRIVATE_KEY=\"$(cat ../.bazaar/gm_private_key.txt)\" \
   [BAZAAR_MATCH_LIMIT=N] uv run python gm/run.py >> gm-cron.log 2>&1"
```

- **The GM pulls before acting** — a cron clone never runs on stale state.
- **`BAZAAR_MATCH_LIMIT`** (optional): park the arena instead of auto-chaining into the next match. When the match number passes the limit, the GM refuses to deal, sets `phase: halted`, and announces that the bazaar rests — every bot idles, nothing starts without an operator. Unset = unlimited chaining (the default).
- **`gm-cron.log`** is the GM's diary: one block per tick (`phase=discussion → waiting until …`, tallies, night resolutions, the halt).
- **A manual tick** works anytime: `cd game_master && GM_PRIVATE_KEY=$(cat ../.bazaar/gm_private_key.txt) uv run python gm/run.py`.

> **Legacy drivers**: the GitHub Action (`gm.yml`, self-scheduled every 5 minutes and on pushes to `votes/`, `night/`, `village/`) still exists for a cloud-hosted arena — its `GM_PRIVATE_KEY` comes from the repo secret. `src/town-clock.py` (a local heartbeat that *dispatches* that Action) is the retired middle piece of the Actions setup. Pick exactly **one** GM driver; the local cron is the current default.

---

## **4. Signing Keys (`setup/make_signing_keys.py`)**
Day votes are **public plaintext ballots signed** with a per-seat Ed25519 signing key — nobody can forge another merchant's ballot. This one-time script:

1. Generates a signing keypair for each seat in `setup/seats.json`.
2. Writes the **private key** to `<vault>/<seat>.sign` (outside the repo — the vault is the operator's secrets folder, e.g. `../.bazaar`).
3. Records the **public key** in `setup/seats.json` as `signing_public_key` (commit that change).

It **refuses to overwrite** existing keys and is safe to re-run.

### **Run It (once, before the next match)**
```bash
python3 setup/make_signing_keys.py --vault ../.bazaar
```

---

## **5. Match Reset (`src/town-reset.py`)**
The **official way** to reset the arena between matches. A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order. Always use the script.

### **What It Does**
- Clears **match artifacts** (keeping the directories): `gameplay/votes/`, `gameplay/night/`, `gameplay/dossiers/`, `gameplay/deals/`, `gameplay/herald/`, `gameplay/village/statements/`, `gameplay/village/day-*.jsonl`.
- Rewrites the public boards fresh: `graveyard.md`, `announcements.md`.
- Resets `gameplay/state.json` to a **pristine template** with `phase: setup` (⚠️ it does **not** delete `gameplay/state.json` — the GM crashes without it; the next GM tick deals the match with a fresh epoch). By default the match counter restarts at 0 (next deal = Match 1); with **`--keep-match`** the counter the GM already bumped at the last `end_match` is preserved, so a **mid-chain reset deals the *next* match** (Match 2 after Match 1) instead of renumbering over the previous match's recap, judgment, and truth archive. Never renumber mid-chain by hand.
- Clears **local journals** (seat journals + Herald journal) from the vault (`$VAULT`, else the sibling vault `../.bazaar` the bots use, else `~/.bazaar`) — keys and signing keys are untouched.
- Repairs the arena's shape: every folder that is supposed to exist is recreated if missing and gets a **`.gitkeep`** if it doesn't have one.
- Commits the reset — **only after asking**: the script confirms before removing anything, before committing, and before pushing (`--push`).

**Match recaps (`gameplay/village/match-XX-recap.md`) are kept by default** — they are history and cannot interfere with a fresh match (the new epoch namespaces everything). Pass `--wipe-recaps` to remove them too.

### **Usage**
```bash
tools/bazaar-launch.sh stop        # bots must be down first
python3 src/town-reset.py              # asks "Are you sure?" (y/n) before wiping
python3 src/town-reset.py --dry-run    # preview: show what would be wiped, touch nothing, no prompts
python3 src/town-reset.py --push       # after committing, asks before pushing
python3 src/town-reset.py --wipe-recaps  # also remove match-XX-recap.md history
python3 src/town-reset.py --keep-match  # mid-chain reset: deal the NEXT match, don't renumber
tools/bazaar-launch.sh start       # bots + Herald back up (Windows: python3 tools/bazaar-launch.py start)
# the cron GM ticks within 5 minutes; for an immediate tick:
cd ../game_master && GM_PRIVATE_KEY="$(cat ../.bazaar/gm_private_key.txt)" uv run python gm/run.py
```

The original bash version (`setup/reset_match.sh`) does the same wipe; `src/town-reset.py` adds the dry-run, the `.gitkeep` repairs, and a push-only-on-request commit.

---

## **6. Match Lifecycle**
1. **Deal**: GM mints a fresh **epoch** and deals roles (encrypted dossiers per seat). A **Historian** is randomly assigned from the Villagers.
2. **Day** (25 + 5 minutes): Dawn announcement → discussion across the five tea-clock regions (public statements in `gameplay/village/statements/`; **Dinner is the reckoning** — every merchant must state their lean, budget-exempt) → the **Evening** vote (public signed ballots in `gameplay/votes/`) → tally + banishment.
   - **Anonymous Statements**: On a random cycle (2–4), all statements are published without seat IDs (labeled "Anonymous Merchant" in the Herald).
   - **Last Words**: Banished merchants (non-Family) may leave a final statement, published in the next morning edition under "Last Words".
3. **Night** (15 minutes, the three watches) — **uniform by construction**: every living seat posts one sealed **chat file per watch** (`gameplay/night/chat/cCCC-wN-seat-XX.enc`, fixed-size symmetric ciphertext) and submits exactly one sealed **night action at the last watch** (`night/seat-XX-cCCC.enc`, villagers included — a sealed "asleep" payload). The Family's chat is real council talk sealed with the shared `night_channel_key`; everyone else posts **GM-minted decoys — ciphertexts sealed with the same family key**, decrypting to plausible council lines. Every file in the channel opens under the family key, so even a key-holding snoop sees ten council voices and cannot tell which are the Family. The GM publishes a **night packet** to every seat at nightfall (the decoys) and a **result file** to every seat at dawn (only the Detective's is real) — the night tree reveals nothing about roles, targets, or who talks to whom. The council's rhythm: *The night* is the proposal (receipts from the day's record), *Night snacks* the declaration, *The night watch* the assent and the sealed shutter. At match end the whole channel is decrypted into the truth archive for the Elder Council.
4. **Win check** runs right after the tally; a banishment that ends the match skips straight to the recap.
5. **Recap + truth archive**: GM publishes `gameplay/village/match-XX-recap.md` with the full reveal **and `match-XX-truth.md`** (the decrypted registry and every sealed night action — written before the next deal can overwrite them), then auto-chains the next match — **unless `BAZAAR_MATCH_LIMIT` parks the arena** (`phase: halted`).
6. **The Elder Council** (post-match, manual): `src/elder-council.py --match N` compiles the complete record and writes the court-style judgment (`match-XX-judgment.md` + the shelved PDF in `gameplay/library/`) — history with the nights narrated, per-seat verdicts with merit ratings, the awards, and the appendices.

### **Herald Editions**
- **First Morning Edition**: Introduces the merchants and sets the scene for new matches.
- **Morning Edition**: Reports overnight events and today's plan. Includes "Last Words" from banished merchants (if any) and the **Editor's Note** (thematic commentary).
- **Evening Edition**: Reports the day's banishment and vote tallies. Includes "The Historian's Chronicle" (cycle summary) and the **Editor's Note**.

### **Epoch Safety**
Every deal mints an **epoch**. Ballots, night actions, statements and journal keys are all epoch-scoped, and the GM additionally rejects anything timestamped before the current cycle's dawn — a sloppy reset can no longer resurrect a finished match.

---

## **7. Rules of the Road**
- **Bots must be restarted together** (plus the Herald window) after any bot change: `tools/bazaar-launch.sh stop && tools/bazaar-launch.sh start` (the launcher is cross-platform Python — `tools/bazaar-launch.py` — which starts the Herald window too; on Windows invoke the `.py` directly).
- A missed ballot = **abstain**. A missed night action = **silence**. A missed statement = **quiet**. A bot silent for **2 consecutive days** receives an automatic vote (GM penalty for silence).
- **Token spend** is watched on the Mistral console, not enforced in code (the historical "10,000 tokens per bot per cycle" figure was aspirational) — at the current pace a 45-minute cycle costs well under a unit of currency, and a full 24-cycle match lands in single digits. The Elder Council runs on mistral-large once per match.
- **Never commit private keys** (`*.key`, `*.sign`) — `.gitignore` covers `*.key`; keep the vault outside the repo (`../.bazaar`, holding seat keys, signing keys, the GM private key, journals, and the Herald's volume counter — the Family's council channel now lives in the repo itself, sealed and decoy-padded).
- **Never hand-edit `gameplay/`** — it is live game state written by bots and the GM; resets go through `src/town-reset.py`. The **library** (`gameplay/library/`) holds the pressed PDFs of the *current* match only: it is emptied by each reset together with the other artifacts — copy its PDFs out first if you want to keep a match's reading copies (the recaps and judgments in markdown survive as the permanent record).
