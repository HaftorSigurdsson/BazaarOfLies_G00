#!/usr/bin/env python3
"""resolve-jsonl.py — repair merge-conflicted JSONL files in the arena.

When two bots append to a JSONL file in opposite orders, git leaves
conflict markers behind. This tool strips the markers, deduplicates
crash-resume duplicates (same seat+seq keeps the LATER timestamp), and
rewrites the file in timestamp order.

Usage:
    python3 tools/resolve-jsonl.py                 # all gameplay/village/**/*.jsonl
    python3 tools/resolve-jsonl.py file.jsonl ... # explicit files
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def resolve(path):
    text = path.read_text()
    if not any(m in text for m in MARKERS):
        return None                                   # nothing to fix
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(MARKERS):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  skipped unparsable line in {path.name}: {line[:60]!r}")
    # Dedupe: same (seat, seq) keeps the row with the later ts.
    best = {}
    for r in rows:
        key = (r.get("seat"), r.get("seq"))
        if key not in best or r.get("ts", "") >= best[key].get("ts", ""):
            best[key] = r
    ordered = sorted(best.values(), key=lambda r: r.get("ts", ""))
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                            for r in ordered))
    return len(ordered)


def main():
    paths = [Path(a) for a in sys.argv[1:]]
    if not paths:
        paths = sorted(REPO_ROOT.glob("gameplay/village/**/*.jsonl"))
    fixed = 0
    for p in paths:
        n = resolve(p)
        if n is not None:
            print(f"resolved: {p}  ({n} rows)")
            fixed += 1
    print(f"{fixed} file(s) repaired" if fixed else "no conflicted JSONL files found")


if __name__ == "__main__":
    main()
