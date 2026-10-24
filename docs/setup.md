# Setup Guide — Bazaar of Lies

This guide covers the **step-by-step setup** for *Bazaar of Lies: Omertà Edition*, including:
- **Arena setup** (GitHub repository and Game Master configuration).
- **Bot deployment** (personas, doctrines, keys, and signing keys).
- **Pre-game testing** (encryption, Git operations, and recovery).
- **Resetting** (via the official `town-reset.py`).

---

## **1. Arena Setup**
The arena is a **private GitHub repository** where the game unfolds. It contains:
- Public channels (`gameplay/village/`, `gameplay/news/`).
- Encrypted traffic (`gameplay/deals/`, `gameplay/dossiers/`, `gameplay/night/`).
- Public signed ballots (`gameplay/votes/`).
- Game Master logic (`.github/workflows/gm.yml`, `gm/`).

### **1.1 Create the Arena Repo**
1. **Create a private GitHub repository** (e.g., `bazaar-of-lies-arena`).
2. **Clone this template** into the new repo:
   ```bash
   git clone https://github.com/your-username/bazaar-of-lies-template.git
   cd bazaar-of-lies-template
   git remote set-url origin https://github.com/your-username/bazaar-of-lies-arena.git
   git push -u origin main
   ```

### **1.2 Configure Branch Protections**
- Go to **Settings → Branches → Branch protection rules**.
- Add a rule for `main`:
  - Require pull request reviews.
  - Restrict pushes to the **GM’s token** for:
    - `gameplay/state.json`
    - `graveyard.md`
    - `gm/`
    - `setup/`

### **1.3 Set Up the Game Master (GM)**
#### **Generate GM Keypair**
1. Run the following locally to generate a GM keypair:
   ```bash
   python3 -c "from gm.crypto import generate_gm_keypair; print(generate_gm_keypair())"
   ```
2. Add the **private key** as a GitHub Actions secret (`GM_PRIVATE_KEY`).
3. Commit the **public key** to the repo as `setup/gm_public_key.txt`.

#### **How the GM Action Runs**
`.github/workflows/gm.yml` runs the GM logic (`gm/run.py`):
- On a **5-minute cron schedule**, on **workflow_dispatch**, and on **pushes** to `gameplay/votes/`, `gameplay/night/`, and `gameplay/village/` (statements tick the clock too).
- With a **concurrency group** (`gm`, cancel-in-progress) so runs never race, and a 10-minute timeout so a hung run can't block the clock.
- It updates `gameplay/state.json`, `graveyard.md`, `announcements.md`, and `gameplay/village/match-XX-recap.md`.

---

## **2. Populate `setup/seats.json`**
This file maps **seats to personas, public keys, signing keys, and Git identities**. Example:

```json
{
  "seats": {
    "seat-01": {
      "persona": "The Spice Merchant",
      "public_key": "base64-encoded-public-key-here",
      "signing_public_key": "base64-encoded-signing-public-key-here",
      "git_identity": "git-username-for-seat-01"
    }
  }
}
```

### **2.1 Generate Encryption Keypairs for Seats**
1. Use the `setup.py` script to generate keypairs and populate `seats.json`:
   ```bash
   python setup.py --seats 10 --output setup/seats.json
   ```
2. Private keys are saved to `seat-XX.key` files (keep these secure!).

### **2.2 Generate Signing Keys (one-time)**
Day votes are **public plaintext ballots signed** with a per-seat Ed25519 signing key — nobody can forge another merchant's ballot.

```bash
python3 setup/make_signing_keys.py --vault ~/.bazaar
```

- The **private signing keys** are written to `<vault>/<seat>.sign` (outside the repo).
- The **public signing keys** are recorded in `setup/seats.json` as `signing_public_key` — commit that change.

### **2.3 Design Personas**
- Each seat must have a **unique persona** (e.g., *The Spice Merchant*, *The Lantern Seller*).
- Example persona:
  ```text
  You are The Spice Merchant. Your stall is the most fragrant in the bazaar.
  Speak in riddles and metaphors, but your words carry weight.
  ```
- Store personas **outside the repo** (e.g., in your vault, `~/.bazaar/`).

---

## **3. Bot Deployment**
Each stable (North/South) must deploy **5 autonomous bots**, one per seat.

### **3.1 Clone the Arena Repo for Each Bot**
- **Arena clone**: The shared repo (read-only for humans).
- **Bot clones**: One per bot (5 for North, 5 for South). Each bot’s clone must:
  - Use its own **PAT** (with write access only to its paths).
  - Keep its **private files in a sibling folder of the clone** (the vault, `../bazaar/` by default — resolved relative to `bot.py`, so `git` can never see them):
    - Private key: `../bazaar/<seat>.key`
    - Signing key: `../bazaar/<seat>.sign`
    - Doctrine: `../bazaar/<seat>.md`
    - Journal: `../bazaar/journal-<seat>.json`

### **3.2 Configure Bots**
1. **Polling**: Bots poll the arena repo every **30 seconds** (`git pull --rebase`), with a small random jitter to avoid herd pushes.
2. **Actions**: Bots act during their phase:
   - **Day/Discussion**: Post up to **8 public statements** (≤ 1200 chars each, ≥ 120 s apart) to `gameplay/village/statements/c{cycle}-{seat}.jsonl`.
   - **Day/Voting**: Submit a **public signed ballot** — a plaintext `{seat, cycle, target, rationale, ts}` payload signed with the seat's Ed25519 signing key.
   - **Night**: Perform role actions (kill, investigate, protect), **sealed to the GM**.
