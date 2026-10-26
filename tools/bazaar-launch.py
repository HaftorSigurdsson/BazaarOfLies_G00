#!/usr/bin/env python3
"""bazaar-launch.py — start/stop/status the bazaar bots (+ the Herald).

The cross-platform launcher core. Thin wrapper: tools/bazaar-launch.sh
(macOS/Linux; the retired .bat wrapper lives in tools/STORE/).

Usage:
    python3 tools/bazaar-launch.py start            # all default seats + Herald
    python3 tools/bazaar-launch.py start 01 03 05   # a subset of seats
    python3 tools/bazaar-launch.py start --no-herald
    python3 tools/bazaar-launch.py stop
    python3 tools/bazaar-launch.py status

How it runs, by platform (auto-detected):
    macOS/Linux: one tmux session ("bazaar"), one window per seat, one
                 window for the Herald. The MISTRAL_API_KEY is pushed
                 into the session explicitly, so a stale tmux server can
                 never leak an old or empty key. On macOS the session is
                 wrapped in `caffeinate -i` so the machine keeps working.
    Windows:     one new console window per seat (+ Herald), via
                 `cmd /k` so a crashed bot leaves its traceback on
                 screen. PIDs are recorded in GAME_DIR/.bazaar-launch.json
                 for stop/status (taskkill /T kills the whole tree).

Environment:
    MISTRAL_API_KEY   required for start (the bots and the Herald need it)
    BAZAAR_GAME_DIR   seat clones (default ~/Desktop/Game/seat-XX)
    BAZAAR_HERALD_DIR Herald clone (default: this repo)
"""
import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

SESSION = "bazaar"
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
REPO_ROOT = Path(__file__).resolve().parents[1]
GAME_DIR = Path(os.environ.get("BAZAAR_GAME_DIR")
                or Path.home() / "Desktop" / "Game")
HERALD_DIR = Path(os.environ.get("BAZAAR_HERALD_DIR") or REPO_ROOT)
PID_FILE = GAME_DIR / ".bazaar-launch.json"
SEATS_DEFAULT = [f"{i:02d}" for i in range(1, 11)]


def log(msg):
    print(msg, flush=True)


def tmux(*args, check=True):
    return subprocess.run(["tmux", *args], check=check, capture_output=True,
                          text=True)


def has_session():
    if IS_WINDOWS:
        return PID_FILE.exists()
    r = tmux("has-session", "-t", SESSION, check=False)
    return r.returncode == 0


def check_key():
    if not os.environ.get("MISTRAL_API_KEY"):
        log("ERROR: MISTRAL_API_KEY is not set in this shell.")
        log('       export MISTRAL_API_KEY="..." and retry.')
        sys.exit(1)


def check_lock():
    """The uv.lock trap (twice bitten, 2026-10-25/26): a pyproject version
    bump without a regenerated lock makes every `uv run` dirty the lock in
    every seat clone, which breaks their `git pull --rebase` and crash-loops
    all bots (git exit 128). Refuse to start into a broken environment."""
    import re
    try:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text()
        lock = (REPO_ROOT / "uv.lock").read_text()
    except OSError:
        return                          # nothing to check against
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    if not m:
        return
    ver = m.group(1)
    need = [l for l in lock.splitlines()
            if l.startswith("version =") and f'"{ver}"' in l] \
        if f'"{ver}"' in lock else []
    # uv.lock records the project's own version under its [[package]] name
    if not need:
        log(f"ERROR: pyproject says {ver} but uv.lock does not contain it.")
        log("       Run `uv lock`, commit BOTH files, push — then start.")
        sys.exit(1)


