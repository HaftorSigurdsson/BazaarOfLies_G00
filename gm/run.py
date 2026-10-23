#!/usr/bin/env python3
"""Bazaar of Lies — Game Master (v2, patched).

Runs in GitHub Actions (gm.yml) every 5 minutes; also runnable locally with
GM_NO_PUSH=1 (never publishes; use a throwaway GM_PRIVATE_KEY for testing).

Contract with bots (bot.py):
  - day transcript:   village/day-<CCC>.jsonl   (bots append; GM reads)
  - sealed ballots:   votes/<seat>-c<CCC>.enc    (payload: match, cycle, seat, vote, ts)
  - night actions:    night/<seat>-c<CCC>.enc    (payload: match, cycle, seat, target, ts)
  - GM→seat traffic:  dossiers/<seat>-c<CCC>-result.enc  (detective results)
  - role registry:    gm/roles.enc — the deal, sealed to the GM's own public key.
    The repo never holds roles in plaintext. The GM decrypts the registry
    with GM_PRIVATE_KEY whenever it needs roles: night validation, win
    check, death reveals, recap. Night actions are validated against the
    registry — a bot's self-declared role is never trusted.
"""
import base64
import json
import os
import random
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta

from crypto import load_gm_private_key, decrypt_payload, encrypt_for_seat
from utils import (read_state, write_state, update_announcements,
                   update_graveyard, get_seats, is_alive)

# ---------------------------------------------------------------- tuning ---
DISCUSSION_MINUTES = 30
VOTING_MINUTES = 10
NIGHT_MINUTES = 15
GM_ROLES_FILE = "gm/roles.enc"
SECURE_RANDOM = random.SystemRandom()
PUBLISH = not os.environ.get("GM_NO_PUSH")   # GM_NO_PUSH=1 → local testing

KIND_BY_ROLE = {"Mafia": "kill", "Doctor": "save", "Detective": "investigate"}


