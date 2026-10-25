from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Tuple, Union


def read_state() -> Dict[str, Union[int, str, List[str], Dict]]:
    """Read the current game state from state.json."""
    with open("gameplay/state.json", "r") as f:
        return json.load(f)


def write_state(state: Dict[str, Union[int, str, List[str], Dict]]) -> None:
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


def persona_name(persona: Optional[str]) -> str:
    """Short merchant name from a persona prompt.

    'You are The Carpet Weaver. You see the pattern...' → 'The Carpet Weaver'.
    Never dump whole persona paragraphs into announcements or the graveyard.
    """
    if not persona:
        return "Unknown merchant"
    m = _PERSONA_NAME_RE.match(persona)
    if m:
        return m.group(1).strip()
    return persona.strip()[:24] or "Unknown merchant"


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
    with open(path, "r") as f:
        lines = f.read().splitlines()
    idx = next((i for i, l in enumerate(lines) if l.startswith("|---")), None)
    insert_at = idx + 1 if idx is not None else len(lines)
    lines.insert(insert_at, line)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def get_seats() -> Dict[str, Dict[str, Union[str, int]]]:
    """Load seat data from setup/seats.json."""
    with open("setup/seats.json", "r") as f:
        return json.load(f)["seats"]


def display_name(seat: Optional[str]) -> str:
    """The merchant's public name label, alone: 'Gandalf'.

    Names are arbitrary labels — never the seat number in prose. Machine
    files (ballots, dossiers, state, transcripts) always store the bare
    seat ID ('seat-01'); only prose layers display the name. Seat numbers
    are bookkeeping, never speech.
    """
    if not seat:          # e.g. an asleep night action has no target
        return "—"
    name = get_seats().get(seat, {}).get("name")
    return name or seat


def seat_from_label(text: Optional[str]) -> Optional[str]:
    """Seat ID from any label form: 'seat-01', 'Gandalf (1)', '(10)', or a
    plain merchant NAME ('Gandalf', '...as Gandalf said...'). Names are
    unique across seats, so the first name found wins. Backward compatible
    with the old 'Name (number)' labels of earlier matches. Returns None
    when nothing resolves."""
    if not text:
        return None
    m = re.search(r"seat-(\d{1,2})", text)
    if m:
        return f"seat-{int(m.group(1)):02d}"
    m = re.search(r"\(([0-9]{1,2})\)", text)
    if m:
        return f"seat-{int(m.group(1)):02d}"
    low = text.lower()
    for sid, s in sorted(get_seats().items()):
        name = (s.get("name") or "").lower()
        if name and re.search(rf"\b{re.escape(name)}\b", low):
            return sid
    return None


def is_alive(seat: str) -> bool:
    """Check if a seat is alive."""
    return seat in read_state()["alive"]


def get_living_seats() -> List[str]:
    """Get a list of living seats."""
    return read_state()["alive"]


# ------------------------------------------------------------- tea clock ---
# The bazaar's day is divided into named regions — flavour computed from
# the arena clock, not new mechanics. Bots get the current region as
# context and speak of tea naturally; the Herald states the time of
# print. Fractions are of the phase's own duration.
# One 45-minute round: Morning, Morning tea, Lunch, Afternoon tea,
# Dinner (5 min each of a 25-min discussion) → Evening (the 5-min vote)
# → The night, Night snacks, The night watch (5 min each of a 15-min night).
DAY_REGIONS = [
    (0.00, 0.20, "Morning", "the shutters open one by one"),
    (0.20, 0.40, "Morning tea", "the first pots of the day"),
    (0.40, 0.60, "Lunch", "the stalls quiet for lunch"),
    (0.60, 0.80, "Afternoon tea", "the afternoon glasses are poured"),
    (0.80, 1.01, "Dinner",
     "the takings are counted; every merchant names who they lean "
     "toward banishing"),
]

NIGHT_REGIONS = [
    (0.00, 0.34, "The night", "the bazaar sleeps"),
    (0.34, 0.67, "Night snacks", "the braziers burn low"),
    (0.67, 1.01, "The night watch", "the watch makes its rounds"),
]


def _parse_ts(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def day_region(state: Dict[str, Union[int, str, Dict, List]]) -> Tuple[str, str]:
    """(label, flavour) for the current in-theme time of day, from the
    arena clock. Falls back to a neutral region if the clock is missing."""
    now = datetime.now(timezone.utc)
    clock = state.get("clock", {})
    phase = state.get("phase")

    if phase in ("discussion", "voting"):
        if phase == "voting":               # the vote rides the evening
            return "Evening", "the lamps are lit and the vote is on"
        dawn = _parse_ts(clock.get("dawn"))
        end = _parse_ts(clock.get("discussion_deadline"))
        if dawn and end and end > dawn:
            frac = min(max((now - dawn) / (end - dawn), 0.0), 0.99)
            for lo, hi, label, flavour in DAY_REGIONS:
                if lo <= frac < hi:
                    return label, flavour
        return "Morning", "the bazaar hums between dawn and dusk"

    if phase == "night":
        end = _parse_ts(clock.get("night_deadline"))
        if end:
            # The clock only records the night's END (set when night fell),
            # so measure the elapsed fraction backwards over the nominal
            # span (gm/run.py NIGHT_MINUTES, overridable for exotic tests).
            import os
            night_len = timedelta(
                minutes=int(os.environ.get("BAZAAR_NIGHT_MINUTES", "15")))
            elapsed = night_len - (end - now)
            frac = min(max(elapsed / night_len, 0.0), 0.99)
            for lo, hi, label, flavour in NIGHT_REGIONS:
                if lo <= frac < hi:
                    return label, flavour
        return "The night", "the bazaar sleeps, more or less"

    return "The small hours", "the bazaar waits for the next bell"
