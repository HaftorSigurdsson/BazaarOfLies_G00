#!/usr/bin/env python3
"""Unit tests for src/villager.py."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.villager import (
    cycle_state,
    load_journal,
    parse_seat_id,
    plain_speech_block,
    save_journal,
    trim_statement,
)


@pytest.fixture
def temp_journal_file():
    """Fixture: temporary journal file."""
    path = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False).name
    yield path
    Path(path).unlink()


def test_load_journal(temp_journal_file):
    """Test load_journal()."""
    journal = {"cycles": {}, "seen": [], "notebook": ""}
    with open(temp_journal_file, "w") as f:
        json.dump(journal, f)
    
    os.environ["JOURNAL_PATH"] = temp_journal_file
    loaded = load_journal()
    assert loaded == journal


def test_save_journal(temp_journal_file):
    """Test save_journal()."""
    journal = {"cycles": {}, "seen": [], "notebook": "test"}
    os.environ["JOURNAL_PATH"] = temp_journal_file
    save_journal(journal)
    
    with open(temp_journal_file, "r") as f:
        loaded = json.load(f)
    assert loaded == journal


def test_cycle_state(temp_journal_file):
    """Test cycle_state()."""
    journal = {"cycles": {}}
    with open(temp_journal_file, "w") as f:
        json.dump(journal, f)
    
    os.environ["JOURNAL_PATH"] = temp_journal_file
    cs = cycle_state(journal, "epoch", 1)
    assert cs == {"statements": 0, "last_statement_ts": 0, "voted": False, "night_action": False}


def test_parse_seat_id():
    """Test parse_seat_id()."""
    assert parse_seat_id("Gandalf") == "seat-01"
    assert parse_seat_id("Batman (2)") == "seat-02"
    assert parse_seat_id("(01)") == "seat-01"
    assert parse_seat_id("seat-01") == "seat-01"
    assert parse_seat_id("Unknown") is None


def test_trim_statement():
    """Test trim_statement()."""
    text = "This is a test statement. It should be trimmed."
    assert len(trim_statement(text, 20)) == 20
    assert trim_statement(text, 20).endswith(".")
    assert trim_statement("") == ""


def test_plain_speech_block():
    """Test plain_speech_block()."""
    block = plain_speech_block()
    assert "plain speech" in block
    assert "metaphor" in block