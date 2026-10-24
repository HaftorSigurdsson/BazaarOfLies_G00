#!/usr/bin/env python3
"""statements_assemble.py — assemble the per-seat statements into ONE file.

The per-seat statement files exist so ten bots never write to the same
file (no merge conflicts). This tool mirrors them into a single local
transcript per cycle:

    gameplay/village/statements/_assembled-c{CCC}.jsonl

The file is GITIGNORED — a local mirror only, never committed or pushed.
It is ALWAYS overwritten on each run. Bots do not depend on it (they
assemble the same view into their prompts themselves); it exists for the
humans watching the discussion, for grepping, and as a corpus snapshot.

Usage:
    uv run tools/statements_assemble.py                  # current cycle, once
    uv run tools/statements_assemble.py --cycle 3         # a specific cycle
    uv run tools/statements_assemble.py --watch           # keep it fresh (30 s)
    uv run tools/statements_assemble.py --watch 10        # every 10 s
    uv run tools/statements_assemble.py --ignore-epoch    # legacy/stale data OK
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

# The arena is the CURRENT working directory — run this tool from any
# clone (like the bots and the GM, which all use relative arena paths).
REPO_ROOT = Path.cwd()
STATE_FILE = REPO_ROOT / "gameplay" / "state.json"
SDIR = REPO_ROOT / "gameplay" / "village" / "statements"


def current_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def collect(cycle, epoch, ignore_epoch=False):
    """All statements of one cycle, ordered by ts, crash-resume duplicates
    deduped (later ts wins), foreign epochs invisible unless allowed."""
    recs = {}
    paths = sorted(glob.glob(str(SDIR / f"c{cycle:03d}-seat-*.jsonl")))
    # legacy double-named files (c001-seat-seat-01.jsonl) still count
    paths += [p for p in sorted(glob.glob(str(SDIR / f"c{cycle:03d}-*.jsonl")))
              if p not in paths]
    for path in paths:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue        # partial line mid-write by a bot
                    # strict, like the bots' own transcript view:
                    if not ignore_epoch and epoch is not None \
                            and rec.get("epoch") != epoch:
                        continue
                    ts = rec.get("ts", "")
                    key = (rec.get("seat"), rec.get("seq"))
                    if key not in recs or ts >= recs[key].get("ts", ""):
                        recs[key] = rec
        except OSError:
            continue
    return sorted(recs.values(), key=lambda r: r.get("ts", ""))


def assemble(cycle, epoch, ignore_epoch=False):
    recs = collect(cycle, epoch, ignore_epoch)
    out = SDIR / f"_assembled-c{cycle:03d}.jsonl"
    with open(out, "w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out, len(recs)


def main():
    ap = argparse.ArgumentParser(
        description="Assemble per-seat statements into one local "
                    "(gitignored) transcript per cycle.")
    ap.add_argument("--cycle", type=int, default=None,
                    help="cycle to assemble (default: the current cycle)")
    ap.add_argument("--ignore-epoch", action="store_true",
                    help="include records from any epoch (for finished matches)")
    ap.add_argument("--watch", nargs="?", const=30, type=int, default=None,
                    metavar="SEC",
                    help="keep re-assembling every SEC seconds (default 30)")
    args = ap.parse_args()

    while True:
        state = current_state()
        cycle = args.cycle if args.cycle is not None else state.get("cycle", 1)
        epoch = state.get("epoch")
        out, n = assemble(cycle, epoch, args.ignore_epoch)
        print(f"assembled {n} statement(s) -> {out.relative_to(REPO_ROOT)} "
              f"(local mirror, never committed)", flush=True)
        if not args.watch:
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
