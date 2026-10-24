import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional


def read_state() -> dict:
    """Read the current game state from state.json."""
    with open("gameplay/state.json", "r") as f:
        return json.load(f)


def write_state(state: dict) -> None:
    """Write the game state to state.json."""
    with open("gameplay/state.json", "w") as f:
        json.dump(state, f, indent=2)


def update_announcements(message: str) -> None:
    """Append a message to village/announcements.md."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    announcement = f"**{timestamp}**\n{message}\n\n---\n"
    with open("gameplay/village/announcements.md", "a") as f:
        f.write(announcement)


_PERSONA_NAME_RE = re.compile(r"^[Yy]ou are ([^.,;]+)")


def persona_name(persona: str) -> str:
    """Short merchant name from a persona prompt.

    'You are The Carpet Weaver. You see the pattern...' → 'The Carpet Weaver'.
    Never dump whole persona paragraphs into announcements or the graveyard.
    """
    m = _PERSONA_NAME_RE.match(persona or "")
    if m:
        return m.group(1).strip()
    return (persona or "").strip()[:24] or "Unknown merchant"


GRAVEYARD_TEMPLATE = """# Bazaar Graveyard

| Match | Cycle | Seat | Persona | Role | Banished By |
|---|---|---|---|---|---|
"""


def update_graveyard(seat: str, persona: str, role: str,
                     banished_by: Optional[str] = None) -> None:
    """Add a seat to the graveyard in village/graveyard.md.

    The row is inserted directly under the table header (not appended at the
    end of the file, which lands after any later sections and used to mangle
    the markdown). The persona column holds the short name only.
    """
    state = read_state()
    line = (f"| {state['match']} | {state['cycle']} | {seat} | "
            f"{persona_name(persona)} | {role} | {banished_by or 'Night kill'} |")
    path = "gameplay/village/graveyard.md"
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(GRAVEYARD_TEMPLATE)
    with open(path) as f:
        lines = f.read().splitlines()
    idx = next((i for i, l in enumerate(lines) if l.startswith("|---")), None)
    insert_at = idx + 1 if idx is not None else len(lines)
    lines.insert(insert_at, line)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


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
