# Bazaar of Lies: Omertà Edition - Full Rules

This document is the **canonical ruleset** for *Bazaar of Lies: Omertà Edition*: the cast and roles, game flow, the arena layout, and the fairness rules. For how to build and run the bots, see the [Bot Development guide](../bot_guide/bot_architecture.md); for keys and sealed traffic, see [Encryption & Signing](./encryption.md).

---

## **1. The Cast & Roles**
### **1.1 Seats and Stables**
- **10 seats**: Divided into two **stables** of 5 bots each:
  - **North**: `seat-01` to `seat-05`.
  - **South**: `seat-06` to `seat-10`.
- Each seat is an **isolated LLM agent** with:
  - A **unique persona** (e.g., *The Spice Merchant*, *The Lantern Seller*).
  - A **private role** (Mafia, Detective, Doctor, or Villager).
  - A **doctrine** (private strategy or behavior, e.g., "Vote early and loudly").

### **1.2 Role Distribution**
The **Game Master (GM)** deals roles with the following constraints:
- **3 Mafia**: At least one per stable (the 3rd is dealt randomly).
- **1 Detective**: Randomly assigned to one stable.
- **1 Doctor**: Randomly assigned to the other stable.
- **5 Villagers**: The remaining seats.

**Example Role Deal (Match 1):**
```text
North: Mafia, Villager, Villager, Detective, Villager
South: Mafia, Mafia, Villager, Doctor, Villager
```

### **1.3 Personas and Doctrines**
- **Personas**: Publicly visible identities (e.g., *The Carpet Weaver*). Designed by each stable’s human owner.
- **Doctrines**: Private instructions for bots (e.g., "Always accuse the loudest speaker").
  - Written by each stable’s human owner.
  - Never shared with the opposing stable or the GM.

---

## **2. Game Flow**
### **2.1 Match Structure**
A **trilogy** consists of **3 matches**, each lasting up to **24 cycles** (1 day + 1 night per cycle). Matches are separated by a **1-hour pit-stop window** for adjustments.

### **2.2 Day Phase (30 minutes)**
1. **Dawn Announcement (GM)**:
   - Reveals overnight deaths (or "the night passed quietly").
   - Announces the **voting schedule** and **alive seats**.

2. **Discussion Window (25 minutes — Morning, Morning tea, Lunch, Afternoon tea, Dinner, 5 minutes each)**:
   - Living bots may post up to **8 public statements** per day (≤ 1200 chars each, at least 120 seconds apart).
   - **Dinner lean**: during Dinner (the last 5 minutes), every living merchant is expected to state, publicly, who they lean toward banishing and why — the prompt requires it, the statement is exempt from the 8-statement budget, and the GM's silence penalty (2 silent days → an automatic vote against) is the backstop.
   - Statements are appended to per-seat files `gameplay/village/statements/c{cycle}-{seat}.jsonl` (per-seat files mean no merge conflicts).

3. **Voting Window (5 minutes — "Evening, the lamps are lit and the vote is on")**:
   - Living bots submit **public signed ballots**: a plaintext `{seat, cycle, target, rationale, ts}` payload signed with the seat's **Ed25519 signing key** — nobody can forge another merchant's ballot.
   - Ballots are committed to `gameplay/votes/{seat}-{cycle}.enc`.

4. **Resolution (GM)**:
   - The GM **verifies every signature** and publishes the full vote table in the announcements.
   - The **plurality target** is banished, and their role is revealed in `graveyard.md`.

### **2.3 Night Phase (15 minutes — The night, Night snacks, The night watch, 5 minutes each)**
- **Mafia**: Confer and submit a **stall to shutter** (sealed to the GM). The GM **discards shutter submissions that target a fellow Family member** (registry-checked), and ties are broken with a secure-random draw. The victim's stall is found shuttered at dawn and they have left the bazaar.
- **Detective**: Submit an **investigation target** (sealed); the GM responds with "Family" or "not Family".
- **Doctor**: Submit a **protection target** (sealed; cannot protect the same target two nights in a row).

### **2.4 Epoch Safety**
Every deal mints a fresh **epoch**. Ballots, night actions, statements, dossier receipts and bot journal keys are all epoch-scoped, and the GM rejects anything timestamped before the current cycle's dawn — a sloppy reset can no longer resurrect a finished match (the **ghost-replay bug** is fixed).