def read_state():
    try:
        return json.loads((REPO_ROOT / "gameplay" / "state.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def gm_heartbeat_age():
    """Seconds since the GM's last tick (gm-cron.log's mtime); None if the
    log cannot be found (a non-cron GM driver, or a different layout)."""
    candidates = [Path.home() / "Desktop" / "Game" / "game_master"
                  / "gm-cron.log",
                  GAME_DIR.parent / "game_master" / "gm-cron.log"]
    for c in candidates:
        if c.exists():
            import time
            return time.time() - c.stat().st_mtime
    return None


def window_titles():
    return [f"seat-{s}" for s in SEATS_DEFAULT]


def cmd_start(args):
    check_key()
    check_lock()
    seats = args.seats or SEATS_DEFAULT
    clones = [GAME_DIR / f"seat-{s}" for s in seats]
    missing = [c for c in clones if not c.is_dir()]
    if missing:
        log(f"ERROR: no clone at {missing[0]}")
        sys.exit(1)
    if not args.no_herald and not (HERALD_DIR / "src" / "town-herald.py").is_file():
        log(f"ERROR: no Herald at {HERALD_DIR}/src/town-herald.py")
        sys.exit(1)
    if has_session():
        log(f"ERROR: {SESSION} is already running — run 'stop' first.")
        sys.exit(1)

    if IS_WINDOWS:
        # One console per bot; `cmd /k` keeps the window open on a crash.
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        pids = {}
        for seat, clone in zip(seats, clones):
            p = subprocess.Popen(
                ["cmd", "/k", f"uv run src/villager.py --seat seat-{seat}"],
                cwd=str(clone), creationflags=flags)
            pids[f"seat-{seat}"] = p.pid
        if not args.no_herald:
            p = subprocess.Popen(
                ["cmd", "/k", "uv run src/town-herald.py"],
                cwd=str(HERALD_DIR), creationflags=flags)
            pids["herald"] = p.pid
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(json.dumps(pids, indent=2))
        log(f"launched {len(pids)} window(s): {', '.join(pids)}")
        return

    if not subprocess.run(["which", "tmux"], capture_output=True).returncode == 0:
        log("ERROR: tmux is not installed (apt install tmux / brew install tmux).")
        sys.exit(1)
    # Fresh session; wrap in caffeinate on macOS so the machine never sleeps.
    new = ["new-session", "-d", "-s", SESSION]
    if IS_MAC and subprocess.run(["which", "caffeinate"],
                                 capture_output=True).returncode == 0:
        subprocess.Popen(["caffeinate", "-i", "tmux", *new])
    else:
        tmux(*new)
    # Bug-proofing: push the key from THIS shell into the session explicitly.
    tmux("set-environment", "-t", SESSION, "MISTRAL_API_KEY",
         os.environ["MISTRAL_API_KEY"])
    for seat, clone in zip(seats, clones):
        tmux("new-window", "-d", "-t", SESSION, "-n", f"seat-{seat}",
             "-c", str(clone), f"uv run src/villager.py --seat seat-{seat}")
    if not args.no_herald:
        tmux("new-window", "-d", "-t", SESSION, "-n", "herald",
             "-c", str(HERALD_DIR), "uv run src/town-herald.py")
    log(f"launched {len(seats)} seat(s): {' '.join(seats)}"
        + ("" if args.no_herald else " + herald"))
    log(f"  tmux attach -t {SESSION}    (Ctrl-b n: next window, Ctrl-b d: detach)")


def cmd_stop(args):
    if not has_session():
        log(f"no session '{SESSION}' running")
        return
    if IS_WINDOWS:
        for name, pid in json.loads(PID_FILE.read_text()).items():
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True)
        PID_FILE.unlink(missing_ok=True)
    else:
        tmux("kill-session", "-t", SESSION)
    log(f"stopped '{SESSION}' (bots are journal-safe; restart any time)")


def cmd_status(args):
    # the GM's heartbeat first: a stale log with a live game means the
    # arena is frozen, not resting
    state = read_state()
    hb = gm_heartbeat_age()
    if hb is not None and state.get("phase") not in ("halted", None) \
            and hb > 600:
        log(f"⚠ GM HEARTBEAT STALE: last tick {int(hb / 60)} min ago "
            f"while phase is {state.get('phase')!r} — the arena may be "
            f"frozen. Check the crontab and game_master/gm-cron.log.")
    if not has_session():
        log(f"no session '{SESSION}' running")
        sys.exit(1)
    if IS_WINDOWS:
        for name, pid in json.loads(PID_FILE.read_text()).items():
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                               capture_output=True, text=True)
            alive = str(pid) in r.stdout
            log(f"{name:<10} {'RUNNING' if alive else 'DEAD (window closed?)'}")
        return
    out = tmux("list-windows", "-t", SESSION, "-F", "#W").stdout
    for w in out.splitlines():
        if not w:
            continue
        cap = tmux("capture-pane", "-p", "-t", f"{SESSION}:{w}",
                   "-S", "-50", check=False).stdout
        lines = [l for l in cap.splitlines() if l.strip()]
        tail = lines[-1] if lines else "<no output yet>"
        # red flags: a pane stuck on an error is retrying (amber) or dead
        joined = " ".join(lines[-5:]).lower()
        if "needs a human" in joined or "traceback" in joined:
            tail = "🔴 " + tail
        elif "error" in tail.lower() or "exit status 128" in tail.lower():
            tail = "🟠 " + tail
        log(f"{w:<10} {tail}")


def cmd_restart_safe(args):
    """Restart at a phase boundary: immediately in setup/halted, or once
    the night's watches have run (the actions are sealed and the seats
    are idle). Never mid-discussion or mid-vote."""
    import time as _t
    log("waiting for a safe restart point (Ctrl-C to abort)...")
    waited = 0
    while waited < 3600:
        state = read_state()
        phase = state.get("phase")
        if phase in ("setup", "halted"):
            log(f"phase={phase!r} — safe point, restarting now")
            break
        if phase == "night":
            end = state.get("clock", {}).get("night_deadline")
            if end:
                from datetime import datetime, timezone
                try:
                    remaining = (datetime.fromisoformat(end)
                                 - datetime.now(timezone.utc)).total_seconds()
                except ValueError:
                    remaining = None
                if remaining is not None and remaining <= 5 * 60:
                    log("night: watches are done — safe point, restarting")
                    break
        _t.sleep(10)
        waited += 10
    else:
        log("no safe point within an hour — restarting anyway")
    cmd_stop(args)
    cmd_start(args)


def main():
    ap = argparse.ArgumentParser(description="Bazaar of Lies — bot launcher")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start", help="launch seats (+ Herald) in one session")
    p.add_argument("seats", nargs="*", help="seat numbers, e.g. 01 03 05 "
                    f"(default: {' '.join(SEATS_DEFAULT)})")
    p.add_argument("--no-herald", action="store_true",
                   help="do not launch the Herald window")
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("stop", help="kill the session (journal-safe)")
    p.set_defaults(fn=cmd_stop)
    p = sub.add_parser("status", help="one-line heartbeat per window "
                    "(red flags errors, stale GM heartbeat)")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("restart-safe", help="restart at a phase boundary "
                    "(setup/halted, or the night's last watch — never "
                    "mid-discussion or mid-vote)")
    p.add_argument("seats", nargs="*")
    p.add_argument("--no-herald", action="store_true")
    p.set_defaults(fn=cmd_restart_safe)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
