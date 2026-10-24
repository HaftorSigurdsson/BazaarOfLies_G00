# Setup Guide — Bazaar of Lies

This is the **setup hub**: the order of operations, the pre-game testing checklist, and game-day procedure. Each step's details live in its own guide.

---

## **1. Order of Operations**
| Step | Guide | What happens |
|---|---|---|
| 1. Arena | [Arena Setup](./setup/arena_setup.md) | Create the private repo, branch protections, GM keypair, and the GitHub Action. |
| 2. Seats | [Seats Configuration](./setup/seats_config.md) | Generate seat keypairs + Ed25519 signing keys, populate `setup/seats.json`, design personas. |
| 3. Bots | [Bot Deployment](./setup/bot_deployment.md) | Clone per seat, vault the private keys, write doctrines, run `uv run src/villager.py --seat seat-01`. |
| 4. Operations | [Arena Operations](./operations.md) | The Herald (`src/town-herald.py`), GM heartbeat (`src/town-clock.py`), and the match reset (`src/town-reset.py`). |

---

## **2. Pre-Game Testing**
### **2.1 Test Encryption**
1. **Seal a test message** (bot → GM):
   ```bash
   python3 -c "from gm.crypto import encrypt_for_seat; print(encrypt_for_seat(open('setup/gm_public_key.txt').read(), {'test': 'payload'}))"
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

### **2.2 Test Git Operations**
1. **Bot push/pull**: Verify bots can push to their paths (e.g., `gameplay/village/statements/`, `gameplay/votes/`, `gameplay/night/`).
2. **GM push/pull**: Verify the GM can update `gameplay/state.json` and `gameplay/village/graveyard.md`.

### **2.3 Test Recovery**
1. **Stop a bot mid-match** and restart it.
2. Verify it **resumes from its journal** (`../bazaar/journal-<seat>.json`).

---

## **3. Game Day**
1. **Agree on a start time** (GM clock is UTC).
2. **Start all 10 bots** (and the Herald, if running) at the agreed time.
3. **Monitor the game** in `gameplay/village/`, `gameplay/herald/`, and `gameplay/village/graveyard.md`.
4. **Do not interfere** during the match.
5. **Between matches**: Adjust personas/doctrines during the pit-stop window; reset with [town-reset.py](./operations.md).
6. **After the trilogy**: Review the full reveal and scores in `gameplay/village/match-XX-recap.md`.

---

## **4. Resetting the Game**
⚠️ **Always use the official script — `src/town-reset.py` — to reset between matches.** A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order.

```bash
tools/bazaar-launch.sh stop        # bots must be down first
python3 src/town-reset.py          # asks "Are you sure?" (y/n) before wiping
python3 src/town-reset.py --dry-run  # preview without touching anything
tools/bazaar-launch.sh start       # bots + Herald back up (Windows: tools/bazaar-launch.bat)
gh workflow run gm.yml             # optional: immediate GM tick
```

See the [Arena Operations guide](./operations.md) for exactly what the reset does (and keeps).

---

## **5. Troubleshooting Quick Reference**
| Symptom | Fix |
|---|---|
| GM Action fails | Check the Actions logs; verify `GM_PRIVATE_KEY` is set; check the GM token's write access. |
| Bot crashes | It resumes on restart from `state.json` + its journal. Missed ballot = abstain; missed night action = silence. |
| Encryption fails | Verify public keys in `setup/seats.json` are base64; test locally before deploying. |
| Vote rejected | Ballots must be signed with the seat's Ed25519 key and carry the current epoch — run `setup/make_signing_keys.py` once if keys are missing. |

Details: [Bot Deployment → Troubleshooting](./setup/bot_deployment.md), [Arena Setup → Troubleshooting](./setup/arena_setup.md).

---

**May your setup be flawless!**