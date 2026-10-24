#!/usr/bin/env python3
"""bazaar-clock.py — local GM heartbeat for the bazaar.

Dispatches the GM workflow (gm.yml) every INTERVAL seconds and prints
a live status line each tick so you can see it's awake:
  - dispatch result (skipped if a GM run is still in progress)
  - live phase + cycle, read straight from the repo via the API
  - latest GM run status
Ctrl-C stops it cleanly.
"""
import base64
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ARENA_DIR = Path.home() / "Desktop" / "Bazaar"
WORKFLOW = "gm.yml"
INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # seconds; pass e.g. 120 for 2 min


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(args):
    cwd = ARENA_DIR if ARENA_DIR.is_dir() else None
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def repo_name():
    r = sh(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    return r.stdout.strip() if r.returncode == 0 else None


def dispatch(repo):
    args = ["gh", "workflow", "run", WORKFLOW]
    if repo:
        args += ["-R", repo]
    r = sh(args)
    if r.returncode == 0:
        log("✓ GM tick dispatched")
    else:
        log(f"✗ dispatch failed: {(r.stderr or r.stdout).strip()}")


def latest_run(repo):
    args = ["gh", "run", "list", f"--workflow={WORKFLOW}", "--limit", "1",
            "--json", "status,conclusion"]
    if repo:
        args += ["-R", repo]
    r = sh(args)
    try:
        return json.loads(r.stdout)[0]
    except Exception:
        return None


def live_phase(repo):
    if not repo:
        return None
    r = sh(["gh", "api", f"repos/{repo}/contents/state.json"])
    if r.returncode != 0:
        return None
    try:
        blob = json.loads(r.stdout)
        state = json.loads(base64.b64decode(blob["content"]))
        return state.get("phase"), state.get("cycle")
    except Exception:
        return None


def main():
    log(f"bazaar-clock awake — dispatching {WORKFLOW} every {INTERVAL}s. Ctrl-C to stop.")
    repo = repo_name()
    if repo:
        log(f"arena: {repo}")
    while True:
        if latest_run(repo) and latest_run(repo).get("status") == "in_progress":
            log("GM run still in progress — skipping dispatch")
        else:
            dispatch(repo)

        run = latest_run(repo)
        if run:
            concl = run.get("conclusion")
            log(f"latest GM run: {run.get('status')}" + (f" ({concl})" if concl else ""))
        p = live_phase(repo)
        if p and p[0]:
            log(f"live phase: {p[0]} — cycle {p[1]}")

        nxt = datetime.now() + timedelta(seconds=INTERVAL)
        log(f"sleeping — next tick {nxt.strftime('%H:%M:%S')}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("clock stopped")

