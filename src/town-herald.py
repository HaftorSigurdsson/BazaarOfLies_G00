#!/usr/bin/env python3
"""Bazaar of Lies — The Herald (newspaper bot).

An eleventh voice in the arena: the bazaar's only newspaper, printed twice
daily. The Herald is a FACTS-ONLY publication:

  - sources are exclusively public: announcements, the graveyard, the
    current cycle's public statements, and the list of living seats;
  - it never speculates about the roles of living merchants;
  - it never invents statements, deaths, or events;
  - roles may only be restated from official obituaries (the GM reveals
    roles at death);
  - every edition carries a 'By the Numbers' section (machine-counted
    public figures; ballot participation appears in EVENING editions
    only — the morning paper reports the news, the evening paper carries
    the returns);
  - the FIRST MORNING of a match carries a short introduction: who has
    arrived and opened their stalls (public facts only, no news to
    print yet);
  - merchants appear by NAME ALONE — seat numbers never appear in the
    paper;
  - evening editions are the fuller paper: the word on the street with
    brief verbatim quotes from the day's statements;
  - when public statements exist, a 'Letter to the Editor' section closes
    the paper: one statement quoted verbatim, attributed, uncommented.

Editions (one writer per file, journal-guarded against double printing):
  - morning edition — printed once when phase becomes 'discussion'
  - evening edition — printed once when phase becomes 'night'

Output: gameplay/herald/herald-vol<VV>-c<CCC>-{morning,evening}.md (the volume rises forever, kept in the vault); the PDF twins land in gameplay/library/ for the humans.

Run from any clone of the arena repo with push access, in its own window:

    uv run src/town-herald.py            # journal defaults to ../.bazaar/herald-journal.json
    uv run src/town-herald.py --journal ~/.bazaar/herald-journal.json

It is deliberately self-contained (same poll loop, ask(), commit_and_push
patterns as villager.py) so it can run from any seat clone without arguments.
"""
import argparse
import glob
from datetime import datetime, timezone
import json
import logging
import os
import random
import re
import subprocess
import sys
import time
from typing import List, Optional

from dotenv import load_dotenv
from mistralai.client import Mistral

# Load environment variables from .env
load_dotenv()

# gm/ sits at the arena root — the tea clock (day regions) lives there.
_ARENA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ARENA_ROOT)
from gm.utils import day_region, seat_from_label

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- config ---
MODEL = "mistral-large-latest"
POLL_SECONDS = 30
JITTER_SECONDS = 5
PUSH_ATTEMPTS = 5
EDITION_MAX_CHARS = {"morning": 3600, "evening": 5200}   # fuller evenings
ANNOUNCEMENT_HIGHLIGHTS = 6
BALLOT_TABLES_MAX = 2

parser = argparse.ArgumentParser(description="Bazaar of Lies — The Herald")
parser.add_argument("--journal", default=None,
                    help="Journal path (default ../.bazaar/herald-journal.json)")
parser.add_argument("--dry-run", action="store_true",
                    help="Preview markdown output without generating PDF or committing")
parser.add_argument("--verbose", action="store_true",
                    help="Enable verbose logging")
args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

# src/town-herald.py -> REPO_ROOT is the parent of src/ (the clone root).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAZAAR_DIR = os.path.join(os.path.dirname(REPO_ROOT), ".bazaar")
VOL_FILE = os.path.join(BAZAAR_DIR, "herald-vol.txt")


def next_volume():
    """The Herald's volume rises forever — across matches and resets.
    The counter lives in the vault, next to the journal."""
    try:
        vol = int(open(VOL_FILE).read().strip()) + 1
    except (OSError, ValueError):
        vol = 1
    with open(VOL_FILE, "w") as f:
        f.write(str(vol))
    return vol
JOURNAL_PATH = args.journal or os.path.join(BAZAAR_DIR, "herald-journal.json")

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))
if not os.environ.get("MISTRAL_API_KEY"):
    logger.error("MISTRAL_API_KEY not set in .env")
    sys.exit(1)

