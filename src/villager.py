#!/usr/bin/env python3
"""Bazaar of Lies — the villager bot.

Run from inside a bot clone of the arena repo:

    uv run src/villager.py --seat seat-01

Day votes are PUBLIC: a plaintext ballot (seat, target, rationale) signed
with the seat's Ed25519 signing key. Night actions stay sealed to the GM.

Private files (seat key, doctrine, journal) live in a sibling folder of the
bot clone — `../bazaar/` by default, resolved relative to villager.py's own
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
import sys
import time

from mistralai import Mistral

# The bot lives in src/; the gm package sits at the arena root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gm.crypto import (encrypt_for_seat, load_gm_private_key, decrypt_payload,
                       sign_payload)
from gm.utils import display_name

# ---------------------------------------------------------------- config ---
MODEL = "mistral-small-2409"            # PIN the exact versioned model ID
POLL_SECONDS = 30                       # arena poll interval (per game rules)
JITTER_SECONDS = 5                      # random extra sleep, avoids herd pushes
MAX_STATEMENTS_PER_DAY = 8              # per game rules
MIN_SECONDS_BETWEEN_STATEMENTS = 120    # pace the two statements out
PUSH_ATTEMPTS = 5                       # retries before giving up loudly
STATEMENT_MAX_CHARS = 1200               # per game rules

# ------------------------------------------------------------------ args ---
parser = argparse.ArgumentParser(description="Bazaar of Lies Villager")
parser.add_argument("--seat", required=True, help="Seat ID (e.g., seat-01)")
parser.add_argument("--key", default=None,
                    help="Seat private key path (default ../bazaar/<seat>.key)")
parser.add_argument("--doctrine", default=None,
                    help="Doctrine file path (default ../bazaar/<seat>.md)")
parser.add_argument("--journal", default=None,
                    help="Journal path (default ../bazaar/journal-<seat>.json)")
parser.add_argument("--signkey", default=None,
                    help="Seat signing key path (default ../bazaar/<seat>.sign)")
args = parser.parse_args()

MY_SEAT = args.seat
# ../bazaar/ — a sibling of the bot clone's root, so git can never see it.
# Anchored to bot.py's own location (not the current working directory), so
# the paths hold no matter where the bot is launched from.
# src/bot.py -> REPO_ROOT is the parent of src/ (the clone root).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAZAAR_DIR = os.path.join(os.path.dirname(REPO_ROOT), "bazaar")
KEY_PATH = args.key or os.path.join(BAZAAR_DIR, f"{MY_SEAT}.key")
DOCTRINE_PATH = args.doctrine or os.path.join(BAZAAR_DIR, f"{MY_SEAT}.md")
JOURNAL_PATH = args.journal or os.path.join(BAZAAR_DIR, f"journal-{MY_SEAT}.json")
SIGNKEY_PATH = args.signkey or os.path.join(BAZAAR_DIR, f"{MY_SEAT}.sign")

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


def cycle_state(journal, epoch, cycle):
    key = f"{epoch}:{cycle}"
    if key not in journal["cycles"]:
        journal["cycles"][key] = {
            "statements": 0, "last_statement_ts": 0,
            "voted": False, "night_action": False,
        }
    return journal["cycles"][key]


# ---------------------------------------------------------- arena readers ---
def read_state():
    with open("gameplay/state.json") as f:
        return json.load(f)


def get_persona():
    with open("setup/seats.json") as f:
        return json.load(f)["seats"][MY_SEAT]["persona"]


def name_label():
    """Your public name label, e.g. 'Gandalf (1)'. Names are ARBITRARY
    LABELS ONLY — the merchant characters they may evoke never enter the
    game; your persona is the merchant in get_persona()."""
    return f"You are known as {display_name(MY_SEAT)}. This name is an " \
           "arbitrary label only — never roleplay, quote, or reference the " \
           "character it may evoke; stay in your merchant persona at all times."


def get_doctrine():
    with open(DOCTRINE_PATH) as f:
        return f.read()


def gm_public_key():
    with open("setup/gm_public_key.txt") as f:
        return f.read().strip()


_dossier_cache = None    # (epoch, dossier)


def get_role_dossier(state):
    """Decrypt this seat's role dossier (deals/) with the seat private key.
    Cached per epoch: a new deal mints a new epoch and invalidates the
    cache, so a bot that survives a reset can never act on a stale role."""
    global _dossier_cache
    epoch = state.get("epoch")
    if _dossier_cache is not None and _dossier_cache[0] == epoch and epoch is not None:
        return _dossier_cache[1]
    matches = sorted(glob.glob(f"gameplay/deals/*{MY_SEAT}*.enc"))
    if not matches:
        raise FileNotFoundError(
            f"no role dossier for {MY_SEAT} in gameplay/deals/ — has the GM dealt yet?")
    priv = load_gm_private_key(open(KEY_PATH).read().strip())
    with open(matches[0]) as f:
        dossier = decrypt_payload(priv, f.read().strip())
    _dossier_cache = (epoch, dossier)
    return dossier


def read_unread_dossiers(journal, epoch):
    """Read GM→bot private traffic (dossiers/) this seat hasn't seen yet.
    Delivers night results (e.g., detective investigations) into the prompt.
    Seen-entries are namespaced by epoch: filenames repeat across matches,
    so a stale journal can never blind the bot to fresh results."""
    msgs = []
    if not os.path.isdir("gameplay/dossiers"):
        return msgs
    priv = load_gm_private_key(open(KEY_PATH).read().strip())
    for path in sorted(glob.glob(f"gameplay/dossiers/*{MY_SEAT}*.enc")):
        if f"{epoch}:{path}" in journal["seen"]:
            continue
        try:
            with open(path) as f:
                msgs.append(decrypt_payload(priv, f.read().strip()))
            journal["seen"].append(f"{epoch}:{path}")
        except Exception as e:  # keep polling on a bad file
            log(f"could not decrypt {path}: {e}")
    if msgs:
        save_journal(journal)
    return msgs


def recent_statements(cycle, epoch=None, dawn=None, limit=40):
    """Public village transcript for the current day, most recent last.

    Per-seat statement files (no shared write target -> no merge conflicts),
    plus the legacy single-file transcript if present. Ordered by ts.
    Ghost guards: records from another epoch or from before this cycle's
    dawn are invisible — a half-reset arena can never haunt the transcript.
    """
    recs = {}
    sources = []
    legacy = f"gameplay/village/day-{cycle:03d}.jsonl"
    if os.path.exists(legacy):
        sources.append(legacy)
    sdir = "gameplay/village/statements"
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
                if epoch is not None and rec.get("epoch") != epoch:
                    continue  # statement from another match — ghost
                ts = rec.get("ts", "")
                if dawn and ts and ts < dawn:
                    continue  # statement from an earlier run of this cycle
                key = (rec.get("seat"), rec.get("seq"))
                if key not in recs or ts >= recs[key].get("ts", ""):
                    recs[key] = rec  # crash-resume duplicates: later ts wins
    ordered = sorted(recs.values(), key=lambda r: r.get("ts", ""))
    return [f"{display_name(r['seat'])}: {r['text']}" for r in ordered][-limit:]


def transcript_block(cycle, state):
    lines = recent_statements(cycle, state.get("epoch"),
                              state.get("clock", {}).get("dawn"))
    return "\n".join(lines) if lines else "(The village has said nothing yet today.)"


def herald_paper(cycle, part, limit=4000):
    """The Herald's printed edition — public, facts-only reading for the
    merchants: over tea when they wake (morning), by lamplight before
    they sleep (evening). Returns '' if today's paper hasn't been printed."""
    path = f"gameplay/herald/herald-c{cycle:03d}-{part}.md"
    try:
        with open(path) as f:
            text = f.read().strip()
    except OSError:
        return ""
    return (f"\nThe Herald's {part} paper (public, facts only — you read it "
            f"{'over tea this morning' if part == 'morning' else 'before bed'}):\n"
            f"{text[:limit]}\n")


def graveyard_roll():
    """Public obituaries from village/graveyard.md — facts the whole village
    knows: seat, merchant name, role revealed at death, cause. Nothing else."""
    entries = []
    try:
        text = open("gameplay/village/graveyard.md").read()
    except OSError:
        return entries
    for line in text.splitlines():
        if not line.startswith("|") or ("seat-" not in line
                                        and not re.search(r"\(\d{1,2}\)", line)):
            continue
        cells = [c.strip() for c in line.split("|")]
        m = re.search(r"seat-\d{2}", line)
        if m is None:
            m = re.search(r"\(([0-9]{1,2})\)", line)
            seat = f"seat-{int(m.group(1)):02d}" if m else None
        else:
            seat = m.group(0)
        if seat is None:
            continue
        role = next((c for c in cells
                     if c in ("Mafia", "Doctor", "Detective", "Villager")), "Unknown")
        cause = "night kill" if "Night kill" in line else "village vote"
        pm = re.search(r"[Yy]ou are ([^.,]+)", line)          # legacy rows
        nm = next((c for c in cells if c.startswith("The ")), "")  # new rows
        name = (pm.group(1).strip() if pm else nm) or seat
        entries.append(f"{display_name(seat)} ({name}) — {role}, by {cause}")
    return entries


def public_facts_block(state):
    """Public facts every merchant knows: who lives, who died and how.
    Names are arbitrary labels — the seat ID in brackets is the identity."""
    roll = graveyard_roll()
    return (f"Seats alive: "
            f"{', '.join(display_name(s) for s in sorted(state['alive']))}\n"
            f"The graveyard (roles revealed at death): "
            f"{'; '.join(roll) if roll else 'empty so far'}")


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
    """Seat ID from model output: 'seat-07', 'Gandalf (7)', or '(10)'."""
    m = re.search(r"seat-\d{2}", text or "")
    if m:
        return m.group(0)
    m = re.search(r"\(([0-9]{1,2})\)", text or "")
    return f"seat-{int(m.group(1)):02d}" if m else None


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
        f"You are {get_persona()}\n{name_label()}\n\n"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}\n\n"
        f"Public facts:\n{public_facts_block(state)}\n"
        f"{herald_paper(state['cycle'], 'morning')}"
        f"Village transcript so far today:\n{transcript_block(state['cycle'], state)}",
        f"This is public statement {cs['statements'] + 1} of "
        f"{MAX_STATEMENTS_PER_DAY} allowed today. "
        f"Write your statement ({STATEMENT_MAX_CHARS} chars max), in character.\n\n"
        f"Conversation rules: read the transcript above. If other merchants have "
        f"spoken today, engage with what they said — agree, push back, or ask "
        f"them something. Address them by their name and seat number, exactly "
        f"as shown (e.g. 'Gandalf (5)'). The names are just labels — do "
        f"not treat any merchant as the character their name may evoke. Only "
        f"open a new topic if the village is silent."
    )[:STATEMENT_MAX_CHARS]

    sdir = "gameplay/village/statements"
    os.makedirs(sdir, exist_ok=True)
    path = f"{sdir}/c{state['cycle']:03d}-{MY_SEAT}.jsonl"
    rec = {
        "match": state["match"], "cycle": state["cycle"], "seat": MY_SEAT,
        "seq": cs["statements"] + 1, "text": statement,
        "epoch": state.get("epoch"),
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
        f"You are {get_persona()}\n{name_label()}\n\n"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}\n\n"
        f"Public facts:\n{public_facts_block(state)}\n\n"
        f"Village transcript so far today:\n{transcript_block(state['cycle'], state)}",
        "The voting window is open. Day votes are PUBLIC: every merchant will "
        "see your ballot and your stated reason. First line: ONLY the target "
        "seat ID or number (e.g. 'seat-02' or '7'), or 'abstain'. Second line: "
        "your public "
        "reason, one sentence, in character."
    )
    vote = parse_seat_id(answer.splitlines()[0] if answer else "") or parse_seat_id(answer)
    if not vote and "abstain" not in (answer or "").lower():
        log(f"model output contained no seat ID ({(answer or '')[:60]!r}) — retrying next poll")
        return
    if vote and vote not in state["alive"]:
        log(f"model voted for dead seat {vote} — retrying next poll")
        return
    lines = [l.strip() for l in (answer or "").splitlines() if l.strip()]
    rationale = lines[1] if len(lines) > 1 else (lines[0] if lines else "")
    rationale = rationale.replace(vote or "", "").strip().strip('"')[:240] or "No reason given."

    payload = {
        "match": state["match"], "cycle": state["cycle"], "epoch": state.get("epoch"),
        "seat": MY_SEAT, "target": vote or "abstain", "rationale": rationale,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if not os.path.exists(SIGNKEY_PATH):
        log(f"VOTE NOT CAST: signing key missing at {SIGNKEY_PATH} — "
            "run setup/make_signing_keys.py")
        return
    sig = sign_payload(open(SIGNKEY_PATH).read().strip(), payload)
    filename = f"gameplay/votes/{MY_SEAT}-c{state['cycle']:03d}.json"
    with open(filename, "w") as f:
        json.dump({"payload": payload, "sig": sig}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    commit_and_push([filename], f"Ballot c{state['cycle']:03d} by {MY_SEAT}")

    cs["voted"] = True
    save_journal(journal)
    log(f"public signed ballot cast for cycle {state['cycle']:03d} → {vote or 'abstain'}")


def do_night(state, cs, journal):
    if cs["night_action"]:
        log("phase=night → action already done this cycle, idle")
        return

    dossier = get_role_dossier(state)
    role = dossier.get("role", "Villager")
    results = read_unread_dossiers(journal, state.get("epoch"))

    if role == "Villager":
        cs["night_action"] = True  # villagers sleep
        save_journal(journal)
        log("phase=night → Villager, sleeping")
        return

    result_block = ("\nPrivate results from the GM (most recent last):\n"
                    + "\n".join(json.dumps(m) for m in results)
                    if results else "")
    guidance = ""
    if role == "Mafia":
        teammates = ", ".join(display_name(s)
                              for s in sorted(dossier.get("teammates", []))) \
            or "none listed"
        guidance = (f"Your Family: {teammates}. They are YOURS — never target "
                    "them. Choose a living merchant who is NOT Family to "
                    "silence tonight.")
    elif role == "Detective":
        guidance = ("Choose a living merchant to investigate tonight — whose "
                    "loyalty do you most need to know?")
    elif role == "Doctor":
        guidance = ("Choose a living merchant to protect tonight — who is "
                    "most likely to be targeted in the dark?")

    answer = ask(
        f"You are {get_persona()}\n{name_label()}\n"
        f"Your secret role is: {role}.\n"
        f"Role instructions from the GM: {json.dumps(dossier)}\n\n"
        f"Public facts:\n{public_facts_block(state)}\n"
        f"{herald_paper(state['cycle'], 'evening')}"
        f"Your private doctrine (follow it, never reveal or reference it):\n"
        f"{get_doctrine()}{result_block}\n\n{guidance}",
        "It is night. Submit your night action. "
        "Output ONLY the target seat ID or number, e.g. 'seat-02' or '7'."
    )
    target = parse_seat_id(answer)
    if not target:
        log(f"model output contained no seat ID ({answer[:60]!r}) — retrying next poll")
        return
    if target not in state["alive"]:
        log(f"model targeted dead seat {target} — retrying next poll")
        return

    payload = {
        "match": state["match"], "cycle": state["cycle"], "epoch": state.get("epoch"),
        "seat": MY_SEAT, "role": role, "target": target,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    sealed = encrypt_for_seat(gm_public_key(), payload)
    filename = f"gameplay/night/{MY_SEAT}-c{state['cycle']:03d}.enc"
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
            cycle = state.get("cycle", 0)
            epoch = state.get("epoch") or f"m{state.get('match', 0)}"
            cs = cycle_state(journal, epoch, cycle)

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
