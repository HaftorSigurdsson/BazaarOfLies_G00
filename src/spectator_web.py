#!/usr/bin/env python3
"""Bazaar of Lies — Spectator Web UI (Flask).

Run with: uv run src/spectator_web.py
"""

import json
import os
from pathlib import Path

from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

@app.route("/")
def index():
    """Render the spectator dashboard."""
    state = _load_state()
    heralds = _load_heralds()
    statements = _load_statements()
    return render_template(
        "index.html",
        state=state,
        heralds=heralds,
        statements=statements,
    )

@app.route("/herald/<path:filename>")
def serve_herald(filename):
    """Serve Herald PDFs."""
    return send_from_directory("gameplay/library", filename)


def _load_state() -> dict:
    """Load the current game state."""
    try:
        with open("gameplay/state.json", "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _load_heralds() -> list:
    """Load recent Herald PDFs."""
    heralds = []
    for file in sorted(Path("gameplay/library").glob("herald-*.pdf"), reverse=True):
        heralds.append({
            "name": file.name,
            "path": f"/herald/{file.name}",
        })
    return heralds[:5]


def _load_statements() -> list:
    """Load recent statements."""
    statements = []
    for file in sorted(Path("gameplay/village/statements").glob("*.jsonl"), reverse=True):
        with open(file, "r") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    statements.append({
                        "seat": record.get("seat"),
                        "text": record.get("text"),
                        "cycle": record.get("cycle"),
                    })
                except json.JSONDecodeError:
                    continue
    return statements[:20]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)