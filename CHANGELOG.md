# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-10-24
### Added
- **PERSONALS** (press, PDF-only): a classifieds box between the Weather & Market and the Whisper — two in-theme ads per edition from a 14-item deterministic pool ("LOST: one brass key, opens nothing the owner will admit", "SEEKING WORK: scribe, discreet, remembers nothing by morning"). Never enters the markdown the merchants read. Rendered in both engines; samples re-pressed, still one A4 page.
- **Editorial continuity** (Herald): before writing, the Herald re-reads its own last two editions (public record, most recent first, truncated to 1600 chars each) and the system prompt invites a one-line follow-up on its own reporting — or a plain statement when today's facts differ from yesterday's paper. Same-match only; cycle 1 mornings start clean.

## [2.0.0] - 2026-10-24
### Added
- **The Herald has a voice**: the system prompt now writes as a 19th-century town paper — ink-stained, thrifty with words, dryly witty, vintage flourishes used sparingly — while keeping the facts-only doctrine byte-for-byte.
- **The Tally (election-returns chart)**: computed by the Herald from the latest public ballot table (never model-written, exact to the ballot) and appended to every edition as a fenced text chart — small-caps header, ballots and abstentions counted, one solid `▓` bar per candidate. The **press re-renders it as an old-style bar graph** in the PDF: ruled frame, small-caps caption, solid black bars on a common baseline (LaTeX tabular rules in the fine edition, filled rects in the fpdf2 fallback). Verified by raster inspection in both engines, still one A4 page.
- **Masthead motto**: *"All the facts fit to print — the rumours you may trade elsewhere."* under the dateline in both engines.
### Changed
- The model is explicitly told **not** to write a voting-record section (the computed chart is authoritative; it may summarise the result in one sentence). The evening sample carries the new Tally section and has been re-pressed.

