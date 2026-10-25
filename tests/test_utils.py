#!/usr/bin/env python3
"""Unit tests for gm/utils.py."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gm.utils import (
    day_region,
    display_name,
    get_seats,
    is_alive,
    persona_name,
    read_state,
    seat_from_label,
    update_announcements,
    update_graveyard,
    write_state,
)


@pytest.fixture
def temp_state_file():
    """Fixture: temporary state.json."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "match": 1,
            "cycle": 1,
            "phase": "discussion",
            "alive": ["seat-01", "seat-02"],
            "clock": {
                "dawn": datetime.now(timezone.utc).isoformat(),
                "discussion_deadline": (datetime.now(timezone.utc) + 
                                        timedelta(minutes=25)).isoformat(),
            },
        }, f)
        f.flush()
        yield f.name
        os.unlink(f.name)


@pytest.fixture
def temp_seats_file():
    """Fixture: temporary seats.json."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "seats": {
                "seat-01": {"name": "Gandalf", "persona": "You are The Wizard."},
                "seat-02": {"name": "Batman", "persona": "You are The Knight."},
            }
        }, f)
        f.flush()
        yield f.name
        os.unlink(f.name)


@pytest.fixture
def temp_graveyard_file():
    """Fixture: temporary graveyard.md."""
    path = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
    yield path
    os.unlink(path)


def test_read_state(temp_state_file):
    """Test read_state()."""
    os.environ["STATE_FILE"] = temp_state_file
    state = read_state()
    assert state["match"] == 1
    assert state["cycle"] == 1
    assert state["phase"] == "discussion"


def test_write_state(temp_state_file):
    """Test write_state()."""
    os.environ["STATE_FILE"] = temp_state_file
    state = read_state()
    state["cycle"] = 2
    write_state(state)
    new_state = read_state()
    assert new_state["cycle"] == 2


def test_persona_name():
    """Test persona_name()."""
    assert persona_name("You are The Wizard. You see...") == "The Wizard"
    assert persona_name("You are The Knight.") == "The Knight"
    assert persona_name("") == "Unknown merchant"


def test_display_name(temp_seats_file):
    """Test display_name()."""
    os.environ["SEATS_FILE"] = temp_seats_file
    assert display_name("seat-01") == "Gandalf"
    assert display_name("seat-02") == "Batman"
    assert display_name("seat-99") == "seat-99"


def test_seat_from_label(temp_seats_file):
    """Test seat_from_label()."""
    os.environ["SEATS_FILE"] = temp_seats_file
    assert seat_from_label("Gandalf") == "seat-01"
    assert seat_from_label("Batman (2)") == "seat-02"
    assert seat_from_label("(01)") == "seat-01"
    assert seat_from_label("seat-01") == "seat-01"
    assert seat_from_label("Unknown") is None


def test_is_alive(temp_state_file):
    """Test is_alive()."""
    os.environ["STATE_FILE"] = temp_state_file
    assert is_alive("seat-01") is True
    assert is_alive("seat-03") is False


def test_day_region(temp_state_file):
    """Test day_region()."""
    os.environ["STATE_FILE"] = temp_state_file
    state = read_state()
    label, flavour = day_region(state)
    assert label in ["Morning", "Morning tea", "Lunch", "Afternoon tea", "Dinner"]


def test_update_announcements(temp_state_file):
    """Test update_announcements()."""
    os.environ["STATE_FILE"] = temp_state_file
    update_announcements("Test announcement")
    with open("gameplay/village/announcements.md", "r") as f:
        content = f.read()
    assert "Test announcement" in content


def test_update_graveyard(temp_state_file, temp_seats_file, temp_graveyard_file):
    """Test update_graveyard()."""
    os.environ["STATE_FILE"] = temp_state_file
    os.environ["SEATS_FILE"] = temp_seats_file
    Path("gameplay/village").mkdir(parents=True, exist_ok=True)
    
    update_graveyard("seat-01", "You are The Wizard.", "Villager", "Banished by town")
    with open("gameplay/village/graveyard.md", "r") as f:
        content = f.read()
    assert "Gandalf" in content
    assert "Villager" in content
    assert "Banished by town" in content