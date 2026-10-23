#!/usr/bin/env python3
"""Bazaar of Lies — autonomous bot.

Run from inside a bot clone of the arena repo:

    uv run bot.py --seat seat-01

Private files (seat key, doctrine, journal) live in a sibling folder of the
bot clone — `../bazaar/` by default, resolved relative to bot.py's own
location. It is outside the repo because this process runs `git add` in the
same working tree it lives in: the seat's private key and doctrine must be
structurally unreachable by git.

State tracking (statements made, voted, night action done) lives in a local
journal file so a crashed bot resumes correctly on restart.
"""
import argparse
import glob
import json
import os
import random
import re
import subprocess
import time

from mistralai import Mistral

from gm.crypto import encrypt_for_seat, load_gm_private_key, decrypt_payload

# ---------------------------------------------------------------- config ---
MODEL = "mistral-small-2409"            # PIN the exact versioned model ID
POLL_SECONDS = 30                       # arena poll interval (per game rules)
JITTER_SECONDS = 5                      # random extra sleep, avoids herd pushes
MAX_STATEMENTS_PER_DAY = 2              # per game rules
MIN_SECONDS_BETWEEN_STATEMENTS = 300    # pace the two statements out
PUSH_ATTEMPTS = 5                       # retries before giving up loudly
STATEMENT_MAX_CHARS = 600               # per game rules

# ------------------------------------------------------------------ args ---
parser = argparse.ArgumentParser(description="Bazaar of Lies Bot")
parser.add_argument("--seat", required=True, help="Seat ID (e.g., seat-01)")
parser.add_argument("--key", default=None,
                    help="Seat private key path (default ../bazaar/<seat>.key)")
parser.add_argument("--doctrine", default=None,
                    help="Doctrine file path (default ../bazaar/<seat>.md)")
parser.add_argument("--journal", default=None,
                    help="Journal path (default ../bazaar/journal-<seat>.json)")
args = parser.parse_args()

MY_SEAT = args.seat
# ../bazaar/ — a sibling of the bot clone's root, so git can never see it.
# Anchored to bot.py's own location (not the current working directory), so
# the paths hold no matter where the bot is launched from.
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
BAZAAR_DIR = os.path.join(os.path.dirname(REPO_ROOT), "bazaar")
KEY_PATH = args.key or os.path.join(BAZAAR_DIR, f"{MY_SEAT}.key")
DOCTRINE_PATH = args.doctrine or os.path.join(BAZAAR_DIR, f"{MY_SEAT}.md")
JOURNAL_PATH = args.journal or os.path.join(BAZAAR_DIR, f"journal-{MY_SEAT}.json")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {MY_SEAT}: {msg}", flush=True)


# ------------------------------------------------------------------- git ---
def git(*argv, check=True):
    return subprocess.run(["git", *argv], check=check,
                          capture_output=True, text=True)


def safe_push():
    """Push with retry: ten bots share one branch, rejections are guaranteed."""
    for attempt in range(1, PUSH_ATTEMPTS + 1):
        r = git("push", check=False)
        if r.returncode == 0:
            return
        log(f"push rejected (attempt {attempt}/{PUSH_ATTEMPTS}); rebasing")
        git("pull", "--rebase", check=False)
        time.sleep(2 * attempt)
    raise RuntimeError(f"push rejected {PUSH_ATTEMPTS} times — needs a human")


def commit_and_push(paths, msg):
    git("add", *paths)
    r = git("commit", "-m", msg, check=False)
    if r.returncode != 0:
        log(f"nothing to commit for: {msg}")
        return
    safe_push()


# --------------------------------------------------------------- journal ---
def load_journal():
    if os.path.exists(JOURNAL_PATH):
        with open(JOURNAL_PATH) as f:
            return json.load(f)
    return {"cycles": {}, "seen": []}


def save_journal(journal):
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    with open(JOURNAL_PATH, "w") as f:
        json.dump(journal, f, indent=2)


def cycle_state(journal, match, cycle):
    key = f"{match}:{cycle}"
    if key not in journal["cycles"]:
        journal["cycles"][key] = {
            "statements": 0, "last_statement_ts": 0,
            "voted": False, "night_action": False,
        }
    return journal["cycles"][key]


# ---------------------------------------------------------- arena readers ---
def read_state():
    with open("state.json") as f:
        return json.load(f)


