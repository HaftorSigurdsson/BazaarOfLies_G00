import base64
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from crypto import load_gm_private_key, decrypt_payload, encrypt_for_seat
from utils import (
    read_state, write_state, update_announcements, update_graveyard,
    get_seats, is_alive, get_living_seats
)


def advance_phase() -> None:
    """Advance the game phase based on the current state."""
    state = read_state()
    now = datetime.now(timezone.utc)
    
    if state["phase"] == "setup":
        # Initialize the first match
        state["match"] = 1
        state["cycle"] = 1
        state["phase"] = "dawn"
        state["clock"] = {
            "dawn": now.isoformat(),
            "discussion_deadline": (now + timedelta(minutes=5)).isoformat(),  # 5 min for testing
            "voting_deadline": None,
            "night_deadline": None
        }
        write_state(state)
        update_announcements(
            f"**Match {state['match']}, Cycle {state['cycle']}**\n"
            "The bazaar awakens! Roles have been dealt.\n"
            f"**Seats alive:** {', '.join(state['alive'])}\n"
            f"**Discussion ends at:** {state['clock']['discussion_deadline']}"
        )
        deal_roles()
        
    elif state["phase"] == "discussion":
        if now >= datetime.fromisoformat(state["clock"]["discussion_deadline"]):
            state["phase"] = "voting"
            state["clock"]["voting_deadline"] = (now + timedelta(minutes=2)).isoformat()  # 2 min for testing
            write_state(state)
            update_announcements(
                f"**Match {state['match']}, Cycle {state['cycle']}**\n"
                "The discussion ends. The bazaar votes!\n"
                f"**Voting ends at:** {state['clock']['voting_deadline']}"
            )
            
    elif state["phase"] == "voting":
        if now >= datetime.fromisoformat(state["clock"]["voting_deadline"]):
            tally_votes()
            state = read_state()  # Refresh after tally
            state["phase"] = "night"
            state["clock"]["night_deadline"] = (now + timedelta(minutes=2)).isoformat()  # 2 min for testing
            write_state(state)
            update_announcements(
                f"**Match {state['match']}, Cycle {state['cycle']}**\n"
                "The sun sets. The bazaar sleeps. Night actions begin!\n"
                f"**Night ends at:** {state['clock']['night_deadline']}"
            )
            
    elif state["phase"] == "night":
        if now >= datetime.fromisoformat(state["clock"]["night_deadline"]):
            resolve_night_actions()
            state = read_state()  # Refresh after night resolution
            
            # Check win conditions
            if check_win_conditions():
                end_match()
            else:
                state["cycle"] += 1
                state["phase"] = "dawn"
                state["clock"] = {
                    "dawn": now.isoformat(),
                    "discussion_deadline": (now + timedelta(minutes=5)).isoformat(),
                    "voting_deadline": None,
                    "night_deadline": None
                }
                write_state(state)
                update_announcements(
                    f"**Match {state['match']}, Cycle {state['cycle']}**\n"
                    "The bazaar awakens!\n"
                    f"**Seats alive:** {', '.join(state['alive'])}\n"
                    f"**Discussion ends at:** {state['clock']['discussion_deadline']}"
                )


