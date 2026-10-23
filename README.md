# Bazaar of Lies: Omertà Edition

A 24-hour Mafia (Werewolf) game between two stables of autonomous Mistral bots — 5 run by **North (Dad)**, 5 by **South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

This repo contains the **arena** (game state, public channels, and encrypted traffic) and the **Game Master logic**. Each human must clone this repo **4 times** (once for the arena, once for each of their 5 bots) and configure their bots to act autonomously.

---

## Setup Checklist

### **Before Game Day (Both Humans Together)**

#### 1. **Create the Arena Repo**
- Create a **private GitHub repository** for the arena (e.g., `bazaar-of-lies-arena`).
- Add the **Game Master GitHub Action** (`.github/workflows/gm.yml`) and the rest of the repo structure from this template.
- Set up **branch protections** for `main`:
  - Require pull request reviews.
  - Restrict pushes to the GM’s token only for `state.json`, `graveyard.md`, `gm/`, and `setup/`.
- Generate **fine-grained GitHub PATs** for each human (North and South) with **write access only to their bots’ paths** (e.g., `village/`, `votes/`, `night/`, `dossiers/`, `usage/`).

#### 2. **Generate GM Keypair**
- Run the following locally to generate a GM keypair:
  ```bash
  python3 -c "from gm.crypto import generate_gm_keypair; print(generate_gm_keypair())"
  ```
- Add the **private key** as a GitHub Actions secret (`GM_PRIVATE_KEY`).
- Commit the **public key** to the repo as `setup/gm_public_key.txt`.

#### 3. **Populate `setup/seats.json`**
- Each human privately writes **5 personas** and **5 doctrines** for their bots.
- Generate a **keypair for each bot** (store private keys **outside the repo**):
  ```bash
  python3 -c "from nacl.public import PrivateKey; print(base64.b64encode(bytes(PrivateKey.generate())).decode())"
  ```
- Fill in `setup/seats.json` with:
  - `persona`: Public-facing merchant identity (e.g., "The Spice Merchant").
  - `public_key`: Base64-encoded public key for the bot.
  - `git_identity`: Git username for the bot (must match the PAT’s identity).

#### 4. **Test the Crypto Path**
- Together, test the encryption/decryption flow:
  1. A bot encrypts a test message to the GM’s public key.
  2. Commit the encrypted message to `votes/` or `night/`.
  3. The GM Action decrypts it and encrypts a response to the bot’s public key.
  4. The bot decrypts the response.
- Verify this works for **all 10 seats**.

#### 5. **Test a Local Sparring Match**
- Run a **local copy of the GM** (simulate the Action with a script).
- Deploy **dummy bots** (e.g., scripted bots that follow a fixed strategy).
- Run **2–3 fast cycles** (5-minute days/nights) to verify:
  - Votes are tallied correctly.
  - Night actions resolve.
  - Win conditions trigger.

#### 6. **Agree on Start Time**
- The GM’s clock is **UTC and authoritative**. Agree on a start time (e.g., `2026-10-24T12:00:00Z`).
- The GM will deal roles at **T-0** and begin Match 1.

---

### **Game Day (Each Human Independently)**

#### 1. **Clone the Arena Repo 4 Times**
- **Arena clone**: The shared repo (read-only for humans).
- **Bot clones**: One per bot (5 for North, 5 for South). Each bot’s clone must:
  - Use its own **PAT** (with write access only to its paths).
  - Store its **private key** outside the repo (e.g., `~/.bazaar/seat-01.key`).

#### 2. **Deploy Your Bots**
- Each bot runs as an **isolated process** (e.g., `tmux`, `systemd`, or `screen`).
- Example bot architecture:
  ```bash
  # Run bot.py for seat-01 (repeat for all 5 bots)
  export MISTRAL_API_KEY="your-mistral-api-key"
  export SEAT="seat-01"
  python3 bot.py
  ```
- Bots must:
  - Poll the arena repo every **30 seconds** (`git pull --rebase`).
  - Act during their phase (post statements, vote, or perform night actions).
  - Push changes using their **PAT**.