def get_persona():
    with open("setup/seats.json") as f:
        return json.load(f)["seats"][MY_SEAT]["persona"]


def get_doctrine():
    with open(DOCTRINE_PATH) as f:
        return f.read()


def gm_public_key():
    with open("setup/gm_public_key.txt") as f:
        return f.read().strip()


_dossier_cache = None


def get_role_dossier():
    """Decrypt this seat's role dossier (deals/) with the seat private key.
    Cached: the role never changes within a match."""
    global _dossier_cache
    if _dossier_cache is None:
        matches = sorted(glob.glob(f"deals/*{MY_SEAT}*.enc"))
        if not matches:
            raise FileNotFoundError(
                f"no role dossier for {MY_SEAT} in deals/ — has the GM dealt yet?")
        priv = load_gm_private_key(open(KEY_PATH).read().strip())
        with open(matches[0]) as f:
            _dossier_cache = decrypt_payload(priv, f.read().strip())
    return _dossier_cache


def read_unread_dossiers(journal):
    """Read GM→bot private traffic (dossiers/) this seat hasn't seen yet.
    Delivers night results (e.g., detective investigations) into the prompt."""
    msgs = []
    if not os.path.isdir("dossiers"):
        return msgs
    priv = load_gm_private_key(open(KEY_PATH).read().strip())
    for path in sorted(glob.glob(f"dossiers/*{MY_SEAT}*.enc")):
        if path in journal["seen"]:
            continue
        try:
            with open(path) as f:
                msgs.append(decrypt_payload(priv, f.read().strip()))
            journal["seen"].append(path)
        except Exception as e:  # keep polling on a bad file
            log(f"could not decrypt {path}: {e}")
    if msgs:
        save_journal(journal)
    return msgs


def recent_statements(cycle, limit=40):
    """Public village transcript for the current day, most recent last.

    Per-seat statement files (no shared write target -> no merge conflicts),
    plus the legacy single-file transcript if present. Ordered by ts.
    """
    recs = {}
    sources = []
    legacy = f"village/day-{cycle:03d}.jsonl"
    if os.path.exists(legacy):
        sources.append(legacy)
    sdir = "village/statements"
    if os.path.isdir(sdir):
        pref = f"c{cycle:03d}-seat-"
        sources += [os.path.join(sdir, p) for p in sorted(os.listdir(sdir))
                    if p.startswith(pref) and p.endswith(".jsonl")]
    for path in sources:
        try:
            fh = open(path)
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue  # partial line mid-write by another bot
                key = (rec.get("seat"), rec.get("seq"))
                if key not in recs:
                    recs[key] = rec
    ordered = sorted(recs.values(), key=lambda r: r.get("ts", ""))
    return [f"{r['seat']}: {r['text']}" for r in ordered][-limit:]


def transcript_block(cycle):
    lines = recent_statements(cycle)
    return "\n".join(lines) if lines else "(The village has said nothing yet today.)"


# ------------------------------------------------------------ model call ---
def ask(system, user, temperature=0.7):
    r = client.chat.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return (r.choices[0].message.content or "").strip()


def parse_seat_id(text):
    m = re.search(r"seat-\d{2}", text or "")
    return m.group(0) if m else None


