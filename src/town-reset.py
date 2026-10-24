#!/usr/bin/env python3
"""Bazaar of Lies — town-reset.py (full arena reset).

Python equivalent of setup/reset_match.sh: wipes everything a match
touches so the next GM tick deals a clean game:

  - artifacts:  gameplay/{votes,night,dossiers,deals,herald,usage}/,
                gameplay/village/statements/, gameplay/village/day-*.jsonl
  - boards:     graveyard.md and announcements.md rewritten fresh
  - state:      gameplay/state.json reset to the pristine template
                (phase=setup — do NOT delete it: the GM crashes without it)
  - journals:   seat + Herald journals cleared from the vault
                ($VAULT, else the sibling vault ../.bazaar the bots use,
                else ~/.bazaar)

Match recaps (gameplay/village/match-XX-recap.md) are KEPT by default —
they are history and cannot interfere with a fresh match (the new epoch
namespaces everything). Pass --wipe-recaps to remove them too.

Every folder that is supposed to exist gets a .gitkeep if it is missing
one, so the arena keeps its shape even when a directory is emptied.

Nothing destructive happens without confirmation: the script asks
"Are you sure?" before removing anything, and again before committing
(pushing asks once more). --dry-run never prompts and touches nothing.

Usage (from the arena repo root):
    python3 town-reset.py             # reset + commit (asks y/n at each step)
    python3 town-reset.py --dry-run   # show what would happen, touch nothing
    python3 town-reset.py --push      # also push the reset commit (asks first)
    python3 town-reset.py --wipe-recaps  # also remove match recaps
"""
import argparse
import json
import os
import subprocess
import sys

# src/town-reset.py -> REPO_ROOT is the parent of src/ (the arena root).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories whose CONTENTS are pure match artifacts. Kept (with a
# .gitkeep) but emptied. statements/ and day-*.jsonl are the village's
# public record of the finished match — history is in the recaps.
ARTIFACT_DIRS = [
    "gameplay/votes",
    "gameplay/night",
    "gameplay/dossiers",
    "gameplay/deals",
    "gameplay/herald",
    "gameplay/usage",
    "gameplay/village/statements",
]

# Folders that must always exist and carry a .gitkeep so git keeps them.
GITKEEP_DIRS = ARTIFACT_DIRS

BOARDS = {
    "gameplay/village/graveyard.md":
        "# Bazaar Graveyard\n"
        "\n"
        "| Match | Cycle | Seat | Persona | Role | Banished By |\n"
        "|---|---|---|---|---|---|\n",
    "gameplay/village/announcements.md":
        "# Bazaar Announcements\n"
        "\n"
        "The Game Master speaks:\n"
        "\n"
        "---\n",
}

STATE_FILE = "gameplay/state.json"
SEATS_FILE = "setup/seats.json"
DAY_TRANSCRIPT_GLOB = "gameplay/village/day-*.jsonl"
RECAP_GLOB = "gameplay/village/match-*-recap.md"
JOURNAL_PREFIXES = ("journal-seat-", "herald-journal")

COMMIT_MESSAGE = "Reset arena for a fresh match (full artifact + journal wipe)"


def rel(path):
    return os.path.relpath(path, REPO_ROOT)


def log(msg):
    print(f"==> {msg}")


