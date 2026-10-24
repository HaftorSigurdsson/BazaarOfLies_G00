#!/usr/bin/env python3
"""Bazaar of Lies — Game Master (v2, patched).

Runs in GitHub Actions (gm.yml) every 5 minutes; also runnable locally with
GM_NO_PUSH=1 (never publishes; use a throwaway GM_PRIVATE_KEY for testing).

Contract with bots (villager.py):
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
import secrets
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta

from crypto import (load_gm_private_key, decrypt_payload, encrypt_for_seat,
                   verify_payload)
from utils import (read_state, write_state, update_announcements,
                   update_graveyard, get_seats, is_alive, persona_name,
                   display_name)

# ---------------------------------------------------------------- tuning ---
# One round = 45 minutes, every window a multiple of the GM's 5-minute
# tick, so phase deadlines always land on a tick:
#   day   25 min — Morning, Morning tea, Lunch, Afternoon tea, Dinner
#    +     5 min — Evening (the vote)
#   night 15 min — The night, Night snacks, The night watch
DISCUSSION_MINUTES = 25
VOTING_MINUTES = 5
NIGHT_MINUTES = 15
# Park the arena instead of auto-chaining into the next match when the
# match number passes this limit (0 = unlimited, the default). Set it in
# the GM's environment (e.g. BAZAAR_MATCH_LIMIT=1 for a single match) —
# a halted arena waits in phase "halted" until an operator resets or
# raises the limit.
MATCH_LIMIT = int(os.environ.get("BAZAAR_MATCH_LIMIT", "0"))
GM_ROLES_FILE = "gm/roles.enc"
SECURE_RANDOM = random.SystemRandom()
PUBLISH = not os.environ.get("GM_NO_PUSH")   # GM_NO_PUSH=1 → local testing

KIND_BY_ROLE = {"Mafia": "shutter", "Doctor": "save", "Detective": "investigate"}


def parse_ts(s):
    """Parse an ISO timestamp (accepts trailing Z or +00:00). None if invalid."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def current_epoch(state):
    """The epoch namespaces a match. Every deal mints a fresh one; ballots
    and night actions from any other epoch are foreign objects and are
    never counted — even if match and cycle numbers collide (the
    ghost-replay bug: a partial reset re-used match 1 and stale ballots
    from the finished match were re-counted as live ones)."""
    if not state.get("epoch"):
        state["epoch"] = secrets.token_hex(4)
    return state["epoch"]


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
    paths = [p for p in ["gameplay/state.json", "gameplay/village",
                         "gameplay/deals", "gameplay/dossiers", GM_ROLES_FILE]
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

    # A state without an epoch (legacy arena) gets one immediately and
    # visibly, so stale ballots/night actions can never be re-counted.
    if not state.get("epoch"):
        current_epoch(state)
        write_state(state)
        commit_and_push(f"minted epoch {state['epoch']} for match {state['match']}")

    if phase == "setup":
        if MATCH_LIMIT and int(state.get("match") or 0) > MATCH_LIMIT:
            log(f"match limit {MATCH_LIMIT} reached — arena parked, no deal")
            state["phase"] = "halted"
            write_state(state)
            update_announcements(
                f"Match {MATCH_LIMIT} has ended. The arena rests — the "
                f"bazaar is closed until the operators open it again.")
            commit_and_push(f"arena parked: match limit {MATCH_LIMIT} reached")
            return
        log("phase=setup → dealing roles, opening cycle 1 discussion")
        # end_match() already bumped the number for the next match; only a
        # pristine reset (match=0) starts at 1. Never renumber mid-chain.
        state["match"] = max(1, int(state.get("match") or 0))
        state["cycle"] = 1
        state["epoch"] = secrets.token_hex(4)   # fresh namespace for the deal
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
            f"**Seats alive:** {', '.join(display_name(s) for s in state['alive'])}\n"
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
        if check_win_conditions():
            end_match()
            commit_and_push(f"match {state['match']} ended with recap after the vote")
            return
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
            f"**Seats alive:** {', '.join(display_name(s) for s in state['alive'])}\n"
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
        with open(f"gameplay/deals/{seat}.enc", "w") as f:
            f.write(sealed)

    save_role_registry(priv, assignment)
    log(f"dealt {len(living)} roles (dossiers sealed to seats, registry sealed to GM)")


# ------------------------------------------------------------------ votes ---
def tally_votes():
    state = read_state()
    epoch = current_epoch(state)
    seats = get_seats()
    dawn = parse_ts(state.get("clock", {}).get("dawn"))

    # Day votes are PUBLIC: votes/<seat>-c<CCC>.json = {"payload": {...}, "sig": ...}.
    # The payload is plaintext (the village sees every ballot and its stated
    # reason) and carries a detached Ed25519 signature made with the seat's
    # private signing key. The GM verifies it against the public key
    # registered in setup/seats.json — a ballot that is forged, stale, from
    # another epoch, or for another match/cycle is rejected, never counted.
    # Old sealed .enc ballots are history and are ignored.
    ballots = []
    rejected = 0
    if os.path.isdir("gameplay/votes"):
        for fn in sorted(os.listdir("gameplay/votes")):
            if not fn.endswith(".json"):
                continue
            try:
                with open(f"gameplay/votes/{fn}") as f:
                    envelope = json.load(f)
                payload = envelope.get("payload", {})
                seat = payload.get("seat")
                spk = seats.get(seat, {}).get("signing_public_key")
                if not spk:
                    raise ValueError(f"no signing key registered for {seat}")
                if not verify_payload(spk, payload, envelope.get("sig", "")):
                    raise ValueError("signature verification failed")
                if payload.get("epoch") != epoch:
                    raise ValueError("ballot from another epoch (ghost artifact)")
                if (payload.get("match") != state["match"]
                        or payload.get("cycle") != state["cycle"]):
                    raise ValueError("ballot for another match/cycle")
                if seat not in state["alive"]:
                    raise ValueError("ballot from a seat that has left the bazaar")
                ts = parse_ts(payload.get("ts"))
                if ts is None or (dawn and ts < dawn):
                    raise ValueError("stale ballot")
                target = payload.get("target")
                if target != "abstain" and target not in state["alive"]:
                    raise ValueError("target not alive")
                ballots.append((payload.get("ts", ""), seat, target,
                                payload.get("rationale", "")))
            except Exception as e:
                rejected += 1
                log(f"rejected ballot {fn}: {e}")
    else:
        log("no gameplay/votes/ directory")

    # Keep only the LATEST ballot per seat.
    latest = {}
    for _, seat, target, rationale in sorted(ballots, key=lambda b: b[0]):
        latest[seat] = (target, rationale)

    counts = Counter()
    for target, _ in latest.values():
        counts[target if target in state["alive"] else "abstain"] += 1
    log(f"tally: {dict(counts) or 'no votes'} ({rejected} rejected)")

    table = ["**Ballots cast this cycle (signed and public):**", "",
             "| Seat | Voted for | Reason |", "|---|---|---|"]
    for seat in sorted(latest):
        target, rationale = latest[seat]
        rationale = (rationale or "").replace("|", "/").replace("\n", " ")[:140]
        target_disp = target if target == "abstain" else display_name(target)
        table.append(f"| {display_name(seat)} | {target_disp} | {rationale} |")
    table_text = "\n".join(table)
    if rejected:
        table_text += ("\n\n(" + str(rejected) + " ballot(s) rejected: forged, stale, "
                       "or from another epoch — not counted.)")

    max_votes = max(counts.values()) if counts else 0
    top = [s for s, c in counts.items() if c == max_votes]
    banished = top[0] if max_votes > 0 and len(top) == 1 and top[0] != "abstain" else None

    if banished:
        state["alive"].remove(banished)
        role = load_role_registry(get_gm_private_key()).get(banished, "Unknown")
        update_graveyard(banished, seats[banished]["persona"], role, "Village vote")
        update_announcements(
            f"**Banishment!** {display_name(banished)}, "
            f"{persona_name(seats[banished]['persona'])}, "
            "has been banished from the bazaar.\n"
            f"Their role was: **{role}**.\n\n{table_text}"
        )
        log(f"banished {banished} (role revealed: {role})")
    else:
        update_announcements("No banishment this cycle (tie or no votes).\n\n" + table_text)
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
    for fn in sorted(os.listdir("gameplay/night")):
        if not fn.endswith(".enc"):
            continue
        try:
            with open(f"gameplay/night/{fn}") as f:
                a = decrypt_payload(priv, f.read().strip())
        except Exception as e:
            log(f"unreadable night action {fn}: {e}")
            continue
        if a.get("match") != state["match"] or a.get("cycle") != state["cycle"]:
            continue
        if a.get("epoch") != current_epoch(state):
            log(f"night action from {a.get('seat')} ignored (foreign epoch — ghost artifact)")
            continue
        ats = parse_ts(a.get("ts"))
        ndawn = parse_ts(state.get("clock", {}).get("dawn"))
        if ats is None or (ndawn and ats < ndawn):
            log(f"night action from {a.get('seat')} ignored (stale ts — ghost artifact)")
            continue
        seat, target = a.get("seat"), a.get("target")
        if seat not in state["alive"]:
            continue
        kind = KIND_BY_ROLE.get(registry.get(seat))
        if not kind:
            log(f"night action from {seat} ignored (no night role)")
            continue
        if target not in state["alive"]:
            log(f"night action from {seat} targets {target}, who has left the bazaar — ignored")
            continue
        actions.append((a.get("ts", ""), seat, kind, target))

    actions.sort(key=lambda x: x[0])
    latest = {}
    for ts, seat, kind, target in actions:
        latest[seat] = (kind, target)

    shutters, saves, investigates = [], [], []
    for seat, (kind, target) in latest.items():
        {"shutter": shutters, "save": saves, "investigate": investigates}[kind].append((seat, target))

    # Friendly fire is forbidden: the Family never shutters one of its
    # own. Shutter submissions targeting a fellow Mafioso (per the GM
    # registry — the bot's self-declared role is never trusted) are discarded.
    valid_shutters = []
    for seat, target in shutters:
        if registry.get(target) == "Mafia":
            log(f"shutter by {seat} targeting fellow Family member {target} — discarded")
            continue
        valid_shutters.append((seat, target))

    # Mafia shutter: majority target among valid submissions; ties are broken
    # securely at random, never by submission order.
    shutter_target = None
    if valid_shutters:
        sc = Counter(t for _, t in valid_shutters)
        top_count = max(sc.values())
        top_targets = [t for t, c in sc.items() if c == top_count]
        shutter_target = SECURE_RANDOM.choice(top_targets)

    if shutter_target and shutter_target not in {t for _, t in saves}:
        state["alive"].remove(shutter_target)
        role = registry.get(shutter_target, "Unknown")
        update_graveyard(shutter_target, seats[shutter_target]["persona"], role)
        update_announcements(
            f"**Stall shuttered!** {display_name(shutter_target)}, "
            f"{persona_name(seats[shutter_target]['persona'])}, "
            "shuttered their stall and left the bazaar overnight. "
            f"Their role was: **{role}**."
        )
        log(f"stall shuttered: {shutter_target} (role revealed: {role})")
    else:
        update_announcements("The night passed quietly.")
        log("no shutter (saved, or no Mafia action)")

    # Detective results go to the DETECTIVE — never to the investigated seat.
    for detective, target in investigates:
        result = "Family" if registry.get(target) == "Mafia" else "not Family"
        payload = {
            "match": state["match"], "cycle": state["cycle"],
            "kind": "investigation", "target": target, "result": result,
        }
        sealed = encrypt_for_seat(seats[detective]["public_key"], payload)
        fn = f"gameplay/dossiers/{detective}-c{state['cycle']:03d}-result.enc"
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

    with open(f"gameplay/village/match-{state["match"]:02d}-recap.md", "w") as f:
        f.write("# Match Recap\n\n**Full Reveal**\n\n")
        f.write("| Seat | Persona | Role | Stable |\n|---|---|---|---|\n")
        for seat in seats:
            stable = "North" if int(seat.split("-")[1]) <= 5 else "South"
            f.write(f"| {display_name(seat)} | {seats[seat]['persona']} | "
                    f"{registry.get(seat, 'Unknown')} | {stable} |\n")

    state["match"] += 1
    state["cycle"] = 0
    state["epoch"] = None             # the next deal mints a fresh epoch
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
        # Local/cron GMs must start from the arena's latest state; the
        # GitHub Action always had a fresh checkout, but a long-lived
        # cron clone would otherwise read stale state (e.g. missing
        # ballots pushed since the last tick) and act on it.
        r = subprocess.run(["git", "pull", "--rebase", "--autostash"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            log(f"startup pull failed: {r.stderr.strip()[:200]}")
            sys.exit(1)
        advance_phase()
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