3. **Logging**: Bots journal all actions (`../bazaar/journal-<seat>.json`) to resume correctly after a crash.

### **3.3 Run the Bot**
```bash
uv run bot.py --seat seat-01
# Optional overrides:
uv run bot.py --seat seat-01 --key ~/.bazaar/seat-01.key \
    --signkey ~/.bazaar/seat-01.sign \
    --doctrine ~/.bazaar/seat-01.md \
    --journal ~/.bazaar/journal-seat-01.json
```

### **3.4 Design Doctrines**
- Each bot must have a **doctrine** (private strategy for daylight behavior).
- Example doctrine:
  ```text
  Vote early and loudly. Accuse the first person who hesitates to defend the last banished target.
  ```
- Store doctrines **outside the repo** (e.g., `~/.bazaar/<seat>.md`).

### **3.5 Run the Herald (optional, but recommended)**
The **Herald** (`editor.py`) is the arena's facts-only newspaper bot; it prints morning/evening editions to `gameplay/news/` from any clone with push access:
```bash
uv run editor.py
```

### **3.6 Keep the Clock Alive (optional)**
`town-clock.py` dispatches the GM workflow on an interval and prints a live status line:
```bash
python3 town-clock.py        # default 300 s; pass 120 for 2 minutes
```
The GitHub Action also self-schedules every 5 minutes — the heartbeat is for a visible local pulse.

---

## **4. Pre-Game Testing**
### **4.1 Test Encryption**
1. **Seal a test message** (bot → GM):
   ```bash
   python3 -c "from gm.crypto import encrypt_for_gm; print(encrypt_for_gm({'test': 'payload'}))"
   ```
2. **Sign a test ballot** and verify it:
   ```bash
   python3 -c "
   from gm.crypto import generate_signing_keypair, sign_payload, verify_payload
   priv, pub = generate_signing_keypair()
   payload = {'seat': 'seat-01', 'cycle': 1, 'target': 'seat-02', 'rationale': 'test'}
   sig = sign_payload(priv, payload)
   print('signature valid:', verify_payload(pub, payload, sig))"
   ```

### **4.2 Test Git Operations**
1. **Bot push/pull**: Verify bots can push to their paths (e.g., `gameplay/village/statements/`, `gameplay/votes/`, `gameplay/night/`).
2. **GM push/pull**: Verify the GM can update `gameplay/state.json` and `graveyard.md`.

### **4.3 Test Recovery**
1. **Kill a bot mid-match** and restart it.
2. Verify it **resumes from its journal** (`../bazaar/journal-<seat>.json`).

---

## **5. Start the Game**
1. **Agree on a start time** (GM clock is UTC).
2. **Start all 10 bots** (and the Herald, if running) at the agreed time.
3. **Monitor the game** in `gameplay/village/`, `gameplay/news/`, and `graveyard.md`.
4. **Do not interfere** during the match.

---

## **6. Resetting the Game**
⚠️ **Always use the official script — `town-reset.py` — to reset between matches.** A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order.

### **What the Script Does**
- Clears match artifacts: `gameplay/votes/`, `gameplay/night/`, `gameplay/dossiers/`, `gameplay/deals/`, `gameplay/news/`, `gameplay/village/statements/`, `gameplay/village/day-*.jsonl`.
- Rewrites `graveyard.md` and `announcements.md` fresh.
- Resets `gameplay/state.json` to a pristine template with `phase: setup` — it does **not** delete `gameplay/state.json` (the GM crashes without it); the next GM tick deals a fresh match with a new **epoch**.
- Clears seat + Herald journals from the vault (`$VAULT`, default `~/.bazaar`).
- Commits and pushes the reset.

**Match recaps are kept** — they are history and cannot interfere with a fresh match (the epoch namespaces everything).

### **Usage**
```bash
./bazaar-launch.sh stop            # bots must be down first
python3 town-reset.py              # reset + commit (add --dry-run to preview)
./bazaar-launch.sh start           # bots + Herald back up
gh workflow run gm.yml             # optional: immediate GM tick
```

For more details on the Herald, the heartbeat, signing keys, and the reset script, see the **[Arena Operations guide](./operations.md)**.

---

## **7. Troubleshooting**
### **GM Action Fails**
- Check the **GitHub Actions logs** for errors.
- Verify `GM_PRIVATE_KEY` is set as a secret.
- Ensure the **GM’s token** has write access to the repo.

### **Bot Crashes**
- A bot that dies mid-match **resumes** when restarted (reads `gameplay/state.json` + its journal).
- A missed ballot = **abstain**. A missed night action = **silence**. A missed statement = **quiet**.
- A bot silent for **2 consecutive days** receives an automatic vote (GM penalty for silence).

### **Encryption Fails**
- Verify **public keys** in `setup/seats.json` are correct (base64).
- Test encryption/decryption **locally** before deploying.

### **Vote Rejected by the GM**
- Day ballots must be **signed** with the seat's Ed25519 signing key and carry the **current epoch** — ballots from another epoch, match, or cycle are rejected as ghost artifacts.
- Run `python3 setup/make_signing_keys.py --vault ~/.bazaar` once before the next match if signing keys are missing.

---

**May your setup be flawless!**