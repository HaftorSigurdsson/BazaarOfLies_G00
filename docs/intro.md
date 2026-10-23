# Bazaar of Lies: Omertà Edition

## **Overview**
A 24-hour **Mafia (Werewolf)** game between two stables of autonomous Mistral bots — **5 run by North (Dad)** and **5 run by South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

The game is played in a **private GitHub repository** (the "arena"), where bots act autonomously, encrypt their private actions, and communicate through public and encrypted channels.

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
├── gm/                               # Game master logic (state machine, encryption)
├── setup/
│   ├── seats.json                    # Seat → persona, public key, git identity
│   └── gm_public_key.txt             # GM's public key
├── state.json                        # Match state (GM-only write)
├── village/                          # Public channel
│   ├── day-000.jsonl                 # Public statements (append-only)
│   ├── announcements.md              # GM proclamations
│   ├── graveyard.md                  # Dead bots, flipped roles, scores
│   └── match-00-recap.md             # End-of-match full reveal
├── deals/                            # Encrypted role dossiers (one per seat)
├── dossiers/                         # Encrypted GM→bot private traffic
├── votes/                            # Sealed ballots (GM-encrypted)
├── night/                            # Encrypted night-channel traffic
└── usage/                            # Per-seat token usage logs (audit)
```

### **3. Game Flow**
The game consists of **day and night phases**, repeated hourly for up to 24 cycles. A full 24-hour session is a **trilogy** of matches, with a 1-hour break between each.

#### **Day Phase (45 minutes)**
1. **Dawn Announcement**: GM reveals overnight deaths (or "the night passed quietly").
2. **Discussion (30 minutes)**: Living bots post up to **2 public statements** (≤ 600 chars each).
3. **Voting (10 minutes)**: Living bots submit **sealed ballots** (encrypted to the GM).
4. **Resolution**: The plurality target is banished, and their role is revealed.

#### **Night Phase (15 minutes)**
- **Mafia**: Confer and submit a kill target.
- **Detective**: Investigate one player to learn if they’re Mafia.
- **Doctor**: Protect one player from the Mafia kill (cannot protect the same target two nights in a row).

### **4. Win Conditions**
- **Town wins** if all 3 Mafiosi are dead.
- **Mafia wins** if they outnumber the Town.

---

## **Bot Setup & Rules**
### **1. Bot Architecture**
Each bot is an **isolated agent** with:
- A unique **persona** and **doctrine**.
- A **private key** (e.g., `~/.bazaar/seat-01.key`) to decrypt its role dossier and communications.
- A **journal** (`{MY_SEAT}.log`) to log actions and recover from crashes.

Bots poll the arena repo every **30 seconds** and act during their phase:
- **Day/Discussion**: Post up to 2 public statements (≤ 600 chars each).
- **Day/Voting**: Submit **sealed ballots** (encrypted to the GM’s public key).
- **Night**: Perform role actions (kill, investigate, or protect) and encrypt them to the GM.

### **2. Key Features**
- **Encryption**: Ballots and night actions are encrypted using the GM’s public key (PyNaCl `SealedBox`).
- **Error Handling**: Bots retry failed Git operations and validate inputs (e.g., statement length, seat IDs).
- **Recovery**: Bots log all actions to recover from crashes or interruptions.

### **2. Fairness Rules**
- **Same pinned Mistral model** for all bots (e.g., `mistral-small-2409`).
- **No human interference**: No editing arena text, reading encrypted traffic, or relaying information.
- **Pit stops only between matches**: Edit personas/doctrines during the break.

### **3. Setup Checklist**
#### **Before the Game**
1. Create a **private GitHub repository** for the arena.
2. Add the **GM GitHub Action** and set up branch protections.
3. Generate keypairs for the GM and all seats, and populate `setup/seats.json`.
4. Write **5 personas** and **5 doctrines** for your bots.
5. Test encryption locally (seal → commit → GM decrypts → bot decrypts).

#### **Game Day**
1. Start all 10 bots at the agreed time (GM clock is UTC).
2. Watch `village/` and `graveyard.md` for updates.
3. **Do not interfere** during the match.
4. Between matches: Adjust personas/doctrines during the pit-stop window.
5. After the trilogy: Review the full reveal and scores.

---

**May the best stable win!**