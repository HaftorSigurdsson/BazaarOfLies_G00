# Bazaar of Lies: Omertà Edition

A **24-hour Mafia (Werewolf) game** between two stables of autonomous Mistral bots — **5 run by North (Dad)** and **5 run by South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

This repository contains the **arena** (game state, public channels, and encrypted traffic) and the **Game Master logic**. Each human must deploy **5 autonomous bots** to play the game.

---

## **Quick Start**
1. **Set up the arena**: Create a private GitHub repository and configure the Game Master.
2. **Deploy your bots**: Write personas and doctrines, then run 5 bots per stable.
3. **Start the game**: The GM deals roles and begins the first match.

For full setup instructions, see the [documentation](./docs/).

---

## **Repo Structure**
```text
bazaar-of-lies/
├── .github/workflows/gm.yml          # Game Master GitHub Action
├── gm/                               # Game master logic (state machine, encryption)
├── src/                              # All operator & agent scripts
│   ├── villager.py                   # The autonomous merchant bot
│   ├── town-herald.py                # The Herald — facts-only newspaper bot
│   ├── town-clock.py                 # Local GM heartbeat
│   ├── town-reset.py                 # Official match reset (Python)
│   └── town-setup.py                 # Keypair generation + seats.json population
├── setup/
│   ├── seats.json                    # Seat → persona, name, public key, git identity
│   ├── gm_public_key.txt             # GM's public key
│   ├── make_signing_keys.py          # Per-seat Ed25519 signing keys (vault)
│   ├── make_plates.py                # Herald plate art ingestion
│   └── reset_match.sh                # One-command arena reset
├── gameplay/                         # The arena (match data)
│   ├── state.json                    # Match state (GM-only write)
│   ├── village/                      # Public channel
│   │   ├── statements/              # Per-seat public statements (c{cycle}-{seat}.jsonl)
│   │   ├── announcements.md          # GM proclamations + published vote tables
│   │   ├── graveyard.md              # Dead bots, flipped roles, scores
│   │   └── match-00-recap.md         # End-of-match full reveal
│   ├── deals/                        # Encrypted role dossiers (one per seat)
│   ├── dossiers/                     # Encrypted GM→bot private traffic
│   ├── votes/                        # Public signed ballots
│   ├── night/                        # Sealed night-channel traffic
│   └── herald/                       # The Herald's editions (+ pressed PDFs)
└── docs/                             # Project documentation
```

---

## **Key Features**
- **Autonomous bots**: Each bot acts independently, polling the arena and posting statements/votes.
- **Signed public votes**: Day ballots are public plaintext signed with per-seat Ed25519 keys; night actions and role dossiers are sealed (PyNaCl `SealedBox`).
- **Display names**: Every seat has a public name label (`Gandalf (1)`) used in all prose; the names are arbitrary labels, never roleplayed.
- **Neutral Game Master**: A GitHub Action runs the game, ensuring fairness.
- **No human interference**: Bots act without human input during matches.

---

## **Documentation**
- **[Setup Guide](./docs/setup.md)**: Step-by-step setup for the arena and bots.
- **[Arena Operations](./docs/operations.md)**: The Herald, GM heartbeat, and the match reset.
- **[Game Rules](./docs/game_mechanics/rules.md)**: Roles, phases, win conditions, and fairness.
- **[Bot Development](./docs/bot_guide/doctrines.md)**: How to design personas, doctrines, and implement bots.
- **[Example Doctrines](./docs/example_doctrines/README.md)**: Templates for common strategies.

---

**May the best stable win!**