def confirm(question):
    """Ask a yes/no question. Returns True only on an explicit yes."""
    try:
        answer = input(f"{question} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


def remove(path, dry):
    """Remove a file or tree, printing what happens. Returns True if removed."""
    if not os.path.exists(path):
        return False
    verb = "would remove" if dry else "removed  "
    if not dry:
        if os.path.isdir(path) and not os.path.islink(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
    print(f"    {verb} {rel(path)}")
    return True


def clear_artifact_dirs(dry):
    """Empty every artifact directory but keep the directory + .gitkeep."""
    cleared = 0
    for d in ARTIFACT_DIRS:
        path = os.path.join(REPO_ROOT, d)
        if not os.path.isdir(path):
            print(f"    missing  {d} (will be recreated with .gitkeep)")
            continue
        for entry in sorted(os.listdir(path)):
            if entry == ".gitkeep":
                continue
            if remove(os.path.join(path, entry), dry):
                cleared += 1
    return cleared


def remove_day_transcripts(dry):
    """Legacy single-file day transcripts are pure match artifacts."""
    import glob as globmod
    removed = 0
    for path in sorted(globmod.glob(os.path.join(REPO_ROOT, DAY_TRANSCRIPT_GLOB))):
        if remove(path, dry):
            removed += 1
    return removed


def remove_recaps(dry):
    """Match recaps are history — only removed with an explicit flag."""
    import glob as globmod
    removed = 0
    for path in sorted(globmod.glob(os.path.join(REPO_ROOT, RECAP_GLOB))):
        if remove(path, dry):
            removed += 1
    return removed


def rewrite_boards(dry):
    """Fresh public notice boards (not deleted — rewritten to template)."""
    for board, template in BOARDS.items():
        path = os.path.join(REPO_ROOT, board)
        if not dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(template)
        print(f"    {'would rewrite' if dry else 'rewrote'} {board}")
    return len(BOARDS)


def reset_state(dry):
    """Pristine state — phase 'setup' makes the next GM tick deal Match 1
    with a fresh epoch. Do NOT delete the file: the GM crashes without it."""
    seats_path = os.path.join(REPO_ROOT, SEATS_FILE)
    with open(seats_path) as f:
        seats = json.load(f)["seats"]
    state = {
        "match": 0,
        "cycle": 0,
        "epoch": None,
        "phase": "setup",
        "clock": {"dawn": None, "discussion_deadline": None,
                  "voting_deadline": None, "night_deadline": None},
        "alive": sorted(seats.keys()),
        "graveyard": {},
    }
    path = os.path.join(REPO_ROOT, STATE_FILE)
    if not dry:
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    print(f"    {'would reset' if dry else 'reset  '} {STATE_FILE} (phase=setup, epoch=None, "
          f"{len(state['alive'])} seats alive)")
    return 1


def clear_family_channel(vault, dry):
    """The Family's candlelight council (../.bazaar/family/) — plaintext
    night proposals between Mafiosi. Stale ones must not leak into a fresh
    match; the epoch guard in the bots ignores them anyway, but the
    channel starts each match empty."""
    import glob as globmod
    fam = os.path.join(vault, "family")
    if not os.path.isdir(fam):
        return 0
    removed = 0
    for path in sorted(globmod.glob(os.path.join(fam, "c*-seat-*.json*"))):
        if remove(path, dry):
            removed += 1
    return removed


def clear_vault_journals(vault, dry):
    """Local journals (seat + Herald) live in the vault, outside the repo.
    A stale journal would make a restarted bot think it already acted."""
    if not os.path.isdir(vault):
        print(f"    vault   {vault} not present — no journals to clear")
        return 0
    removed = 0
    for name in sorted(os.listdir(vault)):
        if name.startswith(JOURNAL_PREFIXES):
            if remove(os.path.join(vault, name), dry):
                removed += 1
    return removed


def ensure_gitkeeps(dry):
    """Every folder that is supposed to be there gets a .gitkeep if missing."""
    made = 0
    for d in GITKEEP_DIRS:
        path = os.path.join(REPO_ROOT, d)
        keep = os.path.join(path, ".gitkeep")
        if not os.path.isdir(path):
            if not dry:
                os.makedirs(path, exist_ok=True)
            print(f"    {'would create' if dry else 'created  '} {d}/")
            made += 1
        if not os.path.exists(keep):
            if not dry:
                open(keep, "w").close()
            print(f"    {'would add' if dry else 'added    '} {d}/.gitkeep")
            made += 1
    return made


def commit_reset(dry, push):
    """Commit the wipe so the GM's next tick sees a clean arena."""
    if not dry and not confirm("Commit the reset to git?"):
        log("Reset left uncommitted — commit manually with: git add -A && git commit")
        return
    git = lambda *args: subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    r = git("add", "-A")
    if r.returncode != 0:
        log(f"git add failed (arena not committed): {r.stderr.strip()[:200]}")
        return
    r = git("diff", "--cached", "--quiet")
    if r.returncode == 0:
        log("Arena already clean — nothing to commit.")
        return
    if dry:
        log("dry-run: would commit the reset")
        return
    r = git("commit", "-m", COMMIT_MESSAGE)
    if r.returncode != 0:
        log(f"git commit failed: {r.stderr.strip()[:200]}")
        return
    log("Committed reset.")
    if push:
        if not confirm("Push the reset commit to the remote?"):
            log("Not pushed — push manually with: git push")
            return
        r = git("push")
        if r.returncode != 0:
            log(f"git push failed: {r.stderr.strip()[:200]}")
        else:
            log("Pushed reset to remote.")


def main():
    ap = argparse.ArgumentParser(
        description="Bazaar of Lies — full arena reset "
                    "(Python equivalent of setup/reset_match.sh).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be removed; touch nothing.")
    ap.add_argument("--push", action="store_true",
                    help="Push the reset commit to the remote after committing.")
    ap.add_argument("--wipe-recaps", action="store_true",
                    help="Also remove match recaps "
                         "(gameplay/village/match-XX-recap.md).")
    args = ap.parse_args()

    os.chdir(REPO_ROOT)
    # Journal vault resolution, in order: $VAULT, the sibling vault the bots
    # use (../.bazaar — see villager.py BAZAAR_DIR), then ~/.bazaar.
    vault = os.environ.get("VAULT")
    if not vault:
        sibling = os.path.join(os.path.dirname(REPO_ROOT), ".bazaar")
        vault = sibling if os.path.isdir(sibling) else os.path.expanduser("~/.bazaar")

    if args.dry_run:
        log("DRY RUN — no files will be touched")
        log(f"Resetting arena (vault: {vault})")
    else:
        print("This will WIPE all match artifacts from gameplay/ "
              "(votes, night, dossiers, deals, herald, usage, statements, "
              "day transcripts), rewrite graveyard.md and announcements.md, "
              f"reset gameplay/state.json to the pristine setup template, and "
              f"clear seat + Herald journals from {vault}.")
        if args.wipe_recaps:
            print("Match recaps WILL ALSO be removed (--wipe-recaps).")
        else:
            print("Match recaps are kept.")
        print("There is no undo.")
        if not confirm("Are you sure you want to reset the arena?"):
            log("Aborted — nothing was touched.")
            return 1
        log(f"Resetting arena (vault: {vault})")

    n = clear_artifact_dirs(args.dry_run)
    log(f"Cleared {n} artifact entries from {len(ARTIFACT_DIRS)} directories")
    n = remove_day_transcripts(args.dry_run)
    log(f"Removed {n} legacy day transcript(s)")
    if args.wipe_recaps:
        n = remove_recaps(args.dry_run)
        log(f"Removed {n} match recap(s)")
    n = rewrite_boards(args.dry_run)
    log(f"Rewrote {n} public board(s) to template")
    n = reset_state(args.dry_run)
    log(f"Reset {n} state file")
    n = clear_vault_journals(vault, args.dry_run)
    log(f"Cleared {n} journal(s) from vault")
    n = clear_family_channel(vault, args.dry_run)
    log(f"Cleared {n} family council proposal(s)")
    n = ensure_gitkeeps(args.dry_run)
    log(f"Folder/.gitkeep repairs: {n}")

    commit_reset(args.dry_run, args.push)

    log("Done. Start the bots and (optionally) tick the GM:")
    log("      tools/bazaar-launch.sh start && gh workflow run gm.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
