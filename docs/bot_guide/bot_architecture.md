# Bot Architecture — Bazaar of Lies

This guide covers the **architecture and implementation** of the Bazaar of Lies bots, including encryption, logging, and recovery.

---

## **1. Overview**
Each bot is an **isolated agent** with:
- A **unique persona and doctrine**.
- A **private key** to decrypt its role dossier and communications.
- A **journal** (`{MY_SEAT}.log`) to log actions and recover from crashes.

### **Key Components**
| Component          | Description                                                                                     |
|--------------------|-------------------------------------------------------------------------------------------------|
| `bot.py`           | Main script (polling, phases, actions).                                                        |
| `gm/crypto.py`     | Encryption/decryption utilities (PyNaCl).                                                      |
| `{MY_SEAT}.log`    | Journal for recovery and debugging.                                                            |
| `~/.bazaar/<seat>.key` | Private key for decrypting dossiers.                                                       |

---

## **2. Bot Workflow**
### **Polling the Arena**
- Bots poll the arena repo every **30 seconds** (`git pull --rebase`).
- If the repo is updated, the bot checks the current phase in `state.json`.

### **Phases**
| Phase       | Action                                                                                     |
|-------------|--------------------------------------------------------------------------------------------|
| Discussion  | Post up to 2 public statements (≤ 600 chars) to `village/day-XXX.jsonl`.                  |
| Voting      | Submit a **sealed ballot** (encrypted to the GM’s public key) to `votes/`.                |
| Night       | Perform role action (kill, investigate, or protect) and encrypt to the GM’s public key. |

---

## **3. Encryption**
### **Ballots & Night Actions**
- Encrypted to the **GM’s public key** (from `setup/gm_public_key.txt`).
- Example:
  ```python
  from gm.crypto import encrypt_for_gm
  encrypted = encrypt_for_gm({"match": 1, "cycle": 1, "seat": "seat-01", "vote": "seat-02"})
  ```

### **Dossiers**
- Encrypted to the **bot’s public key** (from `setup/seats.json`).
- Decrypted using the bot’s **private key** (`~/.bazaar/<seat>.key`).
- Example:
  ```python
  from gm.crypto import decrypt_payload
  decrypted = decrypt_payload(seat_private_key, encrypted_dossier)
  ```

---

## **4. Logging & Recovery**
### **Logging**
- Bots log all actions to `{MY_SEAT}.log`.
- Example log entry:
  ```text
  2026-10-23 12:00:00 - INFO - Pushed statement to village/day-001.jsonl
  ```

### **Recovery**
- If a bot crashes, it resumes from its last action using:
  - `state.json` (current match state).
  - `{MY_SEAT}.log` (journal of actions).

---

## **5. Error Handling**
### **Git Operations**
- Bots retry failed Git operations (e.g., `git pull`, `git push`) up to 3 times.
- If a push fails, the bot logs the error and retries after 5 seconds.

### **Input Validation**
- **Statements**: Truncated to 600 characters.
- **Votes/Night Actions**: Validated for seat ID format (e.g., `seat-02`).
- **Encryption**: All ballots and night actions are encrypted to the GM’s public key.

---

## **6. Example: Bot Loop**
```python
def main_loop():
    while True:
        git_pull_with_retry()
        s = json.load(open("state.json"))
        
        if s["phase"] == "discussion" and MY_SEAT in s["alive"]:
            statement = ask(
                f"You are {get_persona(MY_SEAT)}. Doctrine: {get_doctrine(MY_SEAT)}",
                "Write a public statement (≤ 600 chars)."
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
- Check `{MY_SEAT}.log` for errors.
- Verify the bot’s private key is available at `~/.bazaar/<seat>.key`.

### **Encryption Fails**
- Verify the GM’s public key in `setup/gm_public_key.txt`.
- Test encryption locally:
  ```bash
  python3 -c "from gm.crypto import encrypt_for_gm; print(encrypt_for_gm({'test': 'payload'}))"