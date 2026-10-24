#!/usr/bin/env python3
"""seats-pull.py — pull every seat clone and report state.

Usage:
    python3 seats-pull.py           # pull + report
    python3 seats-pull.py --no-pull # report only (no git side effects)
"""
import subprocess
import sys
from pathlib import Path

import os
GAME = Path(os.environ.get("BAZAAR_GAME_DIR") or Path.home() / "Desktop" / "GAME")
PULL = "--no-pull" not in sys.argv


def git(seat, *args):
    return subprocess.run(["git", "-C", str(seat), *args],
                          capture_output=True, text=True)


def main():
    seats = sorted(GAME.glob("seat-*"))
    if not seats:
        print("no seat clones found")
        return
    for seat in seats:
        if not (seat / ".git").exists():
            print(f"{seat.name}: (not a git clone, skipped)")
            continue

        if PULL:
            r = git(seat, "pull", "--rebase", "--quiet")
            if r.returncode != 0:
                err = (r.stderr or r.stdout).strip().splitlines()
                print(f"{seat.name}: ✗ pull failed — {err[-1] if err else 'unknown'}")
                continue

        head = git(seat, "log", "--oneline", "-1").stdout.strip()
        dirty = git(seat, "status", "--short").stdout.strip()
        flag = "  ⚠ DIRTY" if dirty else ""
        print(f"{seat.name}: ✓ {head}{flag}")
        if dirty:
            for line in dirty.splitlines()[:3]:
                print(f"          {line}")
    print("\n(all clones report their local HEAD; ⚠ marks uncommitted local changes)")


if __name__ == "__main__":
    main()