## [1.9.1] - 2026-10-24
### Added
- **`shuttered-stall` plate**: dedicated night-result motif (closed stall, padlock, single lamp — ingested in final grayscale 3:1 format). A stall-shuttered edition now earns it instead of the interim sunset plate.
- **Three new scenery motifs** (40 plates total): quiet-evening-marked (quiet/calm/peaceful evening), thriving-marked-evening (thriving/brisk trade/bustling), and market-day-animals (livestock/donkeys/goats/geese) — each wired into the keyword rules above the generic market rule. The raw/ folder was also reorganized (finished plates kept, raw sources pruned to the new arrivals).
### Fixed
- **Vocabulary alignment residuals**: win conditions now read "Town wins if all the Mafia have left the bazaar" (rules + index); the graveyard tree entry says "Departed merchants, revealed roles"; "roles revealed at death" → "revealed on departure" everywhere (Herald digest, villagers' public facts, docstrings); "seats alive/dead" → "alive/departed"; the sample papers say "among the departed". Full sweep re-run: no violence terms remain outside the accepted exceptions (historical CHANGELOG, legacy `Night kill` parsers, tmux/taskkill process terms).

## [1.9.0] - 2026-10-24
### Changed
- **Family-friendly vocabulary** (full sweep, code and docs): nobody is ever killed, murdered, or found dead.
  - **Night result** (public): the GM announcement is now `**Stall shuttered!** {name}, {merchant}, shuttered their stall and left the bazaar overnight. Their role was: …` — the softer variant, no fire. The graveyard cause column reads `Stall shuttered` (was `Night kill`).
  - **The Family's private talk**: the Mafia verb is now to *shutter a stall* ("Choose a living merchant who is NOT Family and shutter their stall tonight"); internal GM kinds/logs renamed kill → shutter.
  - **The Herald**: the "the dead" section is now **"the departed"**; the sample morning paper reads "the night passed without a departure".
  - **Compat**: every parser (Herald, villagers, press plates, quiet-night streak, graveyard causes) accepts BOTH the old `Night kill` strings — historical matches stay readable — and the new phrasing.
  - **Press**: the dagger plate is retired (art deleted); a shuttered-stall edition now earns the closed-stalls-at-dusk plate (`sunset-over-stalls`), including re-presses of old editions.
  - Docs updated everywhere (rules, encryption, bot guides, index, operations, setup, setting page); AGENTS.md now carries the vocabulary rule for future edits. The CHANGELOG itself stays as written — it is a historical log.

## [1.8.7] - 2026-10-24
### Changed
- **README slimmed to its job**: removed the repo-structure tree, Key Features list, and the vague Quick Start — all of it duplicated (better maintained) in the docs. The README is now the pitch + a documentation index (incl. the new Setting page and the `mkdocs serve` hint). The **canonical repo map** is `docs/game_mechanics/rules.md` §3, which now also lists `tools/` and `setup/make_plates.py` and the seats.json `name` field.

## [1.8.6] - 2026-10-24
### Reverted
- **Never-collapse sidebar rolled back** (1.8.5): the fixed-overlay gutter approach still misbehaved on the user's screen. The docs are back to Material's stock layout; the issue is deferred.

### Changed
- **Example doctrines now render verbatim**: all nine example pages (`docs/example_doctrines/seat-ex_*.md`) show the doctrine **inside a `text` code block** — the exact bytes the bot reads from the vault file — instead of a formatted rendering of it. Each page keeps a normal heading plus a note explaining the raw display; the overview README says the same.

## [1.8.5] - 2026-10-24
### Changed
- **The left navigation never collapses.** Below Material's 76.25em fold the sidebar stays parked on-canvas (the drawer is simply always in its open position) and the content permanently reserves its strip — no re-flow surgery, wide-mode geometry untouched, hamburger hidden. On phones (<40em) the always-on sidebar slims to 9rem so it does not eat the screen.

## [1.8.4] - 2026-10-24
### Reverted
- **Sidebar/CSS layout experiments rolled back** (1.8.2–1.8.3): the drawer override broke the header/sidebar layout (banner overlap, vanishing sidebar). Material's default behaviour restored — the docs use the stock layout with only the bazaar palette from 1.8.1 kept (palette lives in `mkdocs.yml`, not CSS, and is unaffected).

## [1.8.3] - 2026-10-24
### Fixed
- **Left navigation actually stays** below Material's ~1220px fold: the first override (`display:block`) was a no-op — Material doesn't hide the sidebar there, it turns it into an off-canvas drawer (`position:fixed; left:-12.1rem`). The override now reverses each drawer property in the 40em–76.25em range (sticky in-flow column restored, content gutter reserved, dead hamburger hidden), so the sidebar only folds on real phones (<40em).

## [1.8.2] - 2026-10-24
### Changed
- **Docs layout** (new `docs/stylesheets/extra.css`): the main content is a step smaller (`.74rem` typeset, nav `.68rem`), and the left navigation column no longer collapses at Material's default 60em window width — the smaller content absorbs the width instead. The sidebar only folds into the drawer below 40em (actual phone widths).

## [1.8.1] - 2026-10-24
### Changed
- **Docs theme**: the purple palette is gone — the site now wears the bazaar: **deep orange / amber** (light) and **amber / deep orange** (dark). The index banner is centred over the text.
- **New page — "The Bazaar (Setting & Tone)"** (`game_mechanics/the_bazaar.md`): explains the desert-market setting, the merchant cast, the display names (labels only — the film characters never enter the game), the facts-only Herald, and the tone rules for in-character speech. Linked from the nav and the index.
- Docs hygiene: the sample editions are excluded from the nav (`not_in_nav`); removed the unimplemented "2 silent days = automatic vote" claim from the setup troubleshooting table; the example-doctrines README now states the real 1200-char statement limit.

## [1.8.0] - 2026-10-24
### Added
- **Private notebook (bot memory)** (`src/villager.py`): each seat's vault journal now carries a compact, structured memory — suspicion ledger (0–10 per merchant), verbatim private GM results, the seat's own record of statements/votes/night choices, a cycle log, and a current plan. Folded in after every act and once per new cycle (digesting finished days, at most three back-digested cycles after an outage). Epoch-scoped (a new deal wipes it), capped at `NOTEBOOK_MAX_CHARS`, never committed to git, and rendered into every prompt with a never-reveal instruction. Master switch: `NOTEBOOK_ENABLED`.
- **Two-stage reasoning**: every public act (statement, ballot, night action) is preceded by a private low-temperature thinking call (0.3) whose output feeds the act — the model no longer reasons and roleplays in one breath, and private thinking never reaches the arena.
- **Public ballot matrix**: bots see who has already voted and why (epoch-guarded, pre-computed) before casting their own ballot.
- **GM results persist for every role** — a Detective's findings (or any dossier traffic) now survives past the single prompt that delivered it; previously Villager-role results were read and dropped.

### Fixed
- **Three regex regressions from the notebook edit**: seat extraction in `graveyard_roll` and `parse_seat_id` had lost their bracket anchors and matched any digits — a graveyard row could be attributed to the wrong seat (the match column!) and a vote answer like "I abstain. Today is 2026-10-24." parsed as seat-20. Restored to `seat-07` / `Gandalf (7)` / `(10)` forms only.
- `maybe_digest` passed `limit=60` positionally into `recent_statements`' `dawn` parameter (worked only by accident); now a keyword argument.
- `public_vote_matrix` epoch guard tightened to match the GM's: a ballot without the arena's epoch is invisible (legacy no-epoch ballots can no longer haunt the notebook).

## [1.7.0] - 2026-10-24
### Added
- **`tools/` — operator tooling, reviewed and refactored**:
  - `bazaar_launch.py`: cross-platform bot launcher core — auto-detects the OS (tmux on macOS/Linux with explicit `MISTRAL_API_KEY` injection and macOS `caffeinate`; one console window per bot on Windows with a PID registry for stop/status). **Now also launches the Herald window** and accepts seat subsets (`start 01 03 05`). Thin wrappers: `bazaar-launch.sh` (POSIX) and `bazaar-launch.bat` (Windows) — the requested .bat version.
  - `run.sh` (was an empty placeholder): runs the neutral side on this clone — the Herald + local GM heartbeat (`town-clock.py`) in a `bazaar-neutrals` tmux session, with start/stop/status.
  - `bazaar-pull.sh` (was an empty placeholder): thin wrapper around `seats-pull.py`.
### Fixed
- **Launcher ran the renamed script**: `bazaar-launch.sh` executed `uv run bot.py` (renamed to `src/villager.py` long ago) and never launched the Herald. Both fixed via the Python core.
- `tools/resolve-jsonl.py`: globbed the wrong path (`village/*.jsonl`); now repairs all `gameplay/village/**/*.jsonl`, and additionally dedupes crash-resume duplicates (same seat+seq keeps the later ts).
- `tools/seats-pull.py`: game dir overridable via `BAZAAR_GAME_DIR` (aligned with the launcher).

### Changed
- All launcher references across docs, AGENTS.md, and the reset tools updated to `tools/bazaar-launch.sh` / `.bat`; the tooling overview table now lists the whole `tools/` and `setup/` suite.

## [1.6.2] - 2026-10-24
### Fixed
- **Full documentation/code alignment pass**. Removed or corrected every stale claim found in a repo-wide scan:
  - Ballots are **public plaintext `.json` with an Ed25519 signature**, not encrypted `.enc` — fixed the examples and file tables in `rules.md`, `README.md`, `bot_deployment.md`, `bot_architecture.md`, and `encryption.md`.
  - `encrypt_for_gm` does not exist — docs now use the real `encrypt_for_seat` (`docs/setup.md`, `encryption.md`, `bot_architecture.md`, `bot_deployment.md`).
  - Night-action payload examples now match the real shape (`role`, `ts`; no `action` key).
  - Statement limit is **1200 chars** (was documented as 600 in three places); push retries are **5 with growing backoff** (was "3 times / 5 seconds"); recovery/journaling uses `~/.bazaar/journal-<seat>.json` (was a nonexistent `{MY_SEAT}.log`).
  - Repo trees: `news/` → `herald/`, `usage/` marked reserved (no writer), `statements/` added, setup scripts listed.
  - Removed the unimplemented "token usage logging" rule; README key features now describe signed public votes and display names.
  - Stale code comments fixed (`src/editor.py`, `src/bot.py` → current names; Herald docstring version tag dropped); `bazaar-launch.sh` marked as operator-provided (outside this repo).

## [1.6.1] - 2026-10-24
### Changed
- **Display labels use bare numbers**: the seat bracket is now the seat *number* — `Gandalf (1)` … `Sherlock (10)` (was `Gandalf (seat-01)`). All parsers updated to accept every form (`seat-01`, `Gandalf (1)`, `(10)`, and the legacy `(seat-01)` rows): graveyard rolls, ballot tables, banishment lines, and the bots' vote/night-action output. Vote and night prompts now accept both `seat-02` and `7` as targets. Samples re-pressed.

## [1.6.0] - 2026-10-24
### Added
- **Display names for seats**: every seat now has a public name label (`Gandalf (1)` — from `setup/seats.json`), used system-wide in prose: GM announcements (banishments, night kills, alive lists, ballot tables), the graveyard, the match recap, village transcripts, the Herald's digest and editions, and the bots' prompts. The seat ID stays in brackets everywhere, so no context is ever lost. **The names are arbitrary labels**: bots and the Herald are explicitly instructed never to roleplay, quote, or reference the characters the names may evoke — the merchant personas are unchanged.
- Guardrails: machine files (ballots, dossiers, state.json, statement records, vote payloads) keep the bare seat ID; vote/night-action parsing extracts the seat ID from any name-wrapped model output; the Herald's graveyard and ballot parsers accept both old and new row formats.

## [1.5.3] - 2026-10-24
### Added
- **Ten new motifs** ingested (37 plates total): cutpurse-in-crowd, fortune-teller, merchants-haggling, moneylender-counting, porter-with-basket, puppeteer-show, scribe-at-work, spice-merchant-weighing, tea-vendor-serving, water-carrier — each wired into the scenery keyword tier (thief/stolen, fortune/fate, haggling/bargain, counting, porter/basket, puppet, scribe/manuscript, weigh, tea vendor/poured, water/thirsty). Rules deliberately avoid over-firing words (e.g. "letter", which every edition's Letters section contains).

## [1.5.2] - 2026-10-24
### Added
- **Event motif set completed** (27 plates total): moon-and-stars, dagger-on-cobblestone, scales-of-judgement, ballot-urn, lantern-in-the-dark, and a bonus solar-eclypse plate — all ingested and wired to the top-priority rules (night kill, quiet night, banishment, vote, lantern, eclipse).

### Fixed
- **Quiet-night rule**: now catches the GM's exact phrasing ("The night passed quietly") and ignores the "Quiet nights in a row" stat line, so a quiet-night morning earns the moon while a banishment evening keeps the scales. Both sample PDFs re-pressed accordingly (verified pixel-identical plates in both engines).

## [1.5.1] - 2026-10-24
### Added
- **Six new scenery motifs** ingested (21 plates total): cow-in-butchers-shop, girl-at-marked, market-place-city, market-street, old-stree-with-clock, spice-market-people-buying — each wired into the plate keyword rules (butcher/meat, girl/child, town square/crowd, market/stalls, clock/noon, buyers/haggling). `setup/make_plates.py` now also sweeps unprocessed `*.png` art from `plates/raw/`, not just `*.jpg` dropped in the plates dir.

## [1.5.0] - 2026-10-24
### Added
- **Content-keyed plates (Route C)**: the woodcut plate at the head of the first column is now chosen per edition from the motif pool (`docs/assets/plates/`) by keyword-matching the edition's text — game events first (night kill, quiet night, banishment), then persona and scenery motifs, with sunrise/sunset as edition defaults. Deterministic (same edition, same plate), missing motifs fall through to the next match, and an empty pool falls back to the static engraving. Plates are PDF-only, so the choice never becomes game input. Verified: all three pressed sample PDFs embed the expected plate, pixel-identical.

## [1.4.3] - 2026-10-24
### Added
- **Plate ingestion tool** (`setup/make_plates.py`): converts raw AI-generated motif art (`.jpg`) into uniform Herald plates — grayscale conversion, gentle tone normalisation, white-margin trim, and padding to a 3:1 band — saved as `.png` beside the raw art (moved to `plates/raw/`). Idempotent; run it whenever new art arrives. First 15 content-keyed motifs ingested to `docs/assets/plates/` (Route C groundwork for per-edition figures).

## [1.4.2] - 2026-10-24
### Changed
- **Engraving placement**: the woodcut plate now sits at the head of the first (left) column, above the drop cap — classic newspaper column-illustration style — instead of full-width under the headline. Both engines updated; verified by rasterising the pressed PDFs (plate spans the left column in tectonic and fpdf2 output).

## [1.4.1] - 2026-10-24
### Changed
- **Herald output directory**: editions and their PDF twins now live in `gameplay/herald/` (was `gameplay/news/`). All writers and readers updated: `town-herald.py`, `villager.py` (paper injection), `town-press.py` (PDF twin next to the markdown), and both reset tools clear the new directory. Verified end-to-end: write → villager reads → press twin.
- Added an evening sample front page (`docs/assets/herald-sample-evening.md` + `.pdf`), covering a cycle's dusk banishment.

### Fixed
- **Press sample parsing**: files not matching the real edition filename (`herald-cXXX-{part}.md`, e.g. the docs samples) fell back to "Morning Edition, No. 000" and the wrong filler seed. The press now detects the part from the filename and the cycle from the dateline.

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