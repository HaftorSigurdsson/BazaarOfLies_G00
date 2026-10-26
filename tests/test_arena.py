"""The arena's regression suite.

Run from the repo root:  uv run python -m unittest discover -s tests -v

Covers the deterministic core that today's incidents actually hit: seat
parsing (the self-vote), statement records' ghost guards, the transcript
diet, the dawn delta, yesterday's tests join, edition numbering, the
first-night laws, and the launcher's environment checks. No model calls.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# villager.py parses argv and needs a key at import time
os.environ.setdefault("MISTRAL_API_KEY", "dummy-for-tests")
sys.argv = ["villager.py", "--seat", "seat-01"]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

import villager                                    # noqa: E402
from gm.utils import day_region, seat_from_label   # noqa: E402


def load_launcher():
    spec = importlib.util.spec_from_file_location(
        "bazaar_launch", REPO / "tools" / "bazaar-launch.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class SeatParsing(unittest.TestCase):
    """parse_seat_id must resolve every form — the self-vote match 1
    came from a ballot answer that led with the voter's own name."""

    def test_seat_forms(self):
        for text, want in [("seat-07", "seat-07"), ("seat-7", "seat-07"),
                           ("Gandalf", "seat-01"),       # by name
                           ("Gandalf (7)", "seat-07"),   # legacy label: the number IS the seat
                           ("I say Batman", "seat-04"),
                           ("(10)", "seat-10"), ("3", "seat-03")]:
            self.assertEqual(villager.parse_seat_id(text), want, text)

    def test_garbage_resolves_none(self):
        self.assertIsNone(villager.parse_seat_id("no merchant here"))
        self.assertIsNone(villager.parse_seat_id(""))

    def test_name_label_resolution(self):
        self.assertEqual(seat_from_label("Ripley"), "seat-05")
        self.assertEqual(seat_from_label("Neo (6)"), "seat-06")


class StatementMachinery(unittest.TestCase):
    def test_trim_statement(self):
        self.assertEqual(villager.trim_statement("short.", 100), "short.")
        long_text = ("One. " * 40).strip()
        trimmed = villager.trim_statement(long_text, 100)
        self.assertLessEqual(len(trimmed), 101)
        self.assertTrue(trimmed.endswith("."))

    def test_empty_never_passes(self):
        self.assertEqual(villager.trim_statement(None), "")
        self.assertEqual(villager.trim_statement(""), "")

    def test_silence_token_tail_is_stripped_not_confused(self):
        # the tail-strip rule from do_discussion: a full statement keeps its
        # body; a pure silence answer stays recognizable as silence
        body = "The ledger is clean. no contradictions yet. NO STATEMENT"
        self.assertFalse(body.strip().upper().startswith("NO STATEMENT"))
        stripped = re.sub(r"\s*NO\s+STATEMENT\s*$", "", body.strip(),
                          flags=re.IGNORECASE).strip()
        self.assertFalse(stripped.upper().endswith("NO STATEMENT"))
        self.assertTrue("NO STATEMENT".upper() != stripped.upper())

    def test_edition_number(self):
        spec = importlib.util.spec_from_file_location(
            "town_herald", REPO / "src" / "town-herald.py")
        th = importlib.util.module_from_spec(spec)
        sys.modules["town_herald"] = th
        saved_argv = sys.argv
        sys.argv = ["town-herald.py"]          # it parses argv at import
        try:
            spec.loader.exec_module(th)
        finally:
            sys.argv = saved_argv
        self.assertEqual(th.edition_number(1, "morning"), 1)
        self.assertEqual(th.edition_number(1, "evening"), 2)
        self.assertEqual(th.edition_number(3, "morning"), 5)
        self.assertEqual(th.edition_number(7, "evening"), 14)


class RegionsAndClock(unittest.TestCase):
    def test_day_region_sequence(self):
        now = datetime.now(timezone.utc)
        seen = []
        for minutes in (1, 7, 12, 17, 22):
            state = {"phase": "discussion",
                     "clock": {"dawn": (now - timedelta(minutes=minutes * 1.1)).isoformat(),
                               "discussion_deadline": (now + timedelta(minutes=26 - minutes * 1.1)).isoformat()}}
            seen.append(day_region(state)[0])
        self.assertEqual(seen, ["Morning", "Morning tea", "Lunch",
                                "Afternoon tea", "Dinner"])

    def test_voting_is_evening(self):
        self.assertEqual(day_region({"phase": "voting"})[0], "Evening")


