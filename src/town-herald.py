#!/usr/bin/env python3
"""Bazaar of Lies — The Herald (newspaper bot, v1.2).

An eleventh voice in the arena: the bazaar's only newspaper, printed twice
daily. The Herald is a FACTS-ONLY publication:

  - sources are exclusively public: announcements, the graveyard, the
    current cycle's public statements, and the list of living seats;
  - it never speculates about the roles of living merchants;
  - it never invents statements, deaths, or events;
  - roles may only be restated from official obituaries (the GM reveals
    roles at death).

Editions (one writer per file, journal-guarded against double printing):
  - morning edition — printed once when phase becomes 'discussion'
  - evening edition — printed once when phase becomes 'night'

Output: gameplay/news/herald-c<CCC>-morning.md and gameplay/news/herald-c<CCC>-evening.md.

Run from any clone of the arena repo with push access, in its own window:

    uv run src/town-herald.py            # journal defaults to ../bazaar/herald-journal.json
    uv run src/town-herald.py --journal ~/.bazaar/herald-journal.json

It is deliberately self-contained (same poll loop, ask(), commit_and_push
patterns as villager.py) so it can run from any seat clone without arguments.
"""
import argparse
import glob
import json
import os
import random
import re
import subprocess
import time

from mistralai import Mistral

# ---------------------------------------------------------------- config ---
MODEL = "mistral-small-2409"
POLL_SECONDS = 30
JITTER_SECONDS = 5
PUSH_ATTEMPTS = 5
EDITION_MAX_CHARS = 2800
ANNOUNCEMENT_HIGHLIGHTS = 6

parser = argparse.ArgumentParser(description="Bazaar of Lies — The Herald")
parser.add_argument("--journal", default=None,
                    help="Journal path (default ../bazaar/herald-journal.json)")
args = parser.parse_args()

# src/editor.py -> REPO_ROOT is the parent of src/ (the clone root).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAZAAR_DIR = os.path.join(os.path.dirname(REPO_ROOT), "bazaar")
JOURNAL_PATH = args.journal or os.path.join(BAZAAR_DIR, "herald-journal.json")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

HERALD_SYSTEM = (
    "You are The Herald, the bazaar's only newspaper, printed twice daily. "
    "Strict editorial rules: FACTS ONLY, drawn exclusively from the digest "
    "you are given. Never speculate about the role or allegiance of a living "
    "merchant. Never invent statements, deaths, or events. Roles may only be "
    "restated from official obituaries. Attribute every statement to its "
    "seat. Keep it short and lively: a headline, then brief sections "
    "(headlines, the dead, the word on the street). No advice on how to vote."
)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] HERALD: {msg}", flush=True)


# ------------------------------------------------------------------- git ---
def git(*argv, check=True):
    return subprocess.run(["git", *argv], check=check,
                          capture_output=True, text=True)


def safe_push():
    for attempt in range(1, PUSH_ATTEMPTS + 1):
        r = git("push", check=False)
        if r.returncode == 0:
            return
        log(f"push rejected (attempt {attempt}/{PUSH_ATTEMPTS}); rebasing")
        git("pull", "--rebase", check=False)
        time.sleep(2 * attempt)
    raise RuntimeError(f"push rejected {PUSH_ATTEMPTS} times — needs a human")


def commit_and_push(paths, msg):
    git("add", *paths)
    r = git("commit", "-m", msg, check=False)
    if r.returncode != 0:
        log(f"nothing to commit for: {msg}")
        return
    safe_push()


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


def graveyard_roll():
    """Public obituaries: seat, merchant name, role revealed at death, cause."""
    entries = []
    try:
        text = open("gameplay/village/graveyard.md").read()
    except OSError:
        return entries
    for line in text.splitlines():
        if not line.startswith("|") or "seat-" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        seat = next((c for c in cells if re.fullmatch(r"seat-\d{2}", c)), None)
        if seat is None:
            continue
        role = next((c for c in cells
                     if c in ("Mafia", "Doctor", "Detective", "Villager")), "Unknown")
        cause = "night kill" if "Night kill" in line else "village vote"
        pm = re.search(r"[Yy]ou are ([^.,]+)", line)              # legacy rows
        nm = next((c for c in cells if c.startswith("The ")), "")  # new rows
        name = (pm.group(1).strip() if pm else nm) or seat
        entries.append(f"{seat} ({name}) — {role}, by {cause}")
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


def statements_digest(state):
    """The current cycle's public statements (facts, attributed to seats)."""
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
    ordered = sorted(recs.values(), key=lambda r: r.get("ts", ""))
    return [f"{r['seat']}: {r['text']}" for r in ordered]


def facts_digest(state, part):
    """Public facts only. Morning: what happened overnight + today's plan.
    Evening: the day's banishment + what was said."""
    digest = [f"Match {state['match']}, cycle {state['cycle']} ({part} edition)."]
    digest.append(f"Seats alive: {', '.join(sorted(state['alive']))}.")
    roll = graveyard_roll()
    digest.append("Official obituaries (roles revealed at death): "
                  + ("; ".join(roll) if roll else "none so far."))
    clock = state.get("clock", {})
    for label in ("discussion_deadline", "voting_deadline", "night_deadline"):
        if clock.get(label):
            digest.append(f"{label.replace('_', ' ')}: {clock[label]}")
    return "\n".join(digest)


# ------------------------------------------------------------ model call ---
def ask(user):
    r = client.chat.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": HERALD_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    return (r.choices[0].message.content or "").strip()


# ------------------------------------------------------------------ work ---
def print_edition(state, part, journal):
    cycle = state["cycle"]
    epoch = state.get("epoch")
    news_dir = "gameplay/news"
    os.makedirs(news_dir, exist_ok=True)
    path = f"{news_dir}/herald-c{cycle:03d}-{part}.md"
    if os.path.exists(path):        # one writer per file, even if the journal is lost
        log(f"{part} edition for cycle {cycle:03d} already printed")
        mark_edition(journal, epoch, cycle, part)
        save_journal(journal)
        return

    digest = facts_digest(state, part)
    ann = announcements_since(journal)
    if ann:
        digest += "\n\nRecent official announcements:\n" + "\n---\n".join(
            f"[{ts}] {body}" for ts, body in ann)
    stmts = statements_digest(state)
    if stmts:
        digest += "\n\nStatements made in the bazaar this cycle (verbatim):\n" + \
            "\n".join(stmts)[-6000:]

    edition = ask(f"Public facts digest:\n\n{digest}\n\n"
                  f"Write the Herald's {part} edition for cycle {cycle:03d} "
                  f"as markdown (max {EDITION_MAX_CHARS} characters)."
                  )[:EDITION_MAX_CHARS]

    with open(path, "w") as f:
        f.write(f"# The Herald — {'Morning' if part == 'morning' else 'Evening'} Edition\n\n"
                f"*Match {state['match']}, Cycle {cycle:03d}*\n\n{edition}\n")

    # Press the human copy: a one-page A4 newspaper front page (best-effort —
    # the markdown edition is what the merchants actually read).
    pdf_path = None
    try:
        from town_press import compile_edition
        pdf_path = compile_edition(path)
        log(f"pressed {os.path.basename(pdf_path)}")
    except Exception as e:  # a press failure must never stop the paper
        log(f"press skipped: {type(e).__name__}: {e}")

    commit_and_push([path] + ([pdf_path] if pdf_path else []),
                    f"Herald {part} edition c{cycle:03d}")
    mark_edition(journal, epoch, cycle, part)
    save_journal(journal)
    log(f"printed {part} edition for cycle {cycle:03d}")


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
