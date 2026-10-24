# AGENTS.md — Bazaar of Lies: Omertà Edition

Guidelines for AI coding agents (and helpful humans) working in this repository.

## The Golden Rules

1. **Commit after major changes.** After completing a significant change
   (a feature, a fix, a refactor spanning files), `git add` the relevant
   files and `git commit` with a descriptive message. Do not leave major
   work uncommitted in the working tree.
2. **Always consider the CHANGELOG.** For every change, ask: *should this
   be an entry in `CHANGELOG.md`?* User-visible changes, behavioural
   changes, new files or scripts, fixes, and anything the operators of the
   arena would want to know belong there (Keep a Changelog style:
   Added / Changed / Fixed / Removed). If the change is truly trivial or
   invisible (typo, formatting), note why you skipped it.
3. **Versioning.** If the release is significant, bump `version` in
   `pyproject.toml` and add a matching `## [x.y.z] - YYYY-MM-DD` heading.

## Industry-standard agent conduct

- **Read before you write.** Read the file (and enough surrounding
  context) before editing it. Never edit a file you have not inspected.
- **Smallest coherent change.** Do what was asked; no speculative
  features, no drive-by refactors, no unrelated cleanup.
- **Match the house style.** Follow the existing code conventions,
  naming, and structure (`src/` for bot scripts, `gm/` for the Game
  Master, `docs/` for documentation).
- **Never push without explicit authorization.** Commits are local;
  `git push` (especially to `main`) needs the user's say-so. Never
  force-push. Prefer `git pull --rebase` over merge commits.
- **Never commit secrets.** API keys, `.key`/`.pem` files, and vaults
  must stay out of the repo (see `.gitignore`; private keys live in
  `~/.bazaar`, never in the tree).
- **Verify your work.** Run the relevant checks before declaring done:
  `uv run python -m py_compile src/*.py gm/*.py` for syntax, the
  project's smoke tests / manual runs for behaviour. Read the output —
  do not claim "tested" without an executed check.
- **Respect the game data.** `gameplay/` is live game state written by
  bots and the GM. Never hand-edit it as part of a code change; resets
  go through `setup/reset_match.sh`.
- **Document what you ship.** New or changed behaviour belongs in the
  matching `docs/` page (e.g. `docs/operations.md` for bot mechanics).
- **Ask when authorization is unclear**, not when implementation details
  are merely ambiguous — resolve routine choices from repo conventions.

## Project-specific gotchas

- Bot changes require restarting **all ten seats together plus the
  Herald window** (`tools/bazaar-launch.sh stop && tools/bazaar-launch.sh start`;
  on Windows use `tools/bazaar-launch.bat`).
- The villagers (`src/villager.py`) carry a **private notebook** memory in the vault
  journal — epoch-scoped, never in git. Master switch: `NOTEBOOK_ENABLED`.
- The Herald (`src/town-herald.py`) is **facts-only**: anything fed to
  villagers must be public, game-legitimate fact. PDF-only flourish
  (via `src/town-press.py`) never enters the markdown the merchants read.
- The PDF press prefers `tectonic` on `PATH`; it falls back to `fpdf2`.
