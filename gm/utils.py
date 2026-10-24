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
    line = (f"| {state['match']} | {state['cycle']} | {display_name(seat)} | "
            f"{persona_name(persona)} | {role} | {banished_by or 'Stall shuttered'} |")
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


def display_name(seat: str) -> str:
    """The seat's public display name: 'Gandalf (1)'.

    Names are arbitrary pop-culture labels for humans and bots to read —
    the number in brackets is the seat number, the one true identity
    ('seat-01' prints as 1, 'seat-10' as 10). Machine files (ballots,
    dossiers, state, transcripts) always store the bare seat ID; only
    prose layers display the name."""
    name = get_seats().get(seat, {}).get("name")
    number = seat.split("-")[-1]
    number = str(int(number)) if number.isdigit() else number
    return f"{name} ({number})" if name else seat


def is_alive(seat: str) -> bool:
    """Check if a seat is alive."""
    return seat in read_state()["alive"]


def get_living_seats() -> List[str]:
    """Get a list of living seats."""
    return read_state()["alive"]
