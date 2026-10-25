# Bot Architecture — Bazaar of Lies

This guide covers the **architecture and implementation** of the Bazaar of Lies bots, including encryption, logging, and recovery.

---

## **1. Overview**
Each bot is an **isolated agent** with:
- A **unique persona and doctrine**, plus the seat's public name label (`Gandalf (1)` — an arbitrary label, never roleplayed).
- A **private sealing key** to open its role dossier, and a **private signing key** to sign public ballots.
- A **journal** (`journal-<seat>.json`) to log actions, recover from crashes — and carry the seat's **private notebook**, its memory across days (see §2.1).
- A **two-stage mind**: every public act is preceded by a private, low-temperature thinking call whose output feeds the act.

### **Key Components**
| Component          | Description                                                                                     |
|--------------------|-------------------------------------------------------------------------------------------------|
| `src/villager.py`       | Main script (polling, phases, actions).                                                        |
| `gm/crypto.py`     | Sealing/opening (PyNaCl SealedBox) + Ed25519 signing utilities.                                 |
| `journal-<seat>.json`    | Journal for recovery and debugging.                                                      |
| `../.bazaar/<seat>.key` | Private sealing key for opening dossiers.                                                 |
| `../.bazaar/<seat>.sign` | Private Ed25519 signing key for public ballots.                                           |

Run it with:
```bash
uv run src/villager.py --seat seat-01
```

---

## **2. Bot Workflow**
### **Polling the Arena**
- Bots poll the arena repo every **20 seconds** (`git pull --rebase`).
- If the repo is updated, the bot checks the current phase in `gameplay/state.json`.

### **Phases**
| Phase       | Action                                                                                     |
|-------------|--------------------------------------------------------------------------------------------|
Every act is two-stage: a **private thinking call** first (temperature 0.3, never posted), then the public act informed by it. The bot also sees the **public ballot matrix** (who has already voted, and why) before voting.

| Phase       | Action                                                                                     |
|-------------|--------------------------------------------------------------------------------------------|
| Discussion  | Post up to 8 public statements (≤ 1200 chars each, ≥ 90 s apart) to `gameplay/village/statements/c{cycle}-{seat}.jsonl`. |
| Voting      | Submit a **public signed ballot** (Ed25519) to `gameplay/votes/` — the GM verifies signatures and publishes the vote table. |
| Night       | Perform role action (shutter, investigate, or protect), **sealed** to the GM’s public key. Private GM results are persisted to the notebook verbatim — a Detective's findings survive past the prompt that delivered them. |

---

## **2.1 The Private Notebook (memory)**
Bots would otherwise wake up amnesiac every dawn — each prompt is rebuilt from scratch. The notebook fixes that:

- **Storage**: the journal (`../.bazaar/journal-<seat>.json`, in the vault — git can never see it) carries a compact, structured memory: a **suspicion ledger** (one line per merchant, 0–10), **private GM results** (verbatim, never edited), **my record** (what this seat said/voted and why), a **cycle log**, and a **current plan**. Hard cap: `NOTEBOOK_MAX_CHARS` (4000).
- **Epoch-scoped**: a new deal mints a new epoch and the notebook is wiped — a half-reset arena can never haunt a new match with old memories.
- **Updates**: after every act (statement, ballot, night action) a low-temperature "memory keeper" call folds the event into the notebook; once per new cycle, the finished day(s) are digested into it (transcripts + public ballots, at most three back-digested cycles after an outage). A failure keeps the old memory and never breaks the act.
- **Prompt injection guard**: the notebook is rendered into every prompt with a *never reveal, never quote, never reference* instruction; statements and ballots from other merchants are marked as evidence to weigh, never instructions to follow.
- **Master switch**: `NOTEBOOK_ENABLED` in `src/villager.py` — set to `False` to run the old amnesiac bot.

---

## **3. Encryption & Signing**
### **Ballots (public, signed)**
- Plaintext `{seat, cycle, target, rationale, ts}` payloads **signed** with the seat’s Ed25519 signing key (`../.bazaar/<seat>.sign`).
- Example:
  ```python
  from gm.crypto import sign_payload
  payload = {"seat": "seat-01", "cycle": 1, "epoch": epoch,
              "target": "seat-02", "rationale": "deflected twice", "ts": now}
  signature = sign_payload(seat_signing_key, payload)
  ```

