import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


def read_state() -> dict:
    """Read the current game state from state.json."""
    with open("state.json", "r") as f:
        return json.load(f)


def write_state(state: dict) -> None:
    """Write the game state to state.json."""
    with open("state.json", "w") as f:
        json.dump(state, f, indent=2)


def update_announcements(message: str) -> None:
    """Append a message to village/announcements.md."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    announcement = f"**{timestamp}**\n{message}\n\n---\n"
    with open("village/announcements.md", "a") as f:
        f.write(announcement)


def update_graveyard(seat: str, persona: str, role: str, banished_by: Optional[str] = None) -> None:
    """Add a seat to the graveyard in village/graveyard.md."""
    match = read_state()["match"]
    cycle = read_state()["cycle"]
    line = f"| {match} | {cycle} | {seat} | {persona} | {role} | {banished_by or 'Night kill'} |".strip()
    with open("village/graveyard.md", "a") as f:
        f.write(f"{line}\n")


def get_seats() -> Dict[str, dict]:
    """Load seat data from setup/seats.json."""
    with open("setup/seats.json", "r") as f:
        return json.load(f)["seats"]


def is_alive(seat: str) -> bool:
    """Check if a seat is alive."""
    return seat in read_state()["alive"]


def get_living_seats() -> List[str]:
    """Get a list of living seats."""
    return read_state()["alive"]


def enforce_token_budget() -> None:
    """Enforce the 10,000-token limit per bot per cycle."""
    state = read_state()
    for seat in get_seats():
        usage_file = f"usage/{seat}.jsonl"
        if not os.path.exists(usage_file):
            continue
        
        total_tokens = 0
        with open(usage_file, "r") as f:
            for line in f:
                data = json.loads(line)
                if data.get("cycle", 0) == state["cycle"]:
                    total_tokens += data["tokens"]
        
        if total_tokens > 10000:
            update_announcements(f"**Penalty!** {seat} exceeded the 10,000-token limit and is silenced this cycle.")
            void_bot_actions(seat, state["cycle"])


def void_bot_actions(seat: str, cycle: int) -> None:
    """Void a bot's statements and votes for a cycle."""
    # Remove statements from village/day-XXX.jsonl
    try:
        with open(f"village/day-{cycle:03d}.jsonl", "r") as f:
            lines = f.readlines()
        with open(f"village/day-{cycle:03d}.jsonl", "w") as f:
            for line in lines:
                data = json.loads(line)
                if data["seat"] != seat:
                    f.write(line)
    except FileNotFoundError:
        pass
    
    # Remove votes from votes/
    for filename in os.listdir("votes/"):
        if filename.endswith(".enc"):
            try:
                with open(f"votes/{filename}", "r") as f:
                    vote = json.loads(decrypt_payload(load_gm_private_key(os.environ["GM_PRIVATE_KEY"]), f.read()))
                if vote["seat"] == seat and vote["cycle"] == cycle:
                    os.remove(f"votes/{filename}")
            except:
                continue


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce-token-budget", action="store_true", help="Enforce token budget for all bots")
    args = parser.parse_args()
    
    if args.enforce_token_budget:
        enforce_token_budget()