HERALD_SYSTEM = (
    "You are The Herald, the bazaar's only newspaper, printed twice daily "
    "for longer than anyone can remember. You are ink-stained, thrifty with "
    "words, and quietly amused by everything the market has tried to sell "
    "you. VOICE: write like a 19th-century town paper — confident, "
    "economical, dryly witty; vintage flourishes ('merchants learned at "
    "dawn', 'by all accounts', 'the patience of the marketplace') used "
    "sparingly, never purple, never sentimental. The headline should carry "
    "the day's one true fact. "
    "Strict editorial rules: FACTS ONLY, drawn exclusively from the digest "
    "you are given. Never speculate about the role or allegiance of a living "
    "merchant. Never invent statements, departures, or events. Roles may "
    "only be restated from official obituaries. Attribute every statement "
    "to its merchant by NAME ALONE, exactly as the label is given (e.g. "
    "'Gandalf') — never print seat numbers in the paper. Names are "
    "arbitrary labels — never treat a merchant "
    "as the character their name may evoke, and never reference any film. "
    "Keep it short and lively: a headline, then brief sections (the day's "
    "news, the departed, the word on the street, by the numbers). Include "
    "a short 'By the Numbers' section using the counted figures exactly as "
    "given. Do NOT write a tally or voting-record section. Ballots are "
    "evening news: in MORNING editions, do not mention ballots, tallies, "
    "or vote counts at all. In EVENING editions, the official tally chart "
    "is appended after your text by the press — you may refer to its "
    "result in one sentence, nothing more. "
    "FIRST MORNING: if the digest marks this as the match's first morning, "
    "there is no news yet — write a short introductory edition: welcome "
    "the readers to the newly opened bazaar and introduce the merchants "
    "who have arrived (names only, public facts). Do not invent events, "
    "statements, or departures. "
    "In EVENING editions, write a fuller paper: include a 'The Word on "
    "the Street' section with brief verbatim quotes from two or three of "
    "the day's statements (attributed by name, never edited, uncommented) "
    "and a few lines on what the day's discussion turned on. "
    "If the digest contains statements, close with a 'Letter to the "
    "Editor' section: quote one of the statements verbatim, attributed "
    "to its seat, introduced by at most one neutral line — never edit the "
    "quote and never comment on the writer's role or allegiance. "
    "CONTINUITY: the digest may include your own previous editions. "
    "You may follow up on your own reporting in one brief line ('as we "
    "reported at dawn', 'this paper noted yesterday') — never re-quote "
    "yesterday's paper at length, and if today's facts differ from what "
    "you printed before, say so plainly and without embarrassment. "
    "No advice on how to vote."
)


def log(message: str) -> None:
    """Log a message to stderr with a timestamp."""
    logger.info(message)


