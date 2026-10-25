#!/usr/bin/env python3
"""Bazaar of Lies — Token usage logger.

Hook into villager.py and elder-council.py to log API calls to gameplay/usage/.
"""
import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

USAGE_DIR = "gameplay/usage"


def log_token_usage(
    script: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    temperature: float,
    reasoning_effort: str,
    cycle: Optional[int] = None,
    phase: Optional[str] = None,
) -> None:
    """Log token usage to gameplay/usage/tokens.csv."""
    os.makedirs(USAGE_DIR, exist_ok=True)
    match = _get_current_match()
    path = f"{USAGE_DIR}/match-{match:02d}/tokens.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow([
                "timestamp", "script", "model", "tokens_in", "tokens_out", 
                "temperature", "reasoning_effort", "cycle", "phase"
            ])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            script,
            model,
            tokens_in,
            tokens_out,
            temperature,
            reasoning_effort,
            cycle,
            phase,
        ])


def _get_current_match() -> int:
    """Get the current match number from state.json."""
    try:
        with open("gameplay/state.json", "r") as f:
            state = json.load(f)
            return state.get("match", 0)
    except (OSError, json.JSONDecodeError):
        return 0