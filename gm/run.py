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
import argparse
import base64
import glob
import json
import logging
import os
import random
import secrets
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from crypto import (load_gm_private_key, decrypt_payload, encrypt_for_seat,
                   verify_payload, seal_chat, open_chat)
from last_words import ask_last_words
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

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Bazaar of Lies — Game Master")
parser.add_argument("--no-push", action="store_true",
                    help="Local testing: never push to the arena repo")
parser.add_argument("--force", action="store_true",
                    help="Override existing night results (use with caution)")
args = parser.parse_args()

# Dynamic events (triggered randomly at dawn)
EVENTS = {
    "market_crash": {
        "chance": 0.1,
        "description": "The bazaar's ledgers are in disarray! All votes this cycle are secret.",
        "effect": "secret_votes",
    },
    "festival": {
        "chance": 0.1,
        "description": "The bazaar is celebrating! No banishment this cycle.",
        "effect": "no_banishment",
    },
    "plague": {
        "chance": 0.1,
        "description": "A plague has struck the bazaar! One merchant is shuttered at night (non-Family).",
        "effect": "plague_shutter",
    },
}

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


def log(msg: str) -> None:
    """Log a message to stderr with a timestamp."""
    logger.info(msg)


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
    committed = False
    for attempt in range(1, attempts + 1):
        r = subprocess.run(["git", "pull", "--rebase", "--autostash"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            log(f"pull failed (attempt {attempt}): {r.stderr.strip()[:200]}")
            time.sleep(2 * attempt)
            continue
        if not committed:
            try:
                subprocess.run(["git", "add", *paths], check=True)
                c = subprocess.run(["git", "diff", "--cached", "--quiet"])
                if c.returncode == 0:
                    log(f"nothing to publish for: {label}")
                    return
                subprocess.run(["git", "commit", "-m", f"GM: {label}"],
                               check=True, capture_output=True, text=True)
                committed = True
            except subprocess.CalledProcessError as e:
                log(f"commit failed: {e}")
                return
            except Exception as e:
                log(f"commit error: {type(e).__name__}: {e}")
                return
        # The work is committed but possibly still unpushed — on a busy
        # branch the push may need several pull+push rounds, and the
        # staged-diff check above must not make us give up with the
        # commit stranded locally (that once lost the GM a whole night).
        try:
            p = subprocess.run(["git", "push"], capture_output=True, text=True, check=True)
            log(f"published: {label}")
            return
        except subprocess.CalledProcessError as e:
            log(f"push failed: {e}")
            return
        except Exception as e:
            log(f"push error: {type(e).__name__}: {e}")
            return
        log(f"push rejected (attempt {attempt}): {p.stderr.strip()[:200]}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"could not publish: {label}")


# ---------------------------------------------------------------- registry ---
def save_role_registry(priv, assignment, family_key, anonymous_cycle, historian):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "roles": assignment, 
        "family_key": family_key,
        "anonymous_cycle": anonymous_cycle,
        "historian": historian,
    }
    sealed = encrypt_for_seat(
        base64.b64encode(bytes(priv.public_key)).decode(), payload)
    with open(GM_ROLES_FILE, "w") as f:
        f.write(sealed)


def load_role_registry(priv):
    with open(GM_ROLES_FILE) as f:
        payload = decrypt_payload(priv, f.read().strip())
    return payload["roles"]


def load_registry_payload(priv):
    """The full registry payload — roles AND the family channel key
    (needed by the night packets and the truth archive)."""
    with open(GM_ROLES_FILE) as f:
        return decrypt_payload(priv, f.read().strip())


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
        commit_and_push(
            f"match {state['match']} dealt, cycle 1 discussion opens")

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
        publish_night_packets(state, get_gm_private_key())
        commit_and_push(f"cycle {state['cycle']} tally done, night falls")

    elif phase == "night":
        deadline = datetime.fromisoformat(state["clock"]["night_deadline"])
        if now < deadline:
            log(f"phase=night → waiting until {deadline.isoformat()}")
            return
        log("phase=night → resolving night actions")
        # Idempotency: a tick that crashed between resolving the night and
        # ending the match must not resolve it again (double announcements,
        # double results). Sealed dawn results for this cycle mean the
        # night is already done — skip straight to the reckoning unless --force is set.
        already = glob.glob(
            f"gameplay/dossiers/seat-*-c{state['cycle']:03d}-result.enc")
        if already and not args.force:
            log(f"night already resolved ({len(already)} dawn results sealed) — "
                f"proceeding to the reckoning (use --force to override)")
        else:
            if already and args.force:
                log(f"Overriding existing night results for cycle {state['cycle']}")
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
# Day-play styles, sealed into the dossier with the role. The power roles
# are the village's only information advantage, and two matches burned the
# Detective on cycle 1 for public heat with no result behind it — the style
# teaches the difference between pressure and exposure.
PLAYSTYLES = {
    "Detective": (
        "Your power is the dawn result, not your voice. Investigate every "
        "night; let the result decide your public pressure. Before your "
        "first result arrives, press quietly and by question, never by "
        "crusade — an investigator who accuses loudly with nothing behind "
        "it gets banished by day two. When a result finally points at "
        "Family, weigh the moment to claim: a claim is a move, the "
        "graveyard will one day test it, and the manifest permits it."
    ),
    "Doctor": (
        "Your protection is silent work: choose the merchant the village "
        "would miss most, never the same two nights running. A quiet night "
        "you caused is yours to claim or to conceal — weigh it like any "
        "move, and remember the Family is listening. Your survival IS the "
        "village's shield: stay out of the day's loudest heat, and trade "
        "accusations for steady, unremarkable reasoning."
    ),
    "Mafia": (
        "Your survival is the trade. Echo the village's own suspicions, "
        "feed pile-ons that never touch the Family, and never be the "
        "loudest accuser — loud accusers draw the village's fire first. "
        "The quiet merchant who agrees often and initiates rarely is the "
        "hardest to catch."
    ),
    "Villager": (
        "Your voice and your vote are all you have — spend them on named "
        "suspects with quoted evidence, not on the village's manners. "
        "An accusation you can date is worth ten you can only feel."
    ),
}


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

    # Assign Historian (random Villager) — told privately, via the dossier:
    # knowing who holds the quill would exclude them from the Family, so
    # the identity never appears in public state.
    villagers = [seat for seat in living if assignment[seat] == "Villager"]
    historian = SECURE_RANDOM.choice(villagers)

    # Anonymous statements: random cycle between 2-4 — a public game
    # parameter (every merchant must know to keep their statements
    # unsigned), so it lives in state.json, not the sealed registry.
    anonymous_cycle = SECURE_RANDOM.randint(2, 4)
    state["anonymous_cycle"] = anonymous_cycle
    write_state(state)

    for seat in living:
        dossier = {
            "role": assignment[seat],
            "teammates": ([s for s in living if assignment[s] == "Mafia" and s != seat]
                          if assignment[seat] == "Mafia" else []),
            # Every seat carries a channel key (uniform shape); the Family
            # share one, the rest hold random unusable ones.
            "night_channel_key": (mafia_key if assignment[seat] == "Mafia"
                                  else base64.b64encode(os.urandom(32)).decode()),
            "historian": seat == historian,
            # Day-play guidance, sealed with the role: two matches in a row
            # the village banished its own Detective on cycle 1 for pressing
            # publicly before any result existed. The power roles now receive
            # a survival style with the deal.
            "playstyle": PLAYSTYLES.get(assignment[seat], ""),
        }
        sealed = encrypt_for_seat(seats[seat]["public_key"], dossier)
        with open(f"gameplay/deals/{seat}.enc", "w") as f:
            f.write(sealed)

    save_decoy_ledger(set())          # fresh decoy ledger for the match
    save_role_registry(priv, assignment, mafia_key, anonymous_cycle, historian)
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
             "| Merchant | Voted for | Reason |", "|---|---|---|"]
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
        # Last words: the banished may address the village one final time —
        # the Family's parting words would only be misdirection, so the
        # Family departs silent.
        last_words = ask_last_words(banished, role) if role != "Mafia" else None
        update_graveyard(banished, seats[banished]["persona"], role, "Village vote",
                         last_words=last_words)
        update_announcements(
            f"**Banishment!** {display_name(banished)}, "
            f"{persona_name(seats[banished]['persona'])}, "
            "has been banished from the bazaar.\n"
            f"Their role was: **{role}**.\n\n{table_text}"
            + (f"\n\n**Last words of {display_name(banished)}:**\n{last_words}"
               if last_words else "")
        )
        log(f"banished {banished} (role revealed: {role})")
    else:
        update_announcements("No banishment this cycle (tie or no votes).\n\n" + table_text)
        log("no banishment")

    write_state(state)


# ------------------------------------------------------------------ night ---
def trigger_event(state: dict) -> Optional[str]:
    """Trigger a random dynamic event at dawn."""
    event = None
    for name, config in EVENTS.items():
        if random.random() < config["chance"]:
            event = name
            update_announcements(f"EVENT: {config['description']}")
            log(f"Event triggered: {name}")
            break
    return event


def resolve_night_actions():
    state = read_state()
    priv = get_gm_private_key()
    registry = load_role_registry(priv)
    seats = get_seats()
    
    # Trigger dynamic event at dawn
    event = trigger_event(state)
    state["event"] = event
    write_state(state)

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

    if event == "festival":
        # Festival: no banishment
        update_announcements("EVENT: Festival! No banishment this cycle.")
        log("Festival: no shutter")
    elif shutter_target and shutter_target not in {t for _, t in saves}:
        state["alive"].remove(shutter_target)
        role = registry.get(shutter_target, "Unknown")
        # Last words for the departed — the Family gets none (a silenced
        # voice cannot steer the village from the grave).
        last_words = ask_last_words(shutter_target, role) if role != "Mafia" else None
        update_graveyard(shutter_target, seats[shutter_target]["persona"], role,
                         last_words=last_words)
        update_announcements(
            f"**Stall shuttered!** {display_name(shutter_target)}, "
            f"{persona_name(seats[shutter_target]['persona'])}, "
            "shuttered their stall and left the bazaar overnight. "
            f"Their role was: **{role}**."
            + (f"\n\n**Last Words**: {last_words}" if last_words else "")
        )
        log(f"stall shuttered: {shutter_target} (role revealed: {role})")
    else:
        update_announcements("The night passed quietly.")
        log("no shutter (saved, or no Mafia action)")

    # Results at dawn, uniform in presence: every living seat receives a
    # result file; only the Detective's carries the investigation — the
    # tree cannot reveal who receives results.
    detective_target = investigates[-1] if investigates else None
    if detective_target:
        result = ("Family" if registry.get(detective_target[1]) == "Mafia"
                  else "not Family")
        log(f"investigation result sealed to {detective_target[0]} "
            f"about {detective_target[1]}")
    publish_quiet_results(state, priv,
                         detective=(detective_target[0] if detective_target
                                    else None),
                         target=(detective_target[1] if detective_target
                                 else None),
                         result=(result if detective_target else None))

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


# ------------------------------------------------ night chat decoys ------
# Plausible council-flavored lines for the decoy chat blobs the GM mints
# for the non-Family seats: every file in the night channel decrypts
# under the family key, so a snoop holding the key sees ten council
# voices and cannot tell which three are the Family. In-theme, family-
# friendly vocabulary; the {merchant} slot is filled with the CURRENT
# target's name at mint time — trades may rotate between matches, so
# the pool never hardcodes them. The register matches the real
# council's plain speech (the Plain Speech Act): decoys must never
# stand out by style.
def plain_speech_block():
    """The bazaar's plain-speech norm, in every prompt: the theme is the
    setting, not the argument. Calibrated after two matches showed the
    register amplifying itself (five seats reciting the same metaphor by
    cycle 2) until the reasoning drowned in imagery."""
    return (
        "Style: argue in plain speech. The bazaar is your setting, not your argument — "
        "at most one brief metaphor per statement, and your case must stand on "
        "exact quotes, votes, and observed actions, never on imagery.\n\n"
    )

# ------------------------------------------------ night chat decoys ------
# Plausible council-flavored lines for the decoy chat blobs the GM mints
# for every non-Family seat. The register matches the real council's
# plain speech (the Plain Speech Act): decoys must never read as
# flowery exceptions. Talk lines are ASSEMBLED from opener x pivot pools
# (10 x 10 = 100 surfaces, deterministically rotated) and declare/assent
# draw from 10-line pools with a stride-7 rotation: no two seats share
# a line within a cycle, and no line repeats for the same seat inside
# ten cycles — a key-holding snoop correlating cycles cannot classify
# decoys by an exact repeated line (the match-3 hole: the same template
# in consecutive cycles, only the merchant slot swapped).
_DECOY_OPENERS = [
    "I propose we watch {merchant}:",
    "Keep one eye on {merchant}:",
    "The quiet ones merit a longer look tonight, and {merchant} leads them:",
    "I say {merchant} knows more than their ledger admits:",
    "Watch the hands, not the stall; {merchant} was busy when the vote needed names:",
    "Note it for the record — {merchant}:",
    "If {merchant} is plain, the bazaar is plain:",
    "{merchant} asks after everyone and answers for no one:",
    "{merchant} measured their wares twice and their words not once:",
    "The lantern light fell on {merchant} twice at the count:",
]

_DECOY_PIVOTS = [
    "their questions today burned brighter than their answers.",
    "they have dodged a plain question twice.",
    "their ledger grew tidy exactly when it should not.",
    "their words agree with whoever spoke last.",
    "their arithmetic at dinner did not match their morning talk.",
    "silence at dinner has a price, and they are paying in small coins.",
    "they were first to name a lean and last to give a reason.",
    "the scale tilts oddly whenever their wares are counted.",
    "they quote the Compact but have never walked it.",
    "their story today does not fit the one from yesterday.",
]

DECOY_POOLS = {
    "declare": [
        "I declare that we watch {merchant} before we sleep.",
        "Let the record show my lean: {merchant}'s votes have wobbled since the second bell.",
        "My declaration stands where it stood: {merchant} first, the rest can wait.",
        "I declare a lean toward {merchant} and a reason with a date attached.",
        "The count needs a name, so here is mine: {merchant}, for the ledger's sake.",
        "Declared plainly and dated: {merchant} — let them answer in the morning.",
        "My lean is {merchant}; my reason is already on the record.",
        "I declare {merchant} — not from silence, but from the shape of their answers.",
        "The declaration is {merchant}, and I will own it at the count.",
        "So declared: watch {merchant}, weigh the ledger, and let the morning judge.",
        "I declare {merchant} for the watch; their stall keeps odd hours.",
        "On my oath as a trader: the lean is {merchant}, and the date is today.",
        "{merchant} carries my declaration tonight; the ledger may check it.",
        "The lean I declare is {merchant}, and I will stand behind it at the count.",
        "Declared and dated: {merchant} — the arithmetic of their answers is wrong.",
    ],
    "assent": [
        "Agreed — the watch closes on {merchant} and the lamps burn low.",
        "So it stands; the count holds, and {merchant} keeps the watch.",
        "The count stands on {merchant}; the day is decided.",
        "Agreed and sealed — {merchant} it is, and the kettle cools.",
        "So we hold together; the lean carries on {merchant} and the ledger is written.",
        "Agreed — and may the morning prove the count right about {merchant}.",
        "The assent is given; the watch is set on {merchant} and the lamps are trimmed.",
        "It stands as counted, {merchant} and no quibble from this stall.",
        "Agreed; the choice is {merchant} and the tea is poured.",
        "Sealed — the watch agrees on {merchant} and the bazaar keeps its counsel.",
        "So it stands: {merchant} bears the watch, and I bear my share of it.",
        "Agreed — the lamps dim on {merchant} and the count holds.",
        "The count carries {merchant}; this stall stands behind it.",
        "Sealed and dated: the watch falls to {merchant} tonight.",
        "Agreed; {merchant} keeps the watch and the rest of us keep the count.",
    ],
}


def decoy_text(kind, seat_n, match, cycle, watch, target_name):
    """One decoy line for a seat/watch, chosen by deterministic rotation.
    The match number rides the rotation too: old matches' night files live
    in git history, so a snoop correlating ACROSS matches must not find
    the same line for the same cycle either."""
    m = match or 0
    if kind == "talk":
        o = _DECOY_OPENERS[(m * 13 + cycle * 7 + seat_n + watch - 1) % len(_DECOY_OPENERS)]
        p = _DECOY_PIVOTS[(m * 9 + cycle * 11 + seat_n * 3 + watch * 7) % len(_DECOY_PIVOTS)]
        return o.format(merchant=target_name) + " " + p
    pool = DECOY_POOLS[kind]
    return pool[(m * 13 + cycle * 7 + seat_n + watch - 1) % len(pool)].format(
        merchant=target_name)


def mint_decoys(family_key, seat, match, cycle, living, sr, used=None):
    """Three chat blobs for one non-Family seat — one per watch, sealed
    with the FAMILY key so every file in the channel decrypts alike.
    Lines come from decoy_text's rotation; the target merchant is the
    random element (the register must stay plausible). `used` is the
    match's decoy ledger: a line that has already been minted is redrawn
    (new rotation index, then a new target) so no decoy line ever
    repeats — repetition across cycles was the snoop's classification
    attack."""
    used = used if used is not None else set()
    seat_n = int(seat.split("-")[-1])
    decoys = []
    for watch, kind in ((1, "talk"), (2, "declare"), (3, "assent")):
        targets = [s for s in living if s != seat]
        bump = 0
        while True:
            w = watch + bump
            target = (sr.choice(targets) if bump == 0 else
                      targets[(seat_n + cycle * 3 + bump * 5) % len(targets)])
            line = decoy_text(kind, seat_n, match, cycle, w, display_name(target))
            if line not in used or bump > 64:
                break
            bump += 1
        used.add(line)
        decoys.append(seal_chat(family_key, {
            "kind": kind, "watch": watch, "cycle": cycle, "seat": seat,
            "text": line,
            "target": target,
            "ts": datetime.now(timezone.utc).isoformat()}))
    return decoys


DECOY_LEDGER = "gm/decoys-used.json"     # GM-local (gitignored): every line
                                         # already minted this match — a line
                                         # is a decoy's fingerprint, so the
                                         # same line may never appear twice.


def load_decoy_ledger():
    try:
        with open(DECOY_LEDGER) as f:
            return set(json.load(f))
    except (OSError, json.JSONDecodeError):
        return set()


def save_decoy_ledger(used):
    with open(DECOY_LEDGER, "w") as f:
        json.dump(sorted(used), f, ensure_ascii=False)


def publish_night_packets(state, priv):
    """At nightfall: one sealed packet per living seat, uniform in
    presence and name. Non-Family seats receive their three decoy chat
    blobs (posted verbatim during the watches); the Family receive an
    acknowledgement. The Detective-leak and night-role-set leak both
    die here: every seat has a packet, every night. No decoy line is
    ever minted twice in a match (the ledger guards the rotation)."""
    payload = load_registry_payload(priv)
    family_key = payload.get("family_key")
    roles = payload["roles"]
    seats = get_seats()
    used = load_decoy_ledger()
    for seat in state["alive"]:
        body = {"kind": "night_packet", "match": state["match"],
                "cycle": state["cycle"], "seat": seat}
        if roles.get(seat) != "Mafia" and family_key:
            body["chat"] = mint_decoys(family_key, seat, state["match"],
                                       state["cycle"], list(state["alive"]),
                                       SECURE_RANDOM, used)
        sealed = encrypt_for_seat(seats[seat]["public_key"], body)
        with open(f"gameplay/dossiers/{seat}-c{state['cycle']:03d}-night.enc",
                  "w") as f:
            f.write(sealed)
    save_decoy_ledger(used)
    log(f"night packets sealed to all {len(state['alive'])} living seats")


def publish_quiet_results(state, priv, detective=None, target=None, result=None):
    """At dawn: one result file per living seat. The Detective's carries
    the investigation; everyone else's carries quiet — the tree cannot
    reveal who receives results."""
    seats = get_seats()
    for seat in state["alive"]:
        if detective and seat == detective:
            body = {"match": state["match"], "cycle": state["cycle"],
                    "kind": "investigation", "target": target,
                    "result": result}
        else:
            body = {"kind": "quiet", "cycle": state["cycle"]}
        sealed = encrypt_for_seat(seats[seat]["public_key"], body)
        with open(f"gameplay/dossiers/{seat}-c{state['cycle']:03d}-result.enc",
                  "w") as f:
            f.write(sealed)
    log(f"night results sealed to all {len(state['alive'])} living seats")


def write_truth_archive(state, registry, priv):
    """The post-match truth file (gameplay/village/match-XX-truth.md):
    the role registry and every sealed night action, decrypted — the
    authoritative record for the Elder Council, written before the next
    deal overwrites gm/roles.enc."""
    lines = ["# Truth Archive\n",
             f"**Match {state['match']}** — the full record, secrecy lifted.\n",
             "\n## Roles\n",
             "| Seat | Role |", "|---|---|"]
    for seat in sorted(registry):
        lines.append(f"| {display_name(seat)} | {registry.get(seat, 'Unknown')} |")
    lines.append("\n## Night actions (sealed at the time, open now)\n")
    for fn in sorted(os.listdir("gameplay/night")):
        if not fn.endswith(".enc"):
            continue
        try:
            with open(f"gameplay/night/{fn}") as f:
                a = decrypt_payload(priv, f.read().strip())
        except Exception as e:
            lines.append(f"- {fn}: unreadable ({e})")
            continue
        role = a.get("role") or "no night role"
        target = a.get("target")
        lines.append(f"- cycle {a.get('cycle')}: {display_name(a.get('seat'))} "
                     f"({role}) "
                     + (f"targeted {display_name(target)}" if target
                        else "(asleep — no target)"))

    # The Family's candlelight council, decrypted for the historians:
    # every chat file opens under the family key (decoys included — the
    # GM minted them with it); the registry labels which voices were real.
    try:
        payload = load_registry_payload(priv)
        family_key = payload.get("family_key")
        roles = payload["roles"]
    except Exception:
        family_key, roles = None, {}
    if family_key:
        lines.append("\n## The Family's candlelight council\n")
        import glob as globmod
        chat_files = sorted(globmod.glob("gameplay/night/chat/c*-w*-seat-*.enc"))
        for fn in chat_files:
            try:
                with open(fn) as f:
                    m = open_chat(family_key, f.read().strip())
            except OSError:
                continue
            if not m:
                continue
            seat = m.get("seat")
            voice = ("REAL" if roles.get(seat) == "Mafia" else "decoy")
            lines.append(f"- cycle {m.get('cycle')} watch {m.get('watch')} "
                         f"{display_name(seat)} [{voice}, {m.get('kind')}]: "
                         f"{m.get('text', '')}"
                         + (f" → {display_name(m.get('target'))}"
                            if m.get("target") else ""))
    with open(f"gameplay/village/match-{state['match']:02d}-truth.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    log(f"truth archive written for match {state['match']}")


def run_elder_council(match_no):
    """The Elder Council convenes itself when the match concludes: the
    judgment (src/elder-council.py, evidence from the just-written truth
    archive) plus the pressed PDF (src/elder-press.py), both committed.
    Best-effort by design — a failed judgment must never break the deal
    chain or the arena parking. Kill switch: BAZAAR_AUTO_COUNCIL=0."""
    if os.environ.get("BAZAAR_AUTO_COUNCIL", "1") == "0":
        log("auto council disabled (BAZAAR_AUTO_COUNCIL=0)")
        return
    try:
        r = subprocess.run(
            [sys.executable, "src/elder-council.py", "--match", str(match_no)],
            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            log(f"elder council failed: {(r.stderr or '').strip()[:200]}")
            return
        judgment = f"gameplay/village/match-{match_no:02d}-judgment.md"
        if not os.path.exists(judgment):
            log("elder council wrote no judgment")
            return
        commit_and_push([judgment], f"Elder Council judgment for match {match_no:02d}")
        pr = subprocess.run([sys.executable, "src/elder-press.py", judgment],
                            capture_output=True, text=True, timeout=600)
        pdf = f"gameplay/library/match-{match_no:02d}-judgment.pdf"
        if pr.returncode == 0 and os.path.exists(pdf):
            commit_and_push([pdf], f"Elder press: match {match_no:02d} judgment")
        else:
            log(f"elder press failed: {(pr.stderr or '').strip()[:200]}")
        log("elder council concluded: judgment written and pressed")
    except Exception as e:
        log(f"elder council error (the match record is safe): "
            f"{type(e).__name__}: {e}")


def end_match():
    priv = get_gm_private_key()
    state = read_state()
    registry = load_role_registry(priv)
    seats = get_seats()

    with open(f"gameplay/village/match-{state["match"]:02d}-recap.md", "w") as f:
        f.write("# Match Recap\n\n**Full Reveal**\n\n")
        f.write("| Seat | Persona | Role | Stable |\n|---|---|---|---|\n")
        for seat in seats:
            stable = "North" if int(seat.split("-")[1]) <= 5 else "South"
            f.write(f"| {display_name(seat)} | {seats[seat]['persona']} | "
                    f"{registry.get(seat, 'Unknown')} | {stable} |\n")

    # The truth archive: secrecy is over. Preserve the authoritative record
    # before the next deal overwrites gm/roles.enc — the Elder Council
    # judges from this, not from prose paraphrase.
    write_truth_archive(state, registry, priv)

    # The Council convenes while the truth archive is fresh — before the
    # counter bump, so the judgment lands in this match's record.
    run_elder_council(state["match"])

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
        try:
            r = subprocess.run(["git", "pull", "--rebase", "--autostash"],
                               capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            log(f"startup pull failed: {e.stderr.strip()[:200]}")
            sys.exit(1)
        except Exception as e:
            log(f"startup pull error: {type(e).__name__}: {e}")
            sys.exit(1)
        advance_phase()
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