def deal_roles() -> None:
    """Deal roles for the current match and encrypt dossiers. Adjust roles based on the previous match's outcome."""
    state = read_state()
    seats = get_seats()
    living_seats = state["alive"]
    
    # Check previous match outcome to adjust roles
    previous_match = state.get("previous_match_outcome", {})
    mafia_count = 3
    if previous_match.get("mafia_win", False):
        # Reduce Mafia count if they won too easily
        mafia_count = max(2, mafia_count - 1)
    elif previous_match.get("town_win", False) and previous_match.get("cycles", 0) <= 3:
        # Increase Mafia count if Town won too quickly
        mafia_count = min(4, mafia_count + 1)
    
    # Classic roles: Mafia, Detective, Doctor, Villagers
    roles = ["Mafia"] * mafia_count + ["Detective", "Doctor"] + ["Villager"] * (len(living_seats) - mafia_count - 2)
    import random
    random.shuffle(roles)
    
    # Assign roles to seats (ensure at least one Mafia per stable)
    north_mafia = 0
    south_mafia = 0
    role_assignment = {}
    
    for i, seat in enumerate(living_seats):
        role = roles[i]
        role_assignment[seat] = role
        if role == "Mafia":
            if int(seat.split("-")[1]) <= 5:
                north_mafia += 1
            else:
                south_mafia += 1
    
    # Ensure at least one Mafia per stable (reassign if needed)
    if north_mafia == 0 or south_mafia == 0:
        for seat in living_seats:
            if role_assignment[seat] == "Mafia":
                if north_mafia == 0 and int(seat.split("-")[1]) > 5:
                    # Reassign a South Mafia to North
                    role_assignment[seat] = "Villager"
                    for s in [s for s in living_seats if int(s.split("-")[1]) <= 5]:
                        if role_assignment[s] == "Villager":
                            role_assignment[s] = "Mafia"
                            break
                elif south_mafia == 0 and int(seat.split("-")[1]) <= 5:
                    # Reassign a North Mafia to South
                    role_assignment[seat] = "Villager"
                    for s in [s for s in living_seats if int(s.split("-")[1]) > 5]:
                        if role_assignment[s] == "Villager":
                            role_assignment[s] = "Mafia"
                            break
    
    # Assign power roles (Detective/Doctor) to opposite stables
    power_roles = ["Detective", "Doctor"]
    random.shuffle(power_roles)
    north_power = power_roles[0]
    south_power = power_roles[1]
    
    for seat in living_seats:
        if int(seat.split("-")[1]) <= 5 and role_assignment[seat] in ["Detective", "Doctor"]:
            role_assignment[seat] = north_power
        elif int(seat.split("-")[1]) > 5 and role_assignment[seat] in ["Detective", "Doctor"]:
            role_assignment[seat] = south_power
    
    # Generate Mafia night channel key
    mafia_key = base64.b64encode(os.urandom(32)).decode()
    
    # Encrypt dossiers for each seat
    for seat in living_seats:
        role = role_assignment[seat]
        dossier = {
            "role": role,
            "teammates": [s for s in living_seats if role_assignment[s] == role and s != seat] if role == "Mafia" else [],
            "night_channel_key": mafia_key if role == "Mafia" else None
        }
        public_key = seats[seat]["public_key"]
        encrypted_dossier = encrypt_for_seat(public_key, dossier)
        with open(f"deals/{seat}.enc", "w") as f:
            f.write(encrypted_dossier)


def tally_votes() -> None:
    """Tally votes and banish the plurality target. Apply penalties for silent bots."""
    state = read_state()
    gm_private_key = load_gm_private_key(os.environ["GM_PRIVATE_KEY"])
    votes_dir = "votes/"
    vote_counts = {seat: 0 for seat in state["alive"]}
    vote_counts["abstain"] = 0
    
    # Track silent bots (no statements for 2 consecutive days)
    silent_bots = get_silent_bots(state)
    for bot in silent_bots:
        update_announcements(f"**Penalty!** {bot} has been silent for 2 days and receives an automatic vote.")
        vote_counts[bot] = 1  # Auto-vote for silent bots
    
    for filename in os.listdir(votes_dir):
        if filename.endswith(".enc"):
            with open(votes_dir + filename, "r") as f:
                encrypted_vote = f.read()
            try:
                vote = decrypt_payload(gm_private_key, encrypted_vote)
                if vote["match"] == state["match"] and vote["cycle"] == state["cycle"]:
                    if vote["vote"] in vote_counts:
                        vote_counts[vote["vote"]] += 1
                    else:
                        vote_counts["abstain"] += 1
            except:
                continue
    
    # Determine the banished seat
    max_votes = max(vote_counts.values())
    candidates = [seat for seat, count in vote_counts.items() if count == max_votes]
    banished = random.choice(candidates) if len(candidates) == 1 else None
    
    if banished and banished != "abstain":
        state["alive"].remove(banished)
        seats = get_seats()
        persona = seats[banished]["persona"]
        role = "Unknown"  # Role is flipped publicly after banishment
        update_graveyard(banished, persona, role, "Village vote")
        update_announcements(
            f"**Banishment!** {banished} ({persona}) has been banished from the bazaar.\n"
            f"Their role was: **{role}**."
        )
    else:
        update_announcements("No banishment this cycle (tie or abstentions).")
    
    write_state(state)