# ------------------------------------------------------------- phase acts ---
def do_discussion(state, cs, journal):
    if cs["statements"] >= MAX_STATEMENTS_PER_DAY:
        log(f"phase=discussion → statement budget used "
            f"({cs['statements']}/{MAX_STATEMENTS_PER_DAY}), idle")
        return
    if cs["statements"] > 0 and time.time() - cs["last_statement_ts"] < MIN_SECONDS_BETWEEN_STATEMENTS:
        log("phase=discussion → pacing, idle")
        return

    statement = ask(
        f"You are {get_persona()}\n\n"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}\n\n"
        f"Village transcript so far today:\n{transcript_block(state['cycle'])}",
        f"This is public statement {cs['statements'] + 1} of "
        f"{MAX_STATEMENTS_PER_DAY} allowed today. "
        f"Write your statement ({STATEMENT_MAX_CHARS} chars max), in character."
    )[:STATEMENT_MAX_CHARS]

    sdir = "village/statements"
    os.makedirs(sdir, exist_ok=True)
    path = f"{sdir}/c{state['cycle']:03d}-seat-{MY_SEAT}.jsonl"
    rec = {
        "match": state["match"], "cycle": state["cycle"], "seat": MY_SEAT,
        "seq": cs["statements"] + 1, "text": statement,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    commit_and_push([path], f"Statement c{state['cycle']:03d}/{rec['seq']} by {MY_SEAT}")

    cs["statements"] += 1
    cs["last_statement_ts"] = time.time()
    save_journal(journal)
    log(f"posted statement {cs['statements']}/{MAX_STATEMENTS_PER_DAY} for cycle {state['cycle']:03d}")


def do_vote(state, cs, journal):
    if cs["voted"]:
        log("phase=voting → already voted this cycle, idle")
        return

    answer = ask(
        f"You are {get_persona()}\n\n"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}\n\n"
        f"Village transcript so far today:\n{transcript_block(state['cycle'])}",
        "The voting window is open. Who do you vote to banish? "
        "Output ONLY the seat ID, e.g. 'seat-02'."
    )
    vote = parse_seat_id(answer)
    if not vote:
        log(f"model output contained no seat ID ({answer[:60]!r}) — retrying next poll")
        return

    payload = {
        "match": state["match"], "cycle": state["cycle"], "seat": MY_SEAT,
        "vote": vote, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    sealed = encrypt_for_seat(gm_public_key(), payload)
    filename = f"votes/{MY_SEAT}-c{state['cycle']:03d}.enc"
    with open(filename, "w") as f:
        f.write(sealed)
    commit_and_push([filename], f"Ballot c{state['cycle']:03d} by {MY_SEAT}")

    cs["voted"] = True
    save_journal(journal)
    log(f"sealed ballot cast for cycle {state['cycle']:03d} → {vote} (content sealed to GM)")


def do_night(state, cs, journal):
    if cs["night_action"]:
        log("phase=night → action already done this cycle, idle")
        return

    dossier = get_role_dossier()
    role = dossier.get("role", "Villager")
    results = read_unread_dossiers(journal)

    if role == "Villager":
        cs["night_action"] = True  # villagers sleep
        save_journal(journal)
        log("phase=night → Villager, sleeping")
        return

    result_block = ("\nPrivate results from the GM (most recent last):\n"
                    + "\n".join(json.dumps(m) for m in results)
                    if results else "")
    answer = ask(
        f"You are {get_persona()}\n"
        f"Your secret role is: {role}.\n"
        f"Role instructions from the GM: {json.dumps(dossier)}\n\n"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}{result_block}",
        "It is night. Submit your night action. "
        "Output ONLY the target seat ID, e.g. 'seat-02'."
    )
    target = parse_seat_id(answer)
    if not target:
        log(f"model output contained no seat ID ({answer[:60]!r}) — retrying next poll")
        return

    payload = {
        "match": state["match"], "cycle": state["cycle"], "seat": MY_SEAT,
        "role": role, "target": target,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    sealed = encrypt_for_seat(gm_public_key(), payload)
    filename = f"night/{MY_SEAT}-c{state['cycle']:03d}.enc"
    with open(filename, "w") as f:
        f.write(sealed)
    commit_and_push([filename], f"Night action c{state['cycle']:03d} by {MY_SEAT}")

    cs["night_action"] = True
    save_journal(journal)
    log(f"sealed night action sent for cycle {state['cycle']:03d} (sealed to GM)")


# ------------------------------------------------------------- main loop ---
def main_loop():
    journal = load_journal()
    log(f"bot up — model={MODEL}")
    log(f"key={KEY_PATH} doctrine={DOCTRINE_PATH} journal={JOURNAL_PATH}")

    while True:
        try:
            git("pull", "--rebase")
            state = read_state()
            phase = state.get("phase", "unknown")
            alive = state.get("alive", [])
            match, cycle = state.get("match", 0), state.get("cycle", 0)
            cs = cycle_state(journal, match, cycle)

            if MY_SEAT not in alive:
                log(f"phase={phase} → not alive, spectating")
            elif phase == "discussion":
                do_discussion(state, cs, journal)
            elif phase == "voting":
                do_vote(state, cs, journal)
            elif phase == "night":
                do_night(state, cs, journal)
            else:
                log(f"phase={phase} → idle")

        except FileNotFoundError as e:
            log(f"waiting: {e}")
        except Exception as e:  # a bot must never die quietly
            log(f"ERROR: {type(e).__name__}: {e}")

        time.sleep(POLL_SECONDS + random.uniform(0, JITTER_SECONDS))


if __name__ == "__main__":
    main_loop()
