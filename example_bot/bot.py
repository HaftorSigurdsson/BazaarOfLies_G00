#!/usr/bin/env python3
import argparse
import json
import time
import subprocess
from mistralai import Mistral

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Bazaar of Lies Bot")
parser.add_argument("--seat", type=str, required=True, help="Seat ID (e.g., seat-01)")
parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
args = parser.parse_args()

MODEL = "mistral-small-2409"  # PIN the exact versioned ID
MY_SEAT = args.seat           # Each bot knows only itself
VERBOSE = args.verbose        # Verbose logging
client = Mistral()

MODEL = "mistral-small-2409"  # PIN the exact versioned ID
MY_SEAT = "seat-01"           # Each bot knows only itself
client = Mistral()             # Reads MISTRAL_API_KEY

# Sub-agent prompts
ANALYST_SYS = """
You are the Analyst for {persona}. Your job is to summarize the day's events and flag contradictions.
- Focus on who accused whom and who defended whom.
- Keep your summary under 500 tokens.
- Use bullet points for clarity.
"""

SPEECHWRITER_SYS = """
You are the Speechwriter for {persona}. Your job is to write 1-2 public statements per day.
- Speak in character (use your persona's voice).
- Keep each statement under 600 characters.
- Follow your doctrine: {doctrine}
"""

STRATEGIST_SYS = """
You are the Strategist for {persona}. Your job is to decide who to vote for.
- Weigh accusations and defenses.
- Follow your doctrine: {doctrine}
- Output only the seat ID of your target (e.g., "seat-02").
"""

NIGHT_AGENT_SYS = """
You are the Night Agent for {persona}. Your role is {role}.
- If Mafia, confer with teammates and submit a kill target.
- If Detective, submit an investigation target.
- If Doctor, submit a protection target.
- Output only the seat ID of your target (e.g., "seat-02").
"""

def ask(system, user, temperature=0.7, max_tokens=500):
    """Helper function to query the Mistral API with token limits."""
    if VERBOSE:
        print(f"[VERBOSE] System prompt: {system}")
        print(f"[VERBOSE] User prompt: {user}")
    
    r = client.chat.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    if VERBOSE:
        print(f"[VERBOSE] Response: {r.choices[0].message.content}")
    
    log_usage(MY_SEAT, r.usage)
    return r.choices[0].message.content

def analyst_phase(cycle_context):
    """Summarize the day's events."""
    summary = ask(ANALYST_SYS.format(persona=get_seats()[MY_SEAT]["persona"]), cycle_context, max_tokens=500)
    return summary

def speechwriter_phase(summary):
    """Write 1-2 public statements."""
    statements = []
    for _ in range(2):
        statement = ask(SPEECHWRITER_SYS.format(
            persona=get_seats()[MY_SEAT]["persona"],
            doctrine=get_doctrine(MY_SEAT)
        ), summary, max_tokens=300)
        statements.append(statement)
    return statements

def strategist_phase(summary):
    """Decide who to vote for."""
    vote = ask(STRATEGIST_SYS.format(
        persona=get_seats()[MY_SEAT]["persona"],
        doctrine=get_doctrine(MY_SEAT)
    ), summary, max_tokens=50)
    return vote

def night_agent_phase(cycle_context):
    """Perform night actions based on role."""
    role = get_role(MY_SEAT)
    if role == "Mafia":
        target = ask(NIGHT_AGENT_SYS.format(persona=get_seats()[MY_SEAT]["persona"], role=role), cycle_context, max_tokens=50)
        return {"type": "kill", "target": target}
    elif role == "Detective":
        target = ask(NIGHT_AGENT_SYS.format(persona=get_seats()[MY_SEAT]["persona"], role=role), cycle_context, max_tokens=50)
        return {"type": "investigate", "target": target}
    elif role == "Doctor":
        target = ask(NIGHT_AGENT_SYS.format(persona=get_seats()[MY_SEAT]["persona"], role=role), cycle_context, max_tokens=50)
        return {"type": "save", "target": target}
    return None

def get_doctrine(seat):
    """Load the bot's doctrine from a private file."""
    with open(f"doctrines/{seat}.txt", "r") as f:
        return f.read()

def get_role(seat):
    """Load the bot's role from its encrypted dossier."""
    # Decrypt the dossier using the bot's private key
    ...

def log_usage(seat, usage):
    """Log token usage to usage/seat-XX.jsonl."""
    with open(f"usage/{seat}.jsonl", "a") as f:
        f.write(json.dumps({"tokens": usage.total_tokens, "timestamp": time.time()}) + "\n")

def main_loop():
    """Main loop for the bot."""
    while True:
        subprocess.run(["git", "pull", "--rebase"], check=True)
        s = json.load(open("state.json"))
        
        if s["phase"] == "discussion" and is_alive(MY_SEAT):
            cycle_context = get_cycle_context()
            summary = analyst_phase(cycle_context)
            statements = speechwriter_phase(summary)
            for statement in statements:
                push_statement(statement)
        
        elif s["phase"] == "voting" and is_alive(MY_SEAT):
            cycle_context = get_cycle_context()
            summary = analyst_phase(cycle_context)
            vote = strategist_phase(summary)
            push_sealed_ballot(seal_for_gm({"match": s["match"], "cycle": s["cycle"], "seat": MY_SEAT, "vote": vote}))
        
        elif s["phase"] == "night" and is_alive(MY_SEAT):
            cycle_context = get_cycle_context()
            action = night_agent_phase(cycle_context)
            if action:
                push_night_action(seal_for_gm({"match": s["match"], "cycle": s["cycle"], "seat": MY_SEAT, **action}))
        
        time.sleep(30)

if __name__ == "__main__":
    main_loop()