def resolve_night_actions() -> None:
    """Resolve night actions (Mafia kill, Detective investigate, Doctor save)."""
    state = read_state()
    gm_private_key = load_gm_private_key(os.environ["GM_PRIVATE_KEY"])
    night_dir = "night/"
    kill_target = None
    save_target = None
    investigate_target = None
    
    # Read night actions
    for filename in os.listdir(night_dir):
        if filename.endswith(".enc"):
            with open(night_dir + filename, "r") as f:
                encrypted_action = f.read()
            try:
                action = decrypt_payload(gm_private_key, encrypted_action)
                if action["match"] == state["match"] and action["cycle"] == state["cycle"]:
                    if action["type"] == "kill" and is_alive(action["seat"]) and action["seat"] in [s for s in state["alive"] if get_seats()[s]["role"] == "Mafia"]:
                        kill_target = action["target"]
                    elif action["type"] == "save" and is_alive(action["seat"]) and get_seats()[action["seat"]]["role"] == "Doctor":
                        save_target = action["target"]
                    elif action["type"] == "investigate" and is_alive(action["seat"]) and get_seats()[action["seat"]]["role"] == "Detective":
                        investigate_target = action["target"]
            except:
                continue
    
    # Resolve kill/save
    if kill_target and kill_target != save_target:
        state["alive"].remove(kill_target)
        seats = get_seats()
        persona = seats[kill_target]["persona"]
        role = "Unknown"  # Role is flipped publicly after night kill
        update_graveyard(kill_target, persona, role)
        update_announcements(f"**Night kill!** {kill_target} ({persona}) was found dead in the bazaar.")
    else:
        update_announcements("The night passed quietly.")
    
    # Resolve Detective investigation
    if investigate_target:
        seats = get_seats()
        role = seats[investigate_target]["role"]
        result = "Family" if role == "Mafia" else "not Family"
        dossier = {"result": result}
        public_key = seats[investigate_target]["public_key"]
        encrypted_dossier = encrypt_for_seat(public_key, dossier)
        os.makedirs(f"dossiers/{investigate_target}", exist_ok=True)
        with open(f"dossiers/{investigate_target}/investigation.enc", "w") as f:
            f.write(encrypted_dossier)
    
    write_state(state)


def check_win_conditions() -> bool:
    """Check if a faction has won. Returns True if the match ends."""
    state = read_state()
    seats = get_seats()
    living_seats = state["alive"]
    mafia_count = 0
    town_count = 0
    
    for seat in living_seats:
        role = seats[seat]["role"]
        if role == "Mafia":
            mafia_count += 1
        else:
            town_count += 1
    
    if mafia_count == 0:
        update_announcements("The Town has won! All Mafiosi have been banished.")
        return True
    elif mafia_count >= town_count:
        update_announcements("The Family has won! They outnumber the Town.")
        return True
    return False


def end_match() -> None:
    """End the current match and prepare for the next."""
    state = read_state()
    seats = get_seats()
    
    # Publish full reveal
    with open(f"village/match-{state['match']:02d}-recap.md", "w") as f:
        f.write("# Match Recap\n\n")
        f.write("**Full Reveal**\n\n")
        f.write("| Seat | Persona | Role | Stable |\n")
        f.write("|---|---|---|---|\n")
        for seat in seats:
            role = seats[seat]["role"]
            stable = "North" if int(seat.split("-")[1]) <= 5 else "South"
            f.write(f"| {seat} | {seats[seat]['persona']} | {role} | {stable} |\n")
        
        # Calculate scores (simplified)
        f.write("\n**Scores**\n\n")
        f.write("| Stable | Points |\n")
        f.write("|---|---|\n")
        f.write("| North | 0 |\n")
        f.write("| South | 0 |\n")
    
    # Reset for next match
    state["match"] += 1
    state["cycle"] = 0
    state["phase"] = "setup"
    state["alive"] = list(seats.keys())
    state["graveyard"] = {}
    write_state(state)
    
    update_announcements(
        f"Match {state['match'] - 1} has ended. The bazaar prepares for Match {state['match']}."
    )


def enforce_token_budget(seat: str, tokens_used: int) -> bool:
    """Enforce the 10,000-token limit per bot per cycle."""
    usage_file = f"usage/{seat}.jsonl"
    if not os.path.exists(usage_file):
        return True
    
    total_tokens = 0
    with open(usage_file, "r") as f:
        for line in f:
            data = json.loads(line)
            if data.get("cycle", 0) == read_state()["cycle"]:
                total_tokens += data["tokens"]
    
    return total_tokens + tokens_used <= 10000


def get_silent_bots(state: dict) -> List[str]:
    """Identify bots that have been silent for 2 consecutive days."""
    silent_bots = []
    for seat in state["alive"]:
        statements = get_statements_for_seat(seat, state["cycle"] - 1) + get_statements_for_seat(seat, state["cycle"] - 2)
        if not statements:
            silent_bots.append(seat)
    return silent_bots


def get_statements_for_seat(seat: str, cycle: int) -> List[str]:
    """Get public statements for a seat in a given cycle."""
    statements = []
    try:
        with open(f"village/day-{cycle:03d}.jsonl", "r") as f:
            for line in f:
                data = json.loads(line)
                if data["seat"] == seat:
                    statements.append(data["text"])
    except FileNotFoundError:
        pass
    return statements


if __name__ == "__main__":
    from datetime import timedelta
    advance_phase()