class ReadingPipeline(unittest.TestCase):
    """Filesystem-backed: fixtures in a temp arena, restored after."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        os.makedirs("gameplay/village/statements", exist_ok=True)
        os.makedirs("gameplay/votes", exist_ok=True)
        os.makedirs("gameplay/herald", exist_ok=True)
        os.makedirs("setup", exist_ok=True)
        # display_name() reads the real roster; the fixture arena needs it too
        import shutil
        shutil.copy(REPO / "setup" / "seats.json", "setup/seats.json")

    def tearDown(self):
        os.chdir(self._cwd)

    def _statement(self, seat, seq, text, ts, epoch="e1", cycle=1,
                    name=None, dawn=None):
        rec = {"match": 1, "cycle": cycle, "seat": seat,
               "name": name, "seq": seq, "text": text,
               "epoch": epoch, "ts": ts}
        path = f"gameplay/village/statements/c{cycle:03d}-{seat}.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")

    def test_ghost_guards(self):
        self._statement("seat-01", 1, "real", "2026-10-25T10:00:00Z", epoch="e1")
        self._statement("seat-02", 1, "ghost (other epoch)",
                        "2026-10-25T10:00:10Z", epoch="old")
        self._statement("seat-03", 1, "ghost (before dawn)",
                        "2026-10-25T09:00:00Z", epoch="e1")
        recs = villager.recent_statement_records(1, epoch="e1",
                                                  dawn="2026-10-25T09:30:00Z")
        self.assertEqual([r["seat"] for r in recs], ["seat-01"])

    def test_duplicate_latest_ts_wins(self):
        self._statement("seat-01", 1, "first try", "2026-10-25T10:00:00Z")
        self._statement("seat-01", 1, "crash-resume rewrite",
                        "2026-10-25T10:00:05Z")
        recs = villager.recent_statement_records(1, epoch="e1")
        self.assertEqual(len(recs), 1)
        self.assertIn("rewrite", recs[0]["text"])

    def test_transcript_diet_window_and_marker(self):
        for i in range(10):
            self._statement(f"seat-{i + 1:02d}", 1, f"statement {i}",
                            f"2026-10-25T10:{i:02d}:00Z", name=f"Name{i}")
        state = {"cycle": 1, "epoch": "e1", "clock": {"dawn": None}}
        block = villager.transcript_block(state, since_iso="2026-10-25T10:05:00Z")
        self.assertIn("Most recent, verbatim", block)
        self.assertLessEqual(block.count("\n» "), villager.TRANSCRIPT_WINDOW + 1)
        self.assertTrue(block.count("statement 9") == 1)   # in the window
        self.assertIn("statement 0", block)               # via the digest/excerpt path

    def test_yesterday_tests_join(self):
        self._statement("seat-01", 1,
                        "If Batman is honest, his vote tonight will cite the clause.",
                        "2026-10-25T10:00:00Z", cycle=1, name="Gandalf")
        ballot = {"payload": {"seat": "seat-04", "target": "seat-07",
                               "epoch": "e1", "cycle": 1}}
        with open("gameplay/votes/seat-04-c001.json", "w") as f:
            json.dump(ballot, f)
        state = {"cycle": 2, "epoch": "e1", "match": 1}
        block = villager.yesterday_tests_block(state)
        self.assertIn("Gandalf tested", block)
        self.assertIn("Batman's ballot: Elsa", block)

    def test_yesterday_tests_silent_before_cycle_2(self):
        state = {"cycle": 1, "epoch": "e1"}
        self.assertEqual(villager.yesterday_tests_block(state), "")

    def test_delta_block_marks_seen_once(self):
        os.makedirs("gameplay/village", exist_ok=True)
        with open("gameplay/village/announcements.md", "w") as f:
            f.write("**2026-10-25T20:00:00Z**\n**Match 1, Cycle 1**\nThe bazaar awakens!\n\n---\n"
                    "**2026-10-25T21:00:00Z**\n**Banishment!** X, role: Villager\n\n---\n"
                    "**2026-10-25T22:00:00Z**\n**Match 2, Cycle 1**\nOther match\n\n---\n")
        journal = {}
        d1 = villager.delta_block({"match": 1}, journal)
        self.assertIn("NEW PUBLIC FACTS", d1)
        self.assertIn("Banishment", d1)
        self.assertNotIn("Other match", d1)     # foreign match filtered
        self.assertEqual(villager.delta_block({"match": 1}, journal), "")
        self.assertEqual(journal["ann_seen_ts"], "2026-10-25T21:00:00Z")


class LawsAndFirstNight(unittest.TestCase):
    def test_laws_block_renders(self):
        lb = villager.laws_block()
        self.assertIn("1.1 The budget", lb)
        self.assertIn("1.2.a", lb)
        self.assertIn("2.1 The first night", lb)
        self.assertIn("3.6 The ledger is public", lb)

    def test_hard_rules_block(self):
        hr = villager.hard_rules_block()
        self.assertIn("never break character", hr)
        self.assertIn("never reveal or reference your private doctrine", hr)

    def test_customs_cover_regions_and_free_dinner(self):
        for region in ("Morning", "Morning tea", "Lunch"):
            self.assertIn(region, villager.REGION_CUSTOMS)
        self.assertNotIn("Afternoon tea", villager.REGION_CUSTOMS)
        self.assertNotIn("Dinner", villager.REGION_CUSTOMS)


class LauncherChecks(unittest.TestCase):
    def test_gm_heartbeat_absent(self):
        m = load_launcher()
        self.assertTrue(callable(m.check_lock))
        self.assertTrue(callable(m.gm_heartbeat_age))
        self.assertTrue(callable(m.read_state))

    def test_check_lock_passes_on_consistent_repo(self):
        m = load_launcher()          # the real repo: pyproject == uv.lock
        m.check_lock()               # must not raise


if __name__ == "__main__":
    unittest.main()
