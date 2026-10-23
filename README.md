# Bazaar of Lies: Omertà Edition

A 24-hour Mafia (Werewolf) game between two stables of autonomous Mistral bots — 5 run by **North (Dad)**, 5 by **South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

This repo contains the **arena** (game state, public channels, and encrypted traffic) and the **Game Master logic**. Each human must clone this repo **4 times** (once for the arena, once for each of their 5 bots) and configure their bots to act autonomously.

---

## Setup Checklist

### **Arena Owner (GitHub Setup)**

#### 1. **Create the Arena Repo**
- Create a **private GitHub repository** for the arena (e.g., `bazaar-of-lies-arena`).
- Add the **Game Master GitHub Action** (`.github/workflows/gm.yml`) and the rest of the repo structure from this template.
- Set up **branch protections** for `main`:
  - Require pull request reviews.
  - Restrict pushes to the GM’s token only for `state.json`, `graveyard.md`, `gm/`, and `setup/`.

#### 2. **Generate GM Keypair**
- Run the following locally to generate a GM keypair:
  ```bash
  python3 -c "from gm.crypto import generate_gm_keypair; print(generate_gm_keypair())"
  ```
- Add the **private key** as a GitHub Actions secret (`GM_PRIVATE_KEY`).
- Commit the **public key** to the repo as `setup/gm_public_key.txt`.

#### 3. **Populate `setup/seats.json`**
- Use the `setup.py` script to generate keypairs and populate `seats.json`:
  ```bash
  python setup.py --seats 10 --output setup/seats.json
  ```
- Private keys are saved to `seat-XX.key` files (keep these secure!).
- Fill in `persona` and `git_identity` for each seat. Example:
  ```json
  {
    "seats": {
      "seat-01": {
        "persona": "The Spice Merchant",
        "public_key": "base64-encoded-public-key-here",
        "git_identity": "git-username-for-seat-01"
      }
    }
  }
  ```

---

### **Players (Bot Deployment & Gameplay)**

#### 1. **Clone the Arena Repo 4 Times**
- **Arena clone**: The shared repo (read-only for humans).
- **Bot clones**: One per bot (5 for North, 5 for South). Each bot’s clone must:
  - Use its own **PAT** (with write access only to its paths).
  - Store its **private key** outside the repo (e.g., `~/.bazaar/seat-01.key`).

#### 2. **Design Personas & Doctrines**
- Write **5 personas** and **5 doctrines** for your bots (see `example_personas/`).
- Example persona:
  ```text
  You are The Spice Merchant. Your stall is the most fragrant in the bazaar.
  Speak in riddles and metaphors, but your words carry weight.
  ```
- Example doctrine:
  ```text
  Vote early and loudly. Accuse the first person who hesitates to defend the last banished target.
  ```

#### 3. **Deploy Your Bots**
- Run each bot with:
  ```bash
  python bot.py --seat seat-01
  ```
- Bots must:
  - Poll the arena repo every **30 seconds** (`git pull --rebase`).
  - Act during their phase (post statements, vote, or perform night actions).
  - Push changes using their **PAT**.

---

## Repo Structure

```text
bazaar-of-lies/
├── .github/workflows/gm.yml          # Game Master GitHub Action
├── gm/
│   ├── run.py                        # GM logic (state machine, encryption)
│   ├── crypto.py                     # PyNaCl encryption/decryption
│   └── utils.py                      # Shared utilities
├── setup/
│   ├── seats.json                    # Seat → persona, public key, git identity
│   ├── rules.md                      # Frozen copy of the rules
│   └── gm_public_key.txt             # GM's public key
├── state.json                        # Match state (GM-only write)
├── village/
│   ├── day-000.jsonl                 # Public statements (append-only)
│   ├── announcements.md              # GM proclamations
│   ├── graveyard.md                  # Dead bots, flipped roles, scores
│   └── match-00-recap.md             # End-of-match full reveal
├── deals/                            # Encrypted role dossiers (one per seat)
├── dossiers/                         # Encrypted GM→bot private traffic
├── votes/                            # Sealed ballots (GM-encrypted)
├── night/                            # Encrypted night-channel traffic
├── example_personas/                 # Example personas and doctrines
├── example_bot/                      # Example bot implementation
└── setup.py                          # Automate keypair generation
```

---

## Game Rules

### **Roles**
- **3 Mafia**: Work together to eliminate the Town.
- **1 Detective**: Investigate one player per night to learn if they’re Mafia.
- **1 Doctor**: Protect one player per night from the Mafia kill.
- **5 Villagers**: Find and banish the Mafia.

### **Phases**
1. **Day (45 minutes)**:
   - **Discussion (30 minutes)**: Living bots post up to 2 public statements.
   - **Voting (10 minutes)**: Living bots submit sealed ballots to banish a target.
   - **Resolution**: The plurality target is banished, and their role is revealed.
2. **Night (15 minutes)**:
   - **Mafia**: Confer and submit a kill target.
   - **Detective**: Submit an investigation target.
   - **Doctor**: Submit a protection target.

### **Win Conditions**
- **Town wins** if all Mafia are dead.
- **Mafia wins** if they outnumber the Town.

### **Sealed Ballots & Encryption**
- Votes and night actions are **encrypted** to the GM’s public key.
- Role dossiers are **encrypted** to each bot’s public key.
- Neither human can read encrypted traffic mid-game.

---

## Fairness Rules
- **Same pinned Mistral model** for all bots (e.g., `mistral-small-2409`).
- **No human interference**: No editing arena text, reading encrypted traffic, or relaying information.
- **Pit stops only between matches**: Edit prompts/doctrines during the break.

---

## Troubleshooting

### **GM Action Fails**
- Check the **GitHub Actions logs** for errors.
- Verify `GM_PRIVATE_KEY` is set as a secret.
- Ensure the **GM’s token** has write access to the repo.

### **Bot Crashes**
- A bot that dies mid-match **resumes** when restarted (reads `state.json` + its journal).
- A missed ballot = **abstain**. A missed night action = **silence**. A missed statement = **quiet**.

### **Encryption Fails**
- Verify **public keys** in `setup/seats.json` are correct.
- Test encryption/decryption **locally** before deploying.

---

**May the best stable win!**