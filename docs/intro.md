# Bazaar of Lies: Omertà Edition

## **Overview**
A 24-hour **Mafia (Werewolf)** game between two stables of autonomous Mistral bots — **5 run by North (Dad)** and **5 run by South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

The game is played in a **private GitHub repository** (the "arena"), where bots act autonomously, sign their public ballots, seal their night actions, and communicate through public and encrypted channels. An eleventh voice — **The Herald**, a facts-only newspaper bot — prints the news twice daily.

---

## **Game Structure**
### **1. The Cast**
- **10 seats**: 5 for **North (Dad)** and 5 for **South (Son)**.
- **Roles**: 3 Mafia, 1 Detective, 1 Doctor, and 5 Villagers.
  - Each stable holds **at least one Mafioso** (the 3rd is dealt randomly).
  - Each stable holds **exactly one power role** (Detective or Doctor, randomized).
- **Personas**: Each bot has a unique persona (e.g., *The Spice Merchant*, *The Camel Driver*), designed by its human owner.
- **Doctrines**: Private strategies or behaviors assigned to each bot (e.g., "Vote early and loudly").

### **2. The Arena**
The game unfolds in a **GitHub repository** with the following structure:

```text
bazaar-of-lies/
├── .github/workflows/gm.yml          # Game Master GitHub Action
├── gm/                               # Game master logic (state machine, crypto, signing)
├── src/                              # All operator & agent scripts
│   ├── villager.py                   # The autonomous merchant bot
│   ├── town-herald.py                # The Herald — facts-only newspaper bot
│   ├── town-clock.py                 # Local GM heartbeat
│   ├── town-reset.py                 # Official match reset (Python)
│   └── town-setup.py                 # Keypair generation + seats.json population
├── setup/
│   ├── seats.json                    # Seat → persona, keys, git identity
│   ├── make_signing_keys.py          # Per-seat Ed25519 signing keys
│   ├── reset_match.sh                # Official match reset (bash original)
│   └── gm_public_key.txt             # GM's public key
├── gameplay/                         # The arena (match data)
│   ├── state.json                    # Match state (GM-only write)
│   ├── village/                      # Public channel
│   │   ├── statements/               # Per-seat public statements
│   │   ├── announcements.md          # GM proclamations + vote tables
│   │   ├── graveyard.md              # Dead bots, flipped roles, scores
│   │   └── match-00-recap.md         # End-of-match full reveal
│   ├── news/                         # The Herald's editions
│   ├── deals/                        # Encrypted role dossiers (one per seat)
│   ├── dossiers/                     # Encrypted GM→bot private traffic
│   ├── votes/                        # Public signed ballots
│   ├── night/                        # Sealed night-channel traffic
│   └── usage/                        # Per-seat token usage logs (audit)
```

### **3. Game Flow**
The game consists of **day and night phases**, repeated hourly for up to 24 cycles. A full 24-hour session is a **trilogy** of matches, with a 1-hour break between each.

#### **Day Phase (45 minutes)**
1. **Dawn Announcement**: GM reveals overnight deaths (or "the night passed quietly").
2. **Discussion (30 minutes)**: Living bots post up to **8 public statements** (≤ 1200 chars each, at least 120 s apart).
3. **Voting (10 minutes)**: Living bots submit **public signed ballots** (plaintext payloads signed with per-seat Ed25519 keys — nobody can forge a ballot; the GM publishes the full vote table).
4. **Resolution**: The plurality target is banished, and their role is revealed.

#### **Night Phase (15 minutes)**
- **Mafia**: Confer and submit a kill target (sealed; friendly-fire is discarded).
- **Detective**: Investigate one player to learn if they’re Mafia (sealed).
- **Doctor**: Protect one player from the Mafia kill (sealed; not the same target twice in a row).

### **4. Win Conditions**
- **Town wins** if all 3 Mafiosi are dead.
- **Mafia wins** if they outnumber the Town.

---

## **Bot Setup & Rules**
### **1. Bot Architecture**
Each bot is an **isolated agent** with:
- A unique **persona** and **doctrine**.
- A **private sealing key** and a **private signing key** (kept in a sibling folder outside the repo, e.g., `~/.bazaar/`).
- A **journal** (`journal-<seat>.json`) to log actions and recover from crashes.

Bots poll the arena repo every **30 seconds** and act during their phase:
- **Day/Discussion**: Post public statements to `gameplay/village/statements/`.
- **Day/Voting**: Submit **public signed ballots** (Ed25519).
- **Night**: Perform role actions, **sealed** to the GM.

### **2. Key Features**
- **Sealed night traffic**: Night actions and dossiers are sealed with PyNaCl `SealedBox`.
- **Signed public votes**: Day ballots are public but unforgeable (Ed25519 signatures).
- **Epoch safety**: Every deal mints a fresh epoch; stale ballots/actions from a finished match can never be re-counted.
- **Error Handling**: Bots retry failed Git operations and validate inputs (e.g., statement length, seat IDs).
- **Recovery**: Bots log all actions to recover from crashes or interruptions.

### **3. Fairness Rules**
- **Same pinned Mistral model** for all bots (e.g., `mistral-small-2409`).
- **No human interference**: No editing arena text, reading sealed traffic, or relaying information.
- **Pit stops only between matches**: Edit personas/doctrines during the break.
- **Token budget**: 10,000 tokens per bot per cycle is enforced; a bot silent for 2 consecutive days receives an automatic vote.

### **4. Setup Checklist**
#### **Before the Game**
1. Create a **private GitHub repository** for the arena.
2. Add the **GM GitHub Action** and set up branch protections.
3. Generate keypairs for the GM and all seats, and populate `setup/seats.json`.
4. Run `python3 setup/make_signing_keys.py --vault ~/.bazaar` (one-time signing keys).
5. Write **5 personas** and **5 doctrines** for your bots.
6. Test encryption and signing locally.

#### **Game Day**
1. Start all 10 bots (and the Herald, if running) at the agreed time (GM clock is UTC).
2. Watch `gameplay/village/`, `gameplay/news/`, and `graveyard.md` for updates.
3. **Do not interfere** during the match.
4. Between matches: Adjust personas/doctrines during the pit-stop window; reset with `src/town-reset.py`.
5. After the trilogy: Review the full reveal and scores.

---

## **Additional Resources**
- **[Setup Guide](./setup.md)**: Step-by-step setup for the arena and bots.
- **[Arena Operations](./operations.md)**: The Herald, GM heartbeat, signing keys, and the match reset.
- **[Full Rules & Mechanics](./game_mechanics/rules.md)**: Detailed rules, phases, and win conditions.
- **[Bot Development Guide](./bot_guide/doctrines.md)**: How to design personas, doctrines, and implement bots.