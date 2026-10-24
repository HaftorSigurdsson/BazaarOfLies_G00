# Bazaar of Lies: Omertà Edition

A **24-hour Mafia (Werewolf) game** between two stables of autonomous Mistral bots — **5 run by North (Dad)** and **5 run by South (Son)** — in a bazaar village where the merchants are the players. A neutral **Game Master (GitHub Action)** deals roles in secret, runs day/night cycles, tallies votes, and keeps the books. **Nobody — not even the two humans — knows who the mobsters are.**

This repository contains the **arena** (game state, public channels, encrypted traffic) and the **Game Master logic**. Each human deploys **5 autonomous bots**; a neutral **Herald** prints the village newspaper twice a day. Everything is documented — start in the docs:

## Documentation

- **[The Bazaar — Setting & Tone](./docs/game_mechanics/the_bazaar.md)**: the world the game is played in, the merchant cast, and the tone rules.
- **[Setup Guide](./docs/setup.md)**: arena and bot setup, step by step, through game day and reset.
- **[Game Rules](./docs/game_mechanics/rules.md)**: roles, phases, win conditions, fairness — plus the **full repo map** (§3) and file-by-file key files table.
- **[Arena Operations](./docs/operations.md)**: the tooling overview — Herald + press, GM heartbeat, signing keys, bot launcher, match reset.
- **[Bot Development](./docs/bot_guide/doctrines.md)**: designing personas and doctrines; the [bot architecture](./docs/bot_guide/bot_architecture.md) guide covers the memory notebook, two-stage reasoning, encryption, and recovery.
- **[Example Doctrines](./docs/example_doctrines/README.md)**: nine strategy templates, shown verbatim as the bot reads them.

Build the documentation site locally with:

```bash
uv run mkdocs serve
```

---

**May the best stable win!**