# ------------------------------------------------------------------- git ---
def git(*argv: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    try:
        return subprocess.run(["git", *argv], check=check,
                              capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"git {' '.join(argv)} failed: {e}")
        raise
    except Exception as e:
        logger.error(f"git {' '.join(argv)} error: {type(e).__name__}: {e}")
        raise


def safe_push() -> None:
    """Push with retry: the Herald shares the branch with ten bots."""
    try:
        for attempt in range(1, PUSH_ATTEMPTS + 1):
            r = git("push", check=False)
            if r.returncode == 0:
                return
            log(f"push rejected (attempt {attempt}/{PUSH_ATTEMPTS}); rebasing")
            git("pull", "--rebase", check=False)
            # jittered backoff so simultaneous writers re-collide less
            time.sleep(2 * attempt + random.uniform(0, 2 * attempt))
        raise RuntimeError(f"push rejected {PUSH_ATTEMPTS} times — needs a human")
    except Exception as e:
        logger.error(f"safe_push failed: {type(e).__name__}: {e}")
        raise


def commit_and_push(paths: List[str], msg: str) -> None:
    """Commit and push changes to the arena repo."""
    try:
        git("add", *paths)
        r = git("commit", "-m", msg, check=False)
        if r.returncode != 0:
            log(f"nothing to commit for: {msg}")
            return
        safe_push()
    except Exception as e:
        logger.error(f"commit_and_push failed: {type(e).__name__}: {e}")
        raise


# --------------------------------------------------------------- journal ---
def load_journal():
    if os.path.exists(JOURNAL_PATH):
        with open(JOURNAL_PATH) as f:
            return json.load(f)
    return {"editions": {}, "last_announcement_ts": ""}


def save_journal(journal):
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    with open(JOURNAL_PATH, "w") as f:
        json.dump(journal, f, indent=2)


def edition_state(journal, epoch, cycle, part):
    key = f"{epoch}:{cycle}:{part}"
    return key in journal["editions"]


def mark_edition(journal, epoch, cycle, part):
    journal["editions"][f"{epoch}:{cycle}:{part}"] = \
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------- arena readers ---
def read_state():
    with open("gameplay/state.json") as f:
        return json.load(f)


def seat_names():
    """Public name labels from setup/seats.json (arbitrary pop-culture
    labels; the seat ID is the one true identity)."""
    try:
        with open("setup/seats.json") as f:
            return {k: v.get("name", "") for k, v in json.load(f)["seats"].items()}
    except (OSError, KeyError, json.JSONDecodeError):
        return {}


def display_name(seat):
    """The merchant's public name label, alone ('Gandalf') — like the
    Elder Council, the Herald never prints seat numbers in its pages.
    (Raw GM text still carries them; seat_from_label does the parsing.)"""
    name = seat_names().get(seat)
    return name or seat


def graveyard_roll():
    """Public obituaries: seat, merchant name, role revealed on departure, cause."""
    entries = []
    try:
        text = open("gameplay/village/graveyard.md").read()
    except OSError:
        return entries
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line or "Banished By" in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        seat = seat_from_label(line)
        if seat is None:
            continue
        role = next((c for c in cells
                     if c in ("Mafia", "Doctor", "Detective", "Villager")), "Unknown")
        if "Stall shuttered" in line:
            cause = "stall shuttered"
        elif "Night kill" in line:            # rows from older matches
            cause = "night kill"
        else:
            cause = "village vote"
        pm = re.search(r"[Yy]ou are ([^.,]+)", line)          # legacy rows
        nm = next((c for c in cells if c.startswith("The ")), "")  # new rows
        name = (pm.group(1).strip() if pm else nm) or seat
        entries.append(f"{display_name(seat)} ({name}) — {role}, by {cause}")
    return entries


_ANNOUNCEMENT_SPLIT = re.compile(r"\*\*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\*\*")


def announcements_since(journal):
    """Public GM announcements published since the last processed one."""
    try:
        text = open("gameplay/village/announcements.md").read()
    except OSError:
        return []
    parts = _ANNOUNCEMENT_SPLIT.split(text)
    blocks, last = [], journal.get("last_announcement_ts", "")
    for i in range(1, len(parts) - 1, 2):
        ts, body = parts[i], parts[i + 1].strip().strip("-").strip()
        if ts > last:
            blocks.append((ts, body))
            journal["last_announcement_ts"] = ts
    return blocks[-ANNOUNCEMENT_HIGHLIGHTS:]


def read_statements(state):
    """The current cycle's public statement records, oldest first."""
    cycle, epoch = state["cycle"], state.get("epoch")
    dawn = state.get("clock", {}).get("dawn")
    recs = {}
    sources = []
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
                    continue
                if epoch is not None and rec.get("epoch") != epoch:
                    continue   # statement from another match — ghost
                ts = rec.get("ts", "")
                if dawn and ts and ts < dawn:
                    continue   # statement from an earlier run of this cycle
                key = (rec.get("seat"), rec.get("seq"))
                if key not in recs or ts >= recs[key].get("ts", ""):
                    recs[key] = rec
    return sorted(recs.values(), key=lambda r: r.get("ts", ""))


def statements_digest(state):
    """The current cycle's public statements (facts, attributed to seats).
    Anonymous statements (cycle >= anonymous_cycle) are labeled as 'Anonymous Merchant'."""
    statements = []
    anonymous_cycle = None
    try:
        with open("gm/roles.enc", "r") as f:
            roles = json.load(f)
            anonymous_cycle = roles.get("anonymous_cycle")
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    
    for r in read_statements(state):
        if anonymous_cycle and state.get("cycle", 0) >= anonymous_cycle and r.get("seat") is None:
            statements.append(f"Anonymous Merchant: {r['text']}")
        else:
            statements.append(f"{display_name(r['seat'])}: {r['text']}")
    return statements


def read_ballot_tables():
    """Published ballot tables from the announcements, in order: a list of
    (announcement body, {seat: target}) — the GM publishes one signed,
    public table per vote. Seats appear as name labels ('Gandalf (seat-01)');
    the seat ID inside the brackets is the identity."""
    try:
        text = open("gameplay/village/announcements.md").read()
    except OSError:
        return []
    tables = []
    parts = _ANNOUNCEMENT_SPLIT.split(text)
    for i in range(2, len(parts), 2):              # block bodies
        body = parts[i]
        if "| Voted for |" not in body:
            continue
        voters = {}
        for line in body.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 3:
                continue
            ms = seat_from_label(cells[0])
            if not ms:
                continue
            mt = seat_from_label(cells[1])
            voters[ms] = mt if mt else cells[1].lower()
        if voters:
            tables.append((body, voters))
    return tables


def vote_history():
    """Recent public ballot tallies, parsed from the GM's published tables.
    Newest first."""
    tallies = []
    for body, voters in read_ballot_tables():
        counts = {}
        for target in voters.values():
            counts[target] = counts.get(target, 0) + 1
        m = re.search(r"\*\*Banishment!\*\*\s*([A-Za-z]+)", body)
        banished = seat_from_label(m.group(1)) if m else None
        result = (f"{display_name(banished)} banished"
                  if banished else "no banishment (tie or no majority)")
        tally = ", ".join(
            f"{display_name(t) if t != 'abstain' else 'abstain'}: "
            f"{n} vote{'s' if n != 1 else ''}"
            for t, n in sorted(counts.items(), key=lambda kv: -kv[1]))
        rejected = re.search(r"(\d+) ballot\(s\) rejected", body)
        line = f"{result} — ballots: {tally}"
        if rejected:
            line += f"; {rejected.group(1)} ballot(s) rejected"
        tallies.append(line)
    return tallies[-BALLOT_TABLES_MAX:][::-1]


def vote_participation():
    """Per-seat participation across all published ballot tables.
    Returns '' when the GM has not published any tables yet."""
    tables = read_ballot_tables()
    if not tables:
        return ""
    n = len(tables)
    casts, abstentions = {}, {}
    for _, voters in tables:
        for seat, target in voters.items():
            casts[seat] = casts.get(seat, 0) + 1
            if target == "abstain":
                abstentions[seat] = abstentions.get(seat, 0) + 1
    parts = []
    for seat in sorted(casts):
        p = f"{display_name(seat)}: {casts[seat]}/{n}"
        if abstentions.get(seat):
            p += f" ({abstentions[seat]} abstention" \
                 f"{'s' if abstentions[seat] != 1 else ''})"
        parts.append(p)
    return (f"Vote participation across the {n} published ballot "
            f"table{'s' if n != 1 else ''}: " + ", ".join(parts) + ".")


def quiet_night_streak():
    """Consecutive most-recent nights the GM announced as quiet."""
    try:
        text = open("gameplay/village/announcements.md").read()
    except OSError:
        return 0
    bodies = _ANNOUNCEMENT_SPLIT.split(text)[2::2]
    streak = 0
    for body in reversed(bodies):
        if "night passed quietly" in body.lower():
            streak += 1
        elif "night kill" in body.lower() or "stall shuttered" in body.lower():
            break
    return streak


def by_the_numbers(state, part):
    """Public, machine-counted figures for the 'By the Numbers' section.
    Ballot figures are evening news only — the morning paper reports the
    news, the evening paper carries the returns."""
    lines = []
    alive = sorted(state.get("alive", []))
    roll = {e.split(" ")[0] for e in graveyard_roll()}   # unique departed
    lines.append(f"{len(alive)} seats alive, {len(roll)} in the graveyard.")
    stmts = read_statements(state)
    if stmts:
        per_seat = {}
        for r in stmts:
            per_seat[r.get("seat")] = per_seat.get(r.get("seat"), 0) + 1
        counts = ", ".join(f"{display_name(s)}: {n}" for s, n in sorted(per_seat.items()))
        silent = [s for s in alive if s not in per_seat]
        lines.append(f"Statements this cycle: {len(stmts)} ({counts}).")
        if silent:
            lines.append("Silent so far this cycle: "
                         + ", ".join(display_name(s) for s in silent) + ".")
    else:
        lines.append("No public statements this cycle yet.")
    streak = quiet_night_streak()
    if streak:
        lines.append(f"Quiet nights in a row: {streak}.")
    if part == "evening":
        participation = vote_participation()
        if participation:
            lines.append(participation)
    return lines


BAR_CHAR = "\u2593"          # the engraved bar of the tally chart
BAR_MAX = 24               # longest bar, in characters


def tally_chart():
    """The daily tally as an election-returns chart, computed (not written):
    the latest public ballot table, drawn as old-style solid bars. Returns
    '' when the GM has not published a table yet."""
    tables = read_ballot_tables()
    if not tables:
        return ""
    body, voters = tables[-1]
    counts = {}
    for target in voters.values():
        counts[target] = counts.get(target, 0) + 1
    total = len(voters)
    abstains = counts.get("abstain", 0)
    m = re.search(r"\*\*Banishment!\*\*\s*([A-Za-z]+)", body)
    banished = seat_from_label(m.group(1)) if m else None

    lines = []
    headline = "THE DAILY TALLY"
    if banished:
        headline += f" — {display_name(banished)} BANISHED"
    lines.append(headline)
    lines.append(f"{total} ballot{'s' if total != 1 else ''} cast"
                 + (f", {abstains} abstention{'s' if abstains != 1 else ''}"
                    if abstains else ""))
    lines.append("-" * 44)
    top = max(counts.values())
    for t, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        label = display_name(t) if t != "abstain" else "abstain"
        width = max(1, round(BAR_MAX * n / top))
        lines.append(f"{label:<15} {BAR_CHAR * width} {n}")
    return "\n".join(lines)


def generate_editors_note(state: dict, part: str) -> str:
    """Generate the Herald's editorial note (model-written, labeled as opinion)."""
    prompt = (
        f"The bazaar is in cycle {state['cycle']}, {part} phase. "
        f"Public facts:\n{facts_digest(state, part)}\n\n"
        "Write a 2-3 sentence editorial note summarizing the bazaar's mood this cycle. "
        "Use the Herald's voice: witty, slightly cynical, and thematic. "
        "Do not reveal private information. Do not speculate about roles. "
        "Label it clearly as the **Editor's Note**."
    )
    note = ask(prompt)
    return f"## Editor's Note\n\n{note}\n"


def generate_by_the_numbers(state: dict, part: str) -> str:
    """Machine-written 'By the Numbers' section (factual, never model-written).
    Ballot figures are evening news only."""
    cycle = state["cycle"]
    alive = len(state["alive"])
    graveyard_count = 0
    try:
        with open("gameplay/village/graveyard.md", "r") as f:
            graveyard = f.read()
            graveyard_count = len([line for line in graveyard.splitlines() 
                                  if line.startswith("|") and not line.startswith("|---") and not line.startswith("| Match")])
    except OSError:
        pass

    numbers = [
        f"- Merchants alive: {alive}",
        f"- Merchants departed: {graveyard_count}",
        f"- Cycle: {cycle}",
    ]

    if part == "evening":
        # Add ballot participation (evening-only)
        try:
            with open("gameplay/village/ballot.md", "r") as f:
                ballot = f.read()
                votes = len([line for line in ballot.splitlines() if line.startswith("|") and not line.startswith("|---")])
                numbers.append(f"- Votes cast this cycle: {votes}")
        except OSError:
            pass
    
    return "## By the Numbers\n\n" + "\n".join(numbers) + "\n"


def read_last_words():
    """Read last words from gameplay/village/last_words.md."""
    try:
        with open("gameplay/village/last_words.md", "r") as f:
            return f.read()
    except OSError:
        return ""


def read_historian_summary(cycle):
    """Read Historian's summary for the given cycle."""
    try:
        with open(f"gameplay/village/cycle-summaries/c{cycle:03d}.md", "r") as f:
            return f.read()
    except OSError:
        return ""


def facts_digest(state, part):
    """Public facts only. Morning: what happened overnight + today's plan.
    Evening: the day's banishment + what was said."""
    label, flavour = day_region(state)
    digest = [f"Match {state['match']}, cycle {state['cycle']} ({part} edition) "
              f"— printed at {label} ({flavour})."]
    digest.append("Seats alive: "
                  + ", ".join(display_name(s) for s in sorted(state["alive"])) + ".")
    roll = graveyard_roll()
    digest.append("Official obituaries (roles revealed on departure): "
                  + ("; ".join(roll) if roll else "none so far."))
    clock = state.get("clock", {})
    for label in ("discussion_deadline", "voting_deadline", "night_deadline"):
        if clock.get(label):
            digest.append(f"{label.replace('_', ' ')}: {clock[label]}")
    
    # Replace model-written "By the Numbers" with machine-written version
    digest.append(generate_by_the_numbers(state, part))
    
    # Add Historian's summary (evening editions only)
    if part == "evening":
        historian_summary = read_historian_summary(state["cycle"])
        if historian_summary:
            digest.append("\n\n## The Historian's Chronicle\n\n" + historian_summary)
    
    # Add last words (morning editions only, after banishment)
    if part == "morning":
        last_words = read_last_words()
        if last_words:
            digest.append("\n\n## Last Words\n\n" + last_words)
    
    if part == "evening":
        tallies = vote_history()
        if tallies:
            digest.append("Recent ballot tallies (from the GM's public tables, "
                          "newest first):\n" + "\n".join(tallies))
    
    # First morning edition: introduce the bazaar and merchants
    if part == "morning" and int(state.get("cycle") or 0) == 1:
        merchants = ", ".join(display_name(s) for s in sorted(state["alive"]))
        digest.insert(2, (
            "FIRST MORNING OF THE MATCH: The bazaar has just opened its gates, "
            "and the following merchants have arrived to set up their stalls: "
            f"{merchants}. Today marks the beginning of a new cycle of trade, "
            "rumors, and alliances. The merchants are eager to establish their "
            "reputations, but only time will tell who can be trusted."
        ))
    
    return "\n".join(digest)


# ------------------------------------------------------------ model call ---
def ask(prompt: str) -> str:
    """Ask the model a question and return its response."""
    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[
                {"role": "system", "content": HERALD_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error(f"ask() failed: {type(e).__name__}: {e}")
        return ""


# ------------------------------------------------------------------ work ---
PREVIOUS_CHARS = 1600       # how much of each old edition to re-read


def previous_editions(state, part):
    """The Herald's own last two editions, most recent first — the paper
    reads itself so it can follow up on yesterday's reporting. Same-match
    only: the reset clears gameplay/herald/ between matches."""
    cycle = state["cycle"]
    if part == "evening":
        order = [(cycle, "morning"), (cycle - 1, "evening")]
    else:
        order = [(cycle - 1, "evening"), (cycle - 1, "morning")]
    parts_out = []
    for c, p in order:
        if c < 1:
            continue
        try:
            import glob as globmod
            paths = sorted(globmod.glob(
                f"gameplay/herald/herald-vol-*-c{c:03d}-{p}.md"))
            text = open(paths[-1]).read().strip()
        except (OSError, IndexError):
            continue
        label = ("this cycle's morning paper" if (c, p) == (cycle, "morning")
                 else f"cycle {c:03d}'s {p} paper")
        parts_out.append(f"[{label}]\n{text[:PREVIOUS_CHARS]}")
    return "\n\n".join(parts_out)


def print_edition(state, part, journal):
    cycle = state["cycle"]
    epoch = state.get("epoch")
    herald_dir = "gameplay/herald"
    os.makedirs(herald_dir, exist_ok=True)
    existing = sorted(glob.glob(
        f"{herald_dir}/herald-vol-*-c{cycle:03d}-{part}.md"))
    if existing:                    # one writer per file, even if the journal is lost
        log(f"{part} edition for cycle {cycle:03d} already printed")
        mark_edition(journal, epoch, cycle, part)
        save_journal(journal)
        return
    vol = next_volume()
    path = f"{herald_dir}/herald-vol-{vol:02d}-c{cycle:03d}-{part}.md"

    digest = facts_digest(state, part)
    ann = announcements_since(journal)
    if ann:
        digest += "\n\nRecent official announcements:\n" + "\n---\n".join(
            f"[{ts}] {body}" for ts, body in ann)
    stmts = statements_digest(state)
    if stmts:
        digest += "\n\nStatements made in the bazaar this cycle (verbatim):\n" + \
            "\n".join(stmts)[-6000:]

    # The Herald re-reads its own last two editions (public record —
    # continuity is facts, not invention).
    previous = previous_editions(state, part)
    if previous:
        digest += "\n\nYour own previous editions (public record of this match, "
        digest += "most recent first):\n" + previous

    limit = EDITION_MAX_CHARS[part]
    edition = ask(f"Public facts digest:\n\n{digest}\n\n"
                  f"Write the Herald's {part} edition for cycle {cycle:03d} "
                  f"as markdown (max {limit} characters)."
                  )[:limit]

    # The official tally chart is computed, never model-written — like an
    # election returns graphic, exact to the ballot. Evening editions only:
    # the morning paper reports the news; the evening paper carries the
    # day's returns.
    chart = tally_chart()
    if chart and part == "evening":
        edition += "\n\n## The Tally\n\n```text\n" + chart + "\n```\n"

    # Add Editor's Note and By the Numbers to the edition
    edition += "\n\n---\n\n" + generate_editors_note(state, part)
    
    with open(path, "w") as f:
        # Inside the paper the numbers print small (Vol. 1, Cycle 1);
        # only the FILENAME pads (vol-01, c001) for clean sorting.
        f.write(f"# The Herald — {'Morning' if part == 'morning' else 'Evening'} Edition\n\n"
                f"*Vol. {vol} — Match {state['match']}, Cycle {cycle}*\n\n"
                f"{edition}\n")

    # Press the human copy: a one-page A4 newspaper front page (best-effort —
    # the markdown edition is what the merchants actually read).
    pdf_path = None
    try:
        # The press lives in town-press.py — kebab-cased, so Python cannot
        # import it by name; load it from its file instead.
        import importlib.util
        _press_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "town-press.py")
        _spec = importlib.util.spec_from_file_location("town_press", _press_file)
        _press = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_press)
        pdf_path = _press.compile_edition(path)
        log(f"pressed {os.path.basename(pdf_path)}")
    except Exception as e:  # a press failure must never stop the paper
        log(f"press skipped: {type(e).__name__}: {e}")

    if not args.dry_run:
        commit_and_push([path] + ([pdf_path] if pdf_path else []),
                        f"Herald {part} edition c{cycle:03d}")
        mark_edition(journal, epoch, cycle, part)
        save_journal(journal)
        log(f"printed {part} edition for cycle {cycle:03d}")
    else:
        log(f"[DRY RUN] Preview of {part} edition for cycle {cycle:03d}:")
        log(edition)


# ------------------------------------------------------------- main loop ---
def main_loop():
    journal = load_journal()
    log(f"Herald up — model={MODEL}")
    log(f"journal={JOURNAL_PATH}")

    while True:
        try:
            git("pull", "--rebase")
            state = read_state()
            phase = state.get("phase", "unknown")
            epoch = state.get("epoch") or "m%s" % state.get("match", 0)
            cycle = state.get("cycle", 0)

            if phase == "discussion" and not edition_state(journal, epoch, cycle, "morning"):
                print_edition(state, "morning", journal)
            elif phase == "night" and not edition_state(journal, epoch, cycle, "evening"):
                print_edition(state, "evening", journal)
            else:
                announcements_since(journal)   # keep the pointer fresh
                save_journal(journal)

        except FileNotFoundError as e:
            log(f"waiting: {e}")
        except Exception as e:  # the Herald must never die quietly
            log(f"ERROR: {type(e).__name__}: {e}")

        time.sleep(POLL_SECONDS + random.uniform(0, JITTER_SECONDS))


if __name__ == "__main__":
    main_loop()
