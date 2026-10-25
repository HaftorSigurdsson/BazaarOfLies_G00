# Setup Guide — Bazaar of Lies

This is the **setup hub**: the order of operations, the pre-game testing checklist, and game-day procedure. Each step's details live in its own guide.

---

## **1. Order of Operations**
| Step | Guide | What happens |
|---|---|---|
| 1. Arena | [Arena Setup](./setup/arena_setup.md) | Create the private repo, branch protections, and the GM keypair (private half vaulted in `../.bazaar/`, public half committed). |
| 2. Seats | [Seats Configuration](./setup/seats_config.md) | Generate seat keypairs + Ed25519 signing keys, populate `setup/seats.json`, design personas. |
| 3. Bots | [Bot Deployment](./setup/bot_deployment.md) | Clone per seat, vault the private keys, write doctrines, run `uv run src/villager.py --seat seat-01`. |
| 4. GM | [Arena Operations → The GM](./operations.md#3-the-game-master-cron-driven) | A dedicated GM clone (`game_master/`) with its own git identity, the GM private key in the vault, and the **crontab line** that ticks it every 5 minutes (`flock`-guarded; optional `BAZAAR_MATCH_LIMIT` to park after N matches). |
| 5. Operations | [Arena Operations](./operations.md) | The Herald (`src/town-herald.py`), the Elder Council (`src/elder-council.py`), and the match reset (`src/town-reset.py`). |

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
2. Verify it **resumes from its journal** (`../.bazaar/journal-<seat>.json`).

---

## **3. Game Day**
1. **Agree on a start time** (GM clock is UTC).
2. **Start all 10 bots** (and the Herald, if running) at the agreed time:
   ```bash
   tools/bazaar-launch.sh start              # all ten seats + the Herald window (tmux "bazaar")
   tools/bazaar-launch.sh start 01 03 05     # a subset of seats
   tools/bazaar-launch.sh start --no-herald  # bots only
   # Windows: python3 tools/bazaar-launch.py start  (the .bat wrapper is retired to tools/STORE/)
   ```
3. **Enable the GM cron** (the crontab line from step 4 of the Order of Operations) — the first tick within 5 minutes deals Match 1 and the clock starts. ⚠️ Pick exactly **one GM driver**: the local cron (current default) or the GitHub Action — never both. (`tools/run.sh`, the old Herald-plus-Actions-heartbeat combo, is legacy.)
4. **Monitor the game**: the GM's own diary at `game_master/gm-cron.log` (every tick, every tally), the discussion in `gameplay/village/` (`tools/statements-assemble.py --watch` keeps a local transcript fresh), the graveyard, and the pressed PDFs as they appear in `gameplay/library/` — the Herald's editions and, after each match, the Elder Council's judgment.
5. **Do not interfere** during the match.
6. **Between matches**: Adjust personas/doctrines during the pit-stop window; reset with [town-reset.py](./operations.md) (add `--wipe-recaps` if the recaps should go too).
7. **After each match**: the full reveal is in `gameplay/village/match-XX-recap.md` (plus the truth archive, `match-XX-truth.md`); run `uv run src/elder-council.py --match N` to write the Council's judgment — shelved as a PDF in `gameplay/library/` beside the Herald's volumes.

---

## **4. Resetting the Game**
⚠️ **Always use the official script — `src/town-reset.py` — to reset between matches.** A partial manual reset once caused the **ghost-replay bug**: the GM re-counted a finished match's stale ballots and re-banished the same seats in the same order.

```bash
tools/bazaar-launch.sh stop        # bots must be down first
python3 src/town-reset.py          # asks "Are you sure?" (y/n) before wiping
python3 src/town-reset.py --dry-run   # preview without touching anything
python3 src/town-reset.py --wipe-recaps  # also remove match recaps (kept by default)
tools/bazaar-launch.sh start       # bots + Herald back up (Windows: python3 tools/bazaar-launch.py start)
# the cron GM ticks within 5 minutes; for an immediate tick, run gm/run.py
# from the GM clone with GM_PRIVATE_KEY set (see Arena Operations)
```

See the [Arena Operations guide](./operations.md) for exactly what the reset does (and keeps).

---

## **5. Troubleshooting Quick Reference**
| Symptom | Fix |
|---|---|
| GM not ticking | Check `game_master/gm-cron.log` (the last tick's error is in it); verify the crontab line is live (`crontab -l`), the GM private key file exists in `../.bazaar/`, and the clone is clean (`tools/seats-pull.py --no-pull`-style check). |
| Arena stuck in `halted` | The `BAZAAR_MATCH_LIMIT` parked it after a match — raise or remove the limit (or reset the arena) and the next tick deals. |
| Bot crashes | It resumes on restart from `state.json` + its journal. Missed ballot = abstain; missed night action = silence. |
| Encryption fails | Verify public keys in `setup/seats.json` are base64; test locally before deploying. |
| Vote rejected | Ballots must be signed with the seat's Ed25519 key and carry the current epoch — run `setup/make_signing_keys.py` once if keys are missing. |

Details: [Bot Deployment → Troubleshooting](./setup/bot_deployment.md), [Arena Setup → Troubleshooting](./setup/arena_setup.md).

---

**May your setup be flawless!**