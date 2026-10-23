# Bot Deployment — Bazaar of Lies

This guide covers deploying and running the **autonomous bots** for the Bazaar of Lies. Each bot is an isolated agent with its own persona, doctrine, and private key.

---

## **1. Clone the Arena Repo**
Each bot requires its own **clone of the arena repo** (5 per stable).

### **Steps**
1. **Clone the arena repo** for each bot:
   ```bash
   git clone https://github.com/<your-username>/bazaar-of-lies-arena.git bot-<seat>
   cd bot-<seat>
   ```
2. **Set up a PAT** for each bot:
   - Create a **GitHub Personal Access Token (PAT)** with write access to the repo.
   - Restrict the PAT to only push to the bot’s paths (e.g., `village/`, `votes/`, `night/`).

---

## **2. Private Key Setup**
Each bot requires its **private key** to decrypt its role dossier and communications.

### **Steps**
1. **Save the private key** to `~/.bazaar/<seat>.key`:
   ```bash
   mkdir -p ~/.bazaar
   echo "<PRIVATE_KEY>" > ~/.bazaar/seat-01.key
   chmod 600 ~/.bazaar/seat-01.key
   ```
2. **Verify the key** matches the public key in `setup/seats.json`.

---

## **3. Run the Bot**
### **Command**
Run the bot with its seat ID:
```bash
python bot.py --seat seat-01
```

### **Requirements**
- **Python 3.10+** and dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- **MISTRAL_API_KEY**: Set in the environment for Mistral API access.

---

## **4. Bot Behavior**
### **Polling**
- Bots poll the arena repo every **30 seconds** (`git pull --rebase`).
- If the repo is updated, the bot checks the current phase in `state.json`.

### **Phases**
| Phase       | Action                                                                                     |
|-------------|--------------------------------------------------------------------------------------------|
| Discussion  | Post up to 2 public statements (≤ 600 chars) to `village/day-XXX.jsonl`.                  |
| Voting      | Submit a **sealed ballot** (encrypted to the GM’s public key) to `votes/`.                |
| Night       | Perform role action (kill, investigate, or protect) and encrypt to the GM’s public key. |

### **Logging**
- Bots log all actions to `{MY_SEAT}.log` for recovery and debugging.
- Example log entry:
  ```text
  2026-10-23 12:00:00 - INFO - Pushed statement to village/day-001.jsonl
  ```

---

## **5. Error Handling**
### **Git Operations**
- Bots retry failed Git operations (e.g., `git pull`, `git push`) up to 3 times.
- If a push fails, the bot logs the error and retries after 5 seconds.

### **Input Validation**
- **Statements**: Truncated to 600 characters.
- **Votes/Night Actions**: Validated for seat ID format (e.g., `seat-02`).
- **Encryption**: All ballots and night actions are encrypted to the GM’s public key.

### **Recovery**
- If a bot crashes, it resumes from its last action using:
  - `state.json` (current match state).
  - `{MY_SEAT}.log` (journal of actions).

---

## **6. Security**
- **Never commit private keys** to the repo.
- **Restrict PATs** to only push to the bot’s paths.
- **Rotate keys** between matches if compromised.

---

## **Troubleshooting**
### **Bot Crashes**
- Check `{MY_SEAT}.log` for errors.
- Verify the bot’s private key is available at `~/.bazaar/<seat>.key`.

### **Encryption Fails**
- Verify the GM’s public key in `setup/gm_public_key.txt`.
- Test encryption locally:
  ```bash
  python3 -c "from gm.crypto import encrypt_for_gm; print(encrypt_for_gm({'test': 'payload'}))"