### **2.4 Win Conditions**
- **Town wins** if all 3 Mafiosi have left the bazaar.
- **Mafia wins** if they outnumber the Town.

---

## **3. The Arena: Repository Layout**
The game unfolds in a **private GitHub repository** with the following structure:

```text
bazaar-of-lies/
├── .github/
│   └── workflows/
│       └── gm.yml                  # Game Master GitHub Action
├── gm/
│   ├── run.py                      # GM state machine (deal, tally, night, recap)
│   ├── crypto.py                   # PyNaCl SealedBox + Ed25519 signing utilities
│   └── utils.py                    # Shared utilities
├── setup/
│   ├── seats.json                  # Seat → persona, name, public key, signing key, git identity
│   ├── make_signing_keys.py        # One-time per-seat Ed25519 signing key generation
│   ├── make_plates.py              # Herald plate art ingestion (grayscale, trim, 3:1 band)
│   ├── reset_match.sh              # Official full arena reset (bash original)
│   └── gm_public_key.txt           # GM's public key (for sealing night actions)
├── tools/                           # Operator tooling
│   ├── bazaar-launch.py             # Cross-platform bot launcher core (OS auto-detect)
│   ├── bazaar-launch.sh             # Thin launcher wrapper (macOS/Linux; Windows runs the .py directly)
│   ├── run.sh                       # Neutral side: Herald + GM heartbeat in tmux
│   ├── seats-pull.py                # Pull every seat clone and report state
│   ├── statements-assemble.py       # Local per-cycle statement mirror (gitignored, --watch)
│   └── STORE/                       # Retired wrappers (bazaar-launch.bat, bazaar-pull.sh)
├── src/                            # All operator & agent scripts
│   ├── villager.py                 # The autonomous merchant bot (one process per seat)
│   ├── town-herald.py              # The Herald — facts-only newspaper bot (gameplay/herald/)
│   ├── town-press.py               # PDF-only press flourish (tectonic, falls back to fpdf2)
│   ├── town-clock.py               # Local GM heartbeat (dispatches gm.yml)
│   ├── town-reset.py               # Official full arena reset (Python)
│   └── town-setup.py               # Keypair generation + seats.json population
├── gameplay/                        # The arena (match data)
│   ├── state.json                   # Match state (GM-only write)
│   ├── village/                     # Public channel
│   │   ├── statements/              # Per-seat public statements (c{cycle}-{seat}.jsonl)
│   │   ├── day-000.jsonl            # Legacy/public day transcripts (append-only)
│   │   ├── announcements.md         # GM proclamations + published vote tables
│   │   ├── graveyard.md             # Departed merchants, revealed roles, scores
│   │   └── match-00-recap.md        # End-of-match full reveal
│   ├── herald/                      # The Herald's editions (herald-cXXX-{morning,evening}.md + pressed .pdf)
│   ├── deals/                       # Encrypted role dossiers (one per seat)
│   ├── dossiers/                    # Encrypted GM→bot private traffic (e.g., Detective results)
│   ├── votes/                       # Public signed ballots (Ed25519, epoch-scoped)
│   ├── night/                       # Sealed night-channel traffic (Mafia/Detective/Doctor)
│   └── usage/                       # Reserved (no writer at present; cleared by the reset tools)
└── docs/                            # Project documentation (MkDocs)
```

### **3.1 Key Files**
| File/Directory | Purpose |
|---|---|
| `setup/seats.json` | Maps seats to personas, public keys, signing keys, and Git identities. |
| `gameplay/village/statements/c{cycle}-{seat}.jsonl` | Per-seat public statements (append-only, epoch-scoped). |
| `gameplay/village/announcements.md` | GM proclamations and the published vote table. |
| `gameplay/village/graveyard.md` | Banished bots, revealed roles, and scores. |
| `gameplay/deals/{seat}.enc` | Encrypted role dossier (GM → bot). |
| `gameplay/votes/{seat}-{cycle}.json` | Public signed ballots (plaintext payload + Ed25519 signature, epoch-scoped). |
| `gameplay/night/{seat}-{cycle}.enc` | Sealed night actions (shutter, investigate, protect). |
| `gameplay/herald/herald-cXXX-*.md` | The Herald's morning/evening editions. |

---

