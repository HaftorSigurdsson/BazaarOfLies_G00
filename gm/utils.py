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