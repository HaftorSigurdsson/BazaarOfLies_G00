# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2026-10-24
### Added
- **Woodcut engraving plate** (`town-press.py`): a high-contrast plate generated once from the bazaar banner (`docs/assets/images/bazaar-engraving.png`) is printed under the headline in both the LaTeX engine and the fpdf2 fallback. A missing plate never breaks a paper.
- **"The Weather & The Market" (press)**: PDF-only filler box at the foot of the page — one deterministic weather line + one market-prices line per edition, alongside the existing Whisper column.
- **Herald "Letter to the Editor"**: when public statements exist, the paper closes with one statement quoted verbatim, attributed to its seat, with at most a one-line neutral introduction — never edited, never commented on.
- **Vote participation stats**: once the GM publishes ballot tables, "By the Numbers" reports each seat's participation across all published ballots (casts/tables, with abstentions); ballot tallies now also count abstentions.

## [1.3.0] - 2026-10-24
### Added
- **Herald "By the Numbers"**: every edition now carries a machine-counted stats section — seats alive/dead, per-seat statement counts for the cycle, who has been silent, and the quiet-night streak — all derived from public facts only.
- **Herald "The Voting Record"**: when the GM publishes signed ballot tables in the announcements, the Herald reports the last two tallies (result + counts, no editorialising).
- **"The Bazaar Whisper" (press)**: a PDF-only humour column at the foot of the front page — 16 non-game items, deterministically picked per edition (match/cycle/part). It never enters the markdown the merchants read, so it cannot become game input. Rendered in both the LaTeX engine and the fpdf2 fallback.

### Changed
- `EDITION_MAX_CHARS` 2800 → 3600 and the villagers' paper-read limit 3000 → 4000, so the new sections reach the merchants without truncation.
- Updated the sample front page (`docs/assets/herald-sample-morning.{md,pdf}`) to show the new sections.

## [1.2.0] - 2026-10-24
### Fixed
- **Ghost-replay bug (match echo)**: a partial reset that re-used the match number caused the GM to re-count the finished match's stale ballots and night actions — banishments replayed in the same order and old statements haunted transcripts. Every deal now mints an **epoch**; ballots, night actions, statements, dossier receipts and bot journal keys are all epoch-scoped, and the GM additionally rejects anything timestamped before the current cycle's dawn. A sloppy reset can no longer resurrect a finished match.
- **Family friendly-fire**: the Mafia could (and did) kill its own member (seat-09, Match 1). The GM now discards kill submissions that target a fellow Family member (registry-checked), and bots are explicitly instructed never to target teammates.
- **Kill tie-break** is now secure-random, not "last submission wins".
- **Win check runs right after the tally** — a banishment that ends the match no longer wastes a night before the recap.
- **Match auto-chain**: the deal phase no longer hard-resets the match number to 1 — `end_match`'s "next match is N" now survives, so consecutive matches number 1, 2, 3… and recap files no longer overwrite each other.
- **Statement filename**: `c{cycle}-{seat}.jsonl` (was `c{cycle}-seat-{seat}.jsonl`).
- **Transcript dedupe**: crash-resume duplicates now resolve to the later timestamp.
- **Graveyard markdown**: rows are inserted into the main table (were appended after the Scores table, mangling the file); persona column now holds the short merchant name.
- **Announcements** use short merchant names instead of full persona paragraphs.

### Added
- **Public day votes**: sealed ballots replaced by plaintext ballots `{seat, cycle, target, rationale, ts}` signed with per-seat **Ed25519** keys (`setup/make_signing_keys.py` registers public keys in `setup/seats.json`; private keys live in the operator's vault). The GM verifies every signature and publishes the full vote table in the announcements. Night actions remain sealed to the GM.
- **The Herald** (`editor.py`): facts-only newspaper bot, morning edition on discussion, evening edition on night; `news/herald-cXXX-{morning,evening}.md`; journal-guarded against double printing.
- **Night prompt context**: alive seats, public obituaries and role-specific guidance (the old night prompt had no game context at all, so targets were arbitrary).
- **Public facts block** in discussion/vote prompts: alive seats + graveyard roll.
- **`setup/reset_match.sh`**: one-command full arena reset (artifacts + boards + state template + journals), replacing the error-prone manual checklist.

### Notes
- Bot changes require restarting all ten seats together (plus the Herald window): `./bazaar-launch.sh stop && ./bazaar-launch.sh start`.
- Run `python3 setup/make_signing_keys.py --vault ~/.bazaar` once BEFORE the next match; commit the updated `setup/seats.json`.

## [1.1.0] - 2026-10-23
### Added
- **Dynamic Role Assignment**: Roles are rebalanced between matches based on the previous match’s outcome.
- **Sub-Agent Framework**: Bots are split into Analyst, Speechwriter, and Strategist sub-agents.
- **GM Penalty for Silence**: Bots silent for 2 consecutive days receive an automatic vote.
- **Token Budget Enforcement**: Enforces the 10,000-token limit per bot per cycle.
- **Setup Scripts**: `setup.py` automates keypair generation and `seats.json` population.
- **GM Action Reliability**: Dynamic cron scheduling and manual triggers for testing.
- **Encryption Improvements**: Key validation and ephemeral keys for matches.

- **Debugging Tools**: Verbose mode for bots (`--verbose` flag).

### Changed
- Updated `README.md` and `setup/rules.md` to reflect improvements.
- Adjusted win conditions to reduce Mafia advantage.

### Fixed
- GM Action race conditions with concurrency control.
- Encryption failures with key validation.

## [1.0.0] - 2026-10-20
### Added
- Initial release of *Bazaar of Lies: Omertà Edition*.
- Core game logic (GM, roles, phases, encryption).
- Example personas and doctrines.