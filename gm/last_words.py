#!/usr/bin/env python3
"""Bazaar of Lies — Last Words Prompt.

This script prompts a banished merchant (non-Family) for their last words,
which are published in the next morning edition of the Herald under "Last Words".

- Only non-Family merchants are prompted (Family members are excluded to avoid metagaming).
- Last words are stored in `gameplay/village/last_words.md` and referenced by the Herald.
- The prompt ensures brevity and prohibits revealing private information or roles.

Usage:
    from gm.last_words import ask_last_words
    last_words = ask_last_words(seat, role)
"""

import os
import sys

from mistralai.client import Mistral

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gm.utils import display_name

_client = None


def _get_client():
    """Lazily build the Mistral client — the cron GM runs without the key
    until a banishment actually needs last words."""
    global _client
    if _client is None:
        _client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return _client


def ask_last_words(seat: str, role: str) -> str:
    """Prompt a banished merchant for their last words."""
    prompt = (
        f"You are {display_name(seat)}, a {role} who has just been banished from the bazaar. "
        "Write your last words to the village. Keep it brief (1-2 sentences). "
        "Do not reveal private information or roles."
    )
    try:
        response = _get_client().chat.complete(
            model="mistral-small-2603",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Failed to get last words for {seat}: {e}", file=sys.stderr)
        return ""