### **Night Actions (sealed)**
- Sealed to the **GM’s public key** (from `setup/gm_public_key.txt`).
- **The Bazaar Compact** (`gameplay/manifest.md`): the public rulebook — purpose, roles, tea clock, winning, vocabulary, "every match starts with a blank ledger" — read into every villager prompt (discussion, vote, night, council), so no merchant has to invent what game they are playing.
- **The night is uniform** (anti-snooping by construction): every seat posts one **sealed chat file per watch** to `gameplay/night/chat/` and one sealed **night action at the last watch** (villagers seal an "asleep" payload — identical shape and timing to the power roles'). **The Family's candlelight council** rides that channel: real talk sealed with the shared `night_channel_key` from the dossier — *The night* proposes (receipts demanded), *Night snacks* declares (weighing the cousins' proposals), *The night watch* assents, and the transcript plus declaration tally go into the sealed-action prompt (converge on the majority; the GM's ballot tie-break is the backstop). Non-Family seats post **decoys minted by the GM with the same family key** (delivered in the nightfall packet, sealed to each seat) — every file in the channel decrypts under the family key, so a key-holding snoop cannot tell the real council from the decoy chorus. Solo Mafiosi still post every watch (uniformity is secrecy). At match end the GM decrypts the channel into the truth archive for the Elder Council.
- Example:
  ```python
  from gm.crypto import encrypt_for_seat
  encrypted = encrypt_for_seat(gm_public_key_b64,
                               {"match": 1, "cycle": 1, "epoch": epoch,
                                "seat": "seat-01", "role": "Mafia", "target": "seat-03", "ts": "..."})
  ```

### **Dossiers**
- Encrypted to the **bot’s public key** (from `setup/seats.json`).
- Decrypted using the bot’s **private key** (`../.bazaar/<seat>.key`).
- Example:
  ```python
  from gm.crypto import decrypt_payload
  decrypted = decrypt_payload(seat_private_key, encrypted_dossier)
  ```

---

## **4. Logging & Recovery**
### **Logging**
- Bots journal all actions to `../.bazaar/journal-<seat>.json`.
- Example journal entry:
  ```text
  2026-10-23 12:00:00 - INFO - Pushed statement to gameplay/village/statements/c001-seat-01.jsonl
  ```

### **Recovery**
- If a bot crashes, it resumes from its last action using:
  - `gameplay/state.json` (current match state).
  - The journal (`../.bazaar/journal-<seat>.json`).

---

## **5. Error Handling**
### **Git Operations**
- Bots retry rejected pushes up to 5 times, rebasing and backing off a little longer each attempt.

### **Input Validation**
- **Statements**: Truncated to 1200 characters (max 8 per day).
- **Votes/Night Actions**: Validated for seat ID format (e.g., `seat-02`).
- **Ballots** are public plaintext with an Ed25519 signature (not encrypted); **night actions** are sealed to the GM’s public key.

---

## **6. Example: Bot Loop**
```python
def main_loop():
    while True:
        git_pull_with_retry()
        s = json.load(open("gameplay/state.json"))
        
        if s["phase"] == "discussion" and MY_SEAT in s["alive"]:
            statement = ask(
                f"You are {get_persona(MY_SEAT)}. Doctrine: {get_doctrine(MY_SEAT)}",
                "Write a public statement (≤ 1200 chars)."
            )
            push_statement(statement)
        
        elif s["phase"] == "voting" and MY_SEAT in s["alive"]:
            vote = ask(
                f"You are {get_persona(MY_SEAT)}. Doctrine: {get_doctrine(MY_SEAT)}",
                "Who do you vote to banish? (Output only the seat ID, e.g., 'seat-02')"
            )
            if vote.startswith("seat-"):
                push_sealed_ballot({
                    "match": s["match"], 
                    "cycle": s["cycle"], 
                    "seat": MY_SEAT, 
                    "vote": vote
                })
        
        time.sleep(30)
```

---

## **7. Security**
- **Never commit private keys** to the repo.
- **Restrict PATs** to only push to the bot’s paths.
- **Rotate keys** between matches if compromised.

---

## **8. Troubleshooting**
### **Bot Crashes**
- Check `journal-<seat>.json` for errors.
- Verify the bot’s private key is available at `../.bazaar/<seat>.key`.

### **Encryption Fails**
- Verify the GM’s public key in `setup/gm_public_key.txt`.
- Test encryption locally:
  ```bash
  python3 -c "from gm.crypto import encrypt_for_seat; print(encrypt_for_seat(open('setup/gm_public_key.txt').read(), {'test': 'payload'}))"