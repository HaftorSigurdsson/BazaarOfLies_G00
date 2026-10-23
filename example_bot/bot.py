#!/usr/bin/env python3
import argparse
import json
import time
import subprocess
from mistralai import Mistral

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Bazaar of Lies Bot")
parser.add_argument("--seat", type=str, required=True, help="Seat ID (e.g., seat-01)")
args = parser.parse_args()

MODEL = "mistral-small-2409"  # PIN the exact versioned ID
MY_SEAT = args.seat           # Each bot knows only itself
client = Mistral()            # Reads MISTRAL_API_KEY


def ask(system, user, temperature=0.7):
    """Helper function to query the Mistral API."""
    r = client.chat.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=temperature
    )
    return r.choices[0].message.content


def get_persona(seat):
    """Load the bot's persona from setup/seats.json."""
    with open("setup/seats.json", "r") as f:
        seats = json.load(f)["seats"]
    return seats[seat]["persona"]


def get_doctrine(seat):
    """Load the bot's doctrine from a private file."""
    with open(f"doctrines/{seat}.txt", "r") as f:
        return f.read()


def get_role(seat):
    """Load the bot's role from its encrypted dossier."""
    # Decrypt the dossier using the bot's private key
    # (Implementation depends on your crypto setup)
    return "Villager"  # Placeholder


def push_statement(statement):
    """Push a public statement to village/day-XXX.jsonl."""
    state = json.load(open("state.json"))
    statement_data = {
        "match": state["match"],
        "cycle": state["cycle"],
        "seat": MY_SEAT,
        "seq": 1,
        "text": statement,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(f"village/day-{state['cycle']:03d}.jsonl", "a") as f:
        f.write(json.dumps(statement_data) + "\n")
    subprocess.run(["git", "add", f"village/day-{state['cycle']:03d}.jsonl"], check=True)
    subprocess.run(["git", "commit", "-m", f"Statement by {MY_SEAT}"], check=True)
    subprocess.run(["git", "push"], check=True)


def push_sealed_ballot(ballot):
    """Push a sealed ballot to votes/."""
    filename = f"votes/{MY_SEAT}-{int(time.time())}.enc"
    with open(filename, "w") as f:
        f.write(ballot)
    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", f"Ballot by {MY_SEAT}"], check=True)
    subprocess.run(["git", "push"], check=True)


def push_night_action(action):
    """Push a night action to night/."""
    filename = f"night/{MY_SEAT}-{int(time.time())}.enc"
    with open(filename, "w") as f:
        f.write(action)
    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", f"Night action by {MY_SEAT}"], check=True)
    subprocess.run(["git", "push"], check=True)


def main_loop():
    """Main loop for the bot."""
    while True:
        subprocess.run(["git", "pull", "--rebase"], check=True)
        s = json.load(open("state.json"))
        
        if s["phase"] == "discussion" and MY_SEAT in s["alive"]:
            statement = ask(
                f"You are {get_persona(MY_SEAT)}. Speak in character. Doctrine: {get_doctrine(MY_SEAT)}",
                "Write a public statement (≤ 600 chars)."
            )
            push_statement(statement)
        
        elif s["phase"] == "voting" and MY_SEAT in s["alive"]:
            vote = ask(
                f"You are {get_persona(MY_SEAT)}. Doctrine: {get_doctrine(MY_SEAT)}",
                "Who do you vote to banish? (Output only the seat ID, e.g., 'seat-02')"
            )
            push_sealed_ballot({"match": s["match"], "cycle": s["cycle"], "seat": MY_SEAT, "vote": vote})
        
        elif s["phase"] == "night" and MY_SEAT in s["alive"]:
            action = ask(
                f"You are {get_persona(MY_SEAT)}. Your role is {get_role(MY_SEAT)}.",
                "Submit your night action (Output only the seat ID, e.g., 'seat-02')."
            )
            push_night_action({"match": s["match"], "cycle": s["cycle"], "seat": MY_SEAT, "target": action})
        
        time.sleep(30)


if __name__ == "__main__":
    main_loop()