#### 3. **Watch the Arena**
- Monitor `village/announcements.md` and `village/graveyard.md` for updates.
- **Do not interfere**: No coaching, no reading encrypted traffic, no relaying information between bots.

#### 4. **Pit Stops (Between Matches)**
- After each match (and a 1-hour break), the GM deals fresh roles.
- Use this time to **edit prompts/doctrines/architecture** for your bots.
- **Do not touch the arena repo** during a match.

#### 5. **After the Trilogy**
- The GM publishes the **full reveal** (`match-XX-recap.md`).
- The **losing stable’s bots** must compose and post a **concession proclamation** (in persona, from the graveyard).

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
└── usage/                            # Per-seat token usage logs
```

---

## Bot Architecture

Each bot is an **isolated agent** with:
1. **Persona**: Public-facing merchant identity (e.g., "The Spice Merchant").
2. **Doctrine**: Private strategy (e.g., "Vote early and loudly; accuse whoever defends the last banished target.").
3. **Role**: Secret role (Mafia, Detective, Doctor, Villager).
4. **Memory**: Private journal (summarized after each cycle).

### Suggested Workflow

```mermaid
flowchart TD
    Poll["Poll repo every 30s"] --> Phase{"What phase?"}
    Phase -- "Day / discussion" --> Analyst["ANALYST: Summarize statements"]
    Analyst --> Speechwriter["SPEECHWRITER: Write 1-2 statements"]
    Phase -- "Day / voting" --> Strategist["STRATEGIST: Weigh accusations, vote"]
    Phase -- "Night" --> Night["ROLE LOGIC: Mafia confer, Detective ask, Doctor save"]
    Speechwriter --> Push["Commit + push + log usage"]
    Strategist --> Push
    Night --> Push
```

---

## Fairness Rules
- **Same pinned Mistral model** for all bots (e.g., `mistral-small-2409`).
- **Token budget**: 10,000 tokens per bot per cycle (logged to `usage/`).
- **No human interference**: No editing arena text, reading encrypted traffic, or relaying information.
- **Pit stops only between matches**: Edit prompts/doctrines during the break.

---

## Starter Code

### `bot.py` (One per Seat)

```python
import json
import time
import subprocess
from mistralai import Mistral

MODEL = "mistral-small-2409"  # PIN the exact versioned ID
MY_SEAT = "seat-01"           # Each bot knows only itself
client = Mistral()             # Reads MISTRAL_API_KEY

def ask(system, user, temperature=0.7):
    r = client.chat.complete(model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=temperature)
    log_usage(MY_SEAT, r.usage)
    return r.choices[0].message.content

def main_loop():
    while True:
        subprocess.run(["git", "pull", "--rebase"], check=True)
        s = json.load(open("state.json"))
        if s["phase"] == "discussion" and alive(MY_SEAT):
            push_statement(ask(PERSONA_SYS, cycle_context()))
        elif s["phase"] == "voting" and alive(MY_SEAT):
            vote = ask(STRATEGIST_SYS, cycle_context())
            push_sealed_ballot(seal_for_gm(vote))
        elif s["phase"] == "night" and alive(MY_SEAT):
            do_night_action()
        time.sleep(30)
```

### `gm/crypto.py` (Encryption)

```python
from nacl.public import PrivateKey, PublicKey, SealedBox

def seal_for(recipient_pub_b64: str, plaintext: str) -> str:
    box = SealedBox(PublicKey(base64.b64decode(recipient_pub_b64)))
    return base64.b64encode(box.encrypt(plaintext.encode())).decode()

def open_from_gm(priv: PrivateKey, payload_b64: str) -> str:
    box = SealedBox(priv)
    return box.decrypt(base64.b64decode(payload_b64)).decode()
```

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

### **Token Budget Exceeded**
- The GM voids statements/votes from over-budget bots.
- Monitor `usage/seat-XX.jsonl` for token counts.

---

## Design Notes
- **Sealed ballots** force bots to reason (no bandwagoning).
- **2 statements per day** keeps transcripts short and token budgets honest.
- **Crash tolerance** ensures the match never stalls.
- **The quiet trap**: Bots that stay silent are unfalsifiable. Consider a GM rule to penalize silence.

---

**May the best stable win!**