def log(msg):
    print(f"[GM {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def get_gm_private_key():
    b64 = os.environ.get("GM_PRIVATE_KEY")
    if not b64:
        raise RuntimeError(
            "GM_PRIVATE_KEY is not set. In Actions it comes from the secret; "
            "locally pass a throwaway: "
            'GM_PRIVATE_KEY=$(python3 -c "import base64,os;'
            'print(base64.b64encode(os.urandom(32)).decode())")')
    return load_gm_private_key(b64)


# ---------------------------------------------------------------- publish ---
def commit_and_push(label, attempts=3):
    """Publish GM work to the arena. Without this the match is invisible."""
    if not PUBLISH:
        log(f"GM_NO_PUSH set — not publishing: {label}")
        return
    paths = [p for p in ["state.json", "graveyard.md", "village",
                         "deals", "dossiers", GM_ROLES_FILE]
             if os.path.exists(p)]
    for attempt in range(1, attempts + 1):
        r = subprocess.run(["git", "pull", "--rebase", "--autostash"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            log(f"pull failed (attempt {attempt}): {r.stderr.strip()[:200]}")
            time.sleep(2 * attempt)
            continue
        subprocess.run(["git", "add", *paths], check=False)
        c = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if c.returncode == 0:
            log(f"nothing to publish for: {label}")
            return
        subprocess.run(["git", "commit", "-m", f"GM: {label}"],
                       check=True, capture_output=True, text=True)
        p = subprocess.run(["git", "push"], capture_output=True, text=True)
        if p.returncode == 0:
            log(f"published: {label}")
            return
        log(f"push rejected (attempt {attempt}): {p.stderr.strip()[:200]}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"could not publish: {label}")


# ---------------------------------------------------------------- registry ---
def save_role_registry(priv, assignment):
    payload = {"ts": datetime.now(timezone.utc).isoformat(),
               "roles": assignment}
    sealed = encrypt_for_seat(
        base64.b64encode(bytes(priv.public_key)).decode(), payload)
    with open(GM_ROLES_FILE, "w") as f:
        f.write(sealed)


def load_role_registry(priv):
    with open(GM_ROLES_FILE) as f:
        payload = decrypt_payload(priv, f.read().strip())
    return payload["roles"]


# ------------------------------------------------------------ state machine ---
def advance_phase():
    state = read_state()
    phase = state["phase"]
    now = datetime.now(timezone.utc)

    if phase == "setup":
        log("phase=setup → dealing roles, opening cycle 1 discussion")
        state["match"] = 1
        state["cycle"] = 1
        state["phase"] = "discussion"
        state["clock"] = {
            "dawn": now.isoformat(),
            "discussion_deadline": (now + timedelta(minutes=DISCUSSION_MINUTES)).isoformat(),
            "voting_deadline": None,
            "night_deadline": None,
        }
        write_state(state)
        update_announcements(
            f"**Match {state['match']}, Cycle {state['cycle']}**\n"
            "The bazaar awakens! Roles have been dealt.\n"
            f"**Seats alive:** {', '.join(state['alive'])}\n"
            f"**Discussion ends at:** {state['clock']['discussion_deadline']}"
        )
        deal_roles()
        commit_and_push("match 1 dealt, cycle 1 discussion opens")

    elif phase == "discussion":
        deadline = datetime.fromisoformat(state["clock"]["discussion_deadline"])
        if now < deadline:
            log(f"phase=discussion → waiting until {deadline.isoformat()}")
            return
        log("phase=discussion → discussion closed, voting opens")
        state["phase"] = "voting"
        state["clock"]["voting_deadline"] = (now + timedelta(minutes=VOTING_MINUTES)).isoformat()
        write_state(state)
        update_announcements(
            f"**Match {state['match']}, Cycle {state['cycle']}**\n"
            "The discussion ends. The bazaar votes!\n"
            f"**Voting ends at:** {state['clock']['voting_deadline']}"
        )
        commit_and_push(f"cycle {state['cycle']} voting opens")

    elif phase == "voting":
        deadline = datetime.fromisoformat(state["clock"]["voting_deadline"])
        if now < deadline:
            log(f"phase=voting → waiting until {deadline.isoformat()}")
            return
        log("phase=voting → voting closed, tallying ballots")
        tally_votes()
        state = read_state()   # tally mutated it
        state["phase"] = "night"
        state["clock"]["night_deadline"] = (now + timedelta(minutes=NIGHT_MINUTES)).isoformat()
        write_state(state)
        update_announcements(
            f"**Match {state['match']}, Cycle {state['cycle']}**\n"
            "The sun sets. The bazaar sleeps. Night actions begin!\n"
            f"**Night ends at:** {state['clock']['night_deadline']}"
        )
        commit_and_push(f"cycle {state['cycle']} tally done, night falls")

    elif phase == "night":
        deadline = datetime.fromisoformat(state["clock"]["night_deadline"])
        if now < deadline:
            log(f"phase=night → waiting until {deadline.isoformat()}")
            return
        log("phase=night → resolving night actions")
        resolve_night_actions()
        state = read_state()
        if check_win_conditions():
            end_match()
            commit_and_push(f"match {state['match']} ended with recap")
            return
        state["cycle"] += 1
        state["phase"] = "discussion"
        state["clock"] = {
            "dawn": now.isoformat(),
            "discussion_deadline": (now + timedelta(minutes=DISCUSSION_MINUTES)).isoformat(),
            "voting_deadline": None,
            "night_deadline": None,
        }
        write_state(state)
        update_announcements(
            f"**Match {state['match']}, Cycle {state['cycle']}**\n"
            "The bazaar awakens!\n"
            f"**Seats alive:** {', '.join(state['alive'])}\n"
            f"**Discussion ends at:** {state['clock']['discussion_deadline']}"
        )
        commit_and_push(f"cycle {state['cycle']} opens after night")

    else:
        log(f"phase={phase!r} → unknown phase, doing nothing")


# ------------------------------------------------------------------- deal ---
def deal_roles():
    """Deal roles and seal them: one dossier per seat + the GM registry."""
    state = read_state()
    seats = get_seats()
    living = list(state["alive"])
    priv = get_gm_private_key()
    sr = SECURE_RANDOM

    north = [s for s in living if int(s.split("-")[1]) <= 5]
    south = [s for s in living if int(s.split("-")[1]) > 5]
    assignment = {}

    # Three Mafia: one guaranteed per stable, third in a random stable.
    assignment[sr.choice(north)] = "Mafia"
    assignment[sr.choice(south)] = "Mafia"
    third_pool = north if sr.random() < 0.5 else south
    assignment[sr.choice([s for s in third_pool if s not in assignment])] = "Mafia"

    # Power roles: one per stable, random stable gets the Detective.
    detective_pool, doctor_pool = (north, south) if sr.random() < 0.5 else (south, north)
    assignment[sr.choice([s for s in detective_pool if s not in assignment])] = "Detective"
    assignment[sr.choice([s for s in doctor_pool if s not in assignment])] = "Doctor"

    for seat in living:
        assignment.setdefault(seat, "Villager")

    mafia_key = base64.b64encode(os.urandom(32)).decode()
    for seat in living:
        dossier = {
            "role": assignment[seat],
            "teammates": ([s for s in living if assignment[s] == "Mafia" and s != seat]
                          if assignment[seat] == "Mafia" else []),
            "night_channel_key": mafia_key if assignment[seat] == "Mafia" else None,
        }
        sealed = encrypt_for_seat(seats[seat]["public_key"], dossier)
        with open(f"deals/{seat}.enc", "w") as f:
            f.write(sealed)

    save_role_registry(priv, assignment)
    log(f"dealt {len(living)} roles (dossiers sealed to seats, registry sealed to GM)")


# ------------------------------------------------------------------ votes ---
def tally_votes():
    state = read_state()
    priv = get_gm_private_key()
    registry = load_role_registry(priv)

    # Collect this cycle's ballots; keep only the LATEST ballot per seat.
    ballots = []
    for fn in sorted(os.listdir("votes")):
        if not fn.endswith(".enc"):
            continue
        try:
            with open(f"votes/{fn}") as f:
                b = decrypt_payload(priv, f.read().strip())
        except Exception as e:
            log(f"unreadable ballot {fn}: {e}")
            continue
        if b.get("match") != state["match"] or b.get("cycle") != state["cycle"]:
            continue
        if b.get("seat") not in state["alive"]:
            log(f"ballot from dead seat ignored: {b.get('seat')}")
            continue
        ballots.append((b.get("ts", ""), b["seat"], b.get("vote")))

    ballots.sort(key=lambda x: x[0])
    latest = {}
    for ts, seat, vote in ballots:
        latest[seat] = vote

    counts = Counter()
    for vote in latest.values():
        counts[vote if vote in state["alive"] else "abstain"] += 1
    log(f"tally: {dict(counts) or 'no votes'}")

    max_votes = max(counts.values()) if counts else 0
    top = [s for s, c in counts.items() if c == max_votes]
    banished = top[0] if max_votes > 0 and len(top) == 1 and top[0] != "abstain" else None

    if banished:
        state["alive"].remove(banished)
        seats = get_seats()
        role = registry.get(banished, "Unknown")
        update_graveyard(banished, seats[banished]["persona"], role, "Village vote")
        update_announcements(
            f"**Banishment!** {banished} ({seats[banished]['persona']}) "
            "has been banished from the bazaar.\n"
            f"Their role was: **{role}**."
        )
        log(f"banished {banished} (role revealed: {role})")
    else:
        update_announcements("No banishment this cycle (tie or no votes).")
        log("no banishment")

    write_state(state)


# ------------------------------------------------------------------ night ---
def resolve_night_actions():
    state = read_state()
    priv = get_gm_private_key()
    registry = load_role_registry(priv)
    seats = get_seats()

    # Collect actions; classify by the REGISTRY role of the sender
    # (a bot's self-declared role is never trusted). Latest per seat wins.
    actions = []
    for fn in sorted(os.listdir("night")):
        if not fn.endswith(".enc"):
            continue
        try:
            with open(f"night/{fn}") as f:
                a = decrypt_payload(priv, f.read().strip())
        except Exception as e:
            log(f"unreadable night action {fn}: {e}")
            continue
        if a.get("match") != state["match"] or a.get("cycle") != state["cycle"]:
            continue
        seat, target = a.get("seat"), a.get("target")
        if seat not in state["alive"]:
            continue
        kind = KIND_BY_ROLE.get(registry.get(seat))
        if not kind:
            log(f"night action from {seat} ignored (no night role)")
            continue
        if target not in state["alive"]:
            log(f"night action from {seat} targets dead {target} — ignored")
            continue
        actions.append((a.get("ts", ""), seat, kind, target))

    actions.sort(key=lambda x: x[0])
    latest = {}
    for ts, seat, kind, target in actions:
        latest[seat] = (kind, target)

    kills, saves, investigates = [], [], []
    for seat, (kind, target) in latest.items():
        {"kill": kills, "save": saves, "investigate": investigates}[kind].append((seat, target))

    # Mafia kill: majority target among Mafia submissions; tie → last received.
    kill_target = None
    if kills:
        kc = Counter(t for _, t in kills)
        top_count = max(kc.values())
        top_targets = [t for t, c in kc.items() if c == top_count]
        kill_target = top_targets[-1]

    if kill_target and kill_target not in {t for _, t in saves}:
        state["alive"].remove(kill_target)
        role = registry.get(kill_target, "Unknown")
        update_graveyard(kill_target, seats[kill_target]["persona"], role)
        update_announcements(
            f"**Night kill!** {kill_target} ({seats[kill_target]['persona']}) "
            f"was found dead in the bazaar. Their role was: **{role}**."
        )
        log(f"night kill: {kill_target} (role revealed: {role})")
    else:
        update_announcements("The night passed quietly.")
        log("no kill (saved, or no Mafia action)")

    # Detective results go to the DETECTIVE — never to the investigated seat.
    for detective, target in investigates:
        result = "Family" if registry.get(target) == "Mafia" else "not Family"
        payload = {
            "match": state["match"], "cycle": state["cycle"],
            "kind": "investigation", "target": target, "result": result,
        }
        sealed = encrypt_for_seat(seats[detective]["public_key"], payload)
        fn = f"dossiers/{detective}-c{state['cycle']:03d}-result.enc"
        with open(fn, "w") as f:
            f.write(sealed)
        log(f"investigation result sealed to {detective} about {target}")

    write_state(state)


# ------------------------------------------------------------- end of game ---
def check_win_conditions():
    state = read_state()
    registry = load_role_registry(get_gm_private_key())
    mafia = sum(1 for s in state["alive"] if registry.get(s) == "Mafia")
    town = len(state["alive"]) - mafia
    log(f"win check: mafia={mafia} town={town}")
    if mafia == 0:
        update_announcements("The Town has won! All Mafiosi have been banished.")
        return True
    if mafia >= town:
        update_announcements("The Family has won! They outnumber the Town.")
        return True
    return False


def end_match():
    state = read_state()
    registry = load_role_registry(get_gm_private_key())
    seats = get_seats()

    with open(f"village/match-{state['match']:02d}-recap.md", "w") as f:
        f.write("# Match Recap\n\n**Full Reveal**\n\n")
        f.write("| Seat | Persona | Role | Stable |\n|---|---|---|---|\n")
        for seat in seats:
            stable = "North" if int(seat.split("-")[1]) <= 5 else "South"
            f.write(f"| {seat} | {seats[seat]['persona']} | "
                    f"{registry.get(seat, 'Unknown')} | {stable} |\n")

    state["match"] += 1
    state["cycle"] = 0
    state["phase"] = "setup"        # next cron run deals the next match
    state["alive"] = list(seats.keys())
    state["graveyard"] = {}
    write_state(state)
    update_announcements(
        f"Match {state['match'] - 1} has ended. "
        f"The bazaar prepares for Match {state['match']}."
    )
    log(f"match ended; next match is {state['match']} (auto-chains on next run)")


if __name__ == "__main__":
    try:
        advance_phase()
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