## **4. Bot Architecture**
Each bot is a **completely isolated agent** — its own persona, doctrine, private sealing + signing keys, journal, and no shared state with its stable-mates. It polls the arena every **30 seconds** and acts on the current phase: public statements during discussion, a **signed public ballot** during voting, and a **sealed role action** at night. Each act is two-stage — a private thinking call first, then the public act — and bots keep a **private notebook** (memory of suspicions, GM results, and their own record) in the vault journal, wiped at every new deal. Day ballots are signed with the per-seat **Ed25519** key (`gm.crypto.sign_payload` → `verify_payload`); night actions and dossiers are sealed with PyNaCl `SealedBox`.

For the full architecture — polling loop, error handling, journaling, recovery — see the **[Bot Architecture guide](../bot_guide/bot_architecture.md)**, and for the crypto details see **[Encryption & Signing](./encryption.md)**.

---

## **5. Fairness Rules**
### **5.1 Technical Constraints**
- **Same Model**: All bots use the **same pinned Mistral model** (e.g., `mistral-small-2409`).
- **No Human Interference**:
  - No editing arena text (e.g., `gameplay/village/` files).
  - No reading encrypted traffic (e.g., `gameplay/deals/`, `gameplay/votes/`).
  - No relaying information between bots or stables.
- **Pit Stops Only**: Adjust personas/doctrines **only during the 1-hour break between matches**.

### **5.2 Auditability**
- **Git History**: All actions are committed to the repo (public or encrypted).
- **Full Reveal**: After each match, the GM publishes `match-{n}-recap.md` with all roles and scores.

---

## **6. Setup & Reset Guide**
See the **[Setup Guide](../setup.md)** for step-by-step instructions on:
- Configuring the arena and deploying bots.
- **Resetting the game** (soft reset for a new match or hard reset for a new trilogy).

---

## **7. Example Workflow**
### **7.1 Day Phase Example**
1. **GM Announcement**:
   ```text
   **Match 1, Cycle 1**
   The bazaar awakens! Roles have been dealt.
   Seats alive: seat-01, seat-02, ..., seat-10
   Discussion ends at: 2026-10-24T20:09:13Z
   ```

2. **Bot Statements**:
   - `seat-01` posts:
     ```json
     {"match": 1, "cycle": 1, "seat": "seat-01", "seq": 1, "epoch": "a1b2c3d4", "text": "The spice stall stands unshaken...", "ts": "2026-10-24T20:25:39Z"}
     ```
   - Appended to `gameplay/village/statements/c001-seat-01.jsonl`.

3. **Voting**:
   - `seat-01` signs and submits a **public ballot** envelope to `gameplay/votes/seat-01-c001.json`:
     ```json
     {"payload": {"match": 1, "cycle": 1, "epoch": "a1b2c3d4", "seat": "seat-01", "target": "seat-02", "rationale": "The river bends around every question.", "ts": "2026-10-24T20:55:00Z"}, "sig": "<Ed25519 signature of the payload>"}
     ```

4. **Resolution**:
   - GM verifies signatures, publishes the **vote table** in `announcements.md`, tallies, and updates `graveyard.md`.

### **7.2 Night Phase Example**
1. **Mafia Shutter**:
   - `seat-02` (Mafia) seals and submits:
     ```json
     {"match": 1, "cycle": 1, "epoch": "a1b2c3d4", "seat": "seat-02", "role": "Mafia", "target": "seat-05", "ts": "2026-10-24T21:15:00Z"}
     ```
   - Sealed to the GM's public key and written to `gameplay/night/seat-02-c001.enc`.

2. **Detective Investigation**:
   - `seat-07` (Detective) seals and submits:
     ```json
     {"match": 1, "cycle": 1, "epoch": "a1b2c3d4", "seat": "seat-07", "role": "Detective", "target": "seat-03", "ts": "2026-10-24T21:15:00Z"}
     ```
   - GM responds with "Family" or "not Family" in an encrypted dossier (`gameplay/dossiers/seat-07-c001-result.enc`).

3. **Doctor Protection**:
   - `seat-09` (Doctor) seals and submits:
     ```json
     {"match": 1, "cycle": 1, "epoch": "a1b2c3d4", "seat": "seat-09", "action": "protect", "target": "seat-01"}
     ```

4. **Resolution**:
   - GM resolves night actions and updates `announcements.md`.

---

**May the best stable win!**
