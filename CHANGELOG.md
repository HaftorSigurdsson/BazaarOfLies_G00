# Changelog

All notable changes to this project will be documented in this file.




## [2.8.4] - 2026-10-25
### Added
- **`BAZAAR_MATCH_LIMIT`**: park the arena instead of auto-chaining into the next match. When the match number passes the limit, the GM refuses to deal, sets phase `halted`, announces that the bazaar rests, and every bot idles — nothing starts without an operator. The live cron runs with `BAZAAR_MATCH_LIMIT=1`, so this match ends and the arena parks; default (unset) remains unlimited.


## [2.9.0] - 2026-10-25
### Added
- **The Elder Council** (`src/elder-council.py`, `src/elder-press.py`) — the arena's fourth institution, built and trialed on match 1: a post-match historian-judge that compiles the complete record (roles, graveyard, published ballots with computed vote tallies, 320 statements, decrypted night actions, the Detective's never-delivered sealed result, the Family's candlelight council) and delivers a **court-style judgment** — history, main arguments, per-seat verdicts with merit ratings, and the awards (MVP, Golden Sacrifice, Worst Misjudgment, Best Lie, Most Damning Quote) — as markdown plus a **3-page court-document PDF**. Ground discipline enforced: an authoritative per-cycle timeline (tallies + departure mechanisms) is restated faithfully; the trial judgment's history matches the GM's own log. Match 1's verdict: MVP Batman (a villager), Golden Sacrifice Elsa the Detective.
- **Truth archive** (`gm/run.py` `write_truth_archive`): at match end the registry and every sealed night action are decrypted and committed (`match-XX-truth.md`) before the next deal can overwrite `gm/roles.enc` — the Council judges from the authoritative record.


## [2.9.1] - 2026-10-25
### Changed
- **The Council speaks with the large model** (`mistral-large-latest`) — the judgment is written once per match, so gravitas is worth the tokens. `reasoning_effort` dropped: the API rejects it on large ("not enabled for this model"); the Council thinks in prose.
- **The matter gets its name**: a case-name call now titles the judgment after the outcome and theme — match 1 was named *"Mafia Shadows Over Stalled Stalls"* — with a dateline line beneath.
### Added
- **Bilag A — The Record** (computed, model-free): the match's start and end times, duration, volumes of the record, the ledger of departures, and every vote tally by cycle.
- **Bilag B — The Ratings**: the verdicts' merit scores parsed from the drafts and ranked best-to-worst in a table — the Council's numbers, typeset by machine so no rating can drift.
- **The elder press renders markdown tables** (ruled LaTeX tabulars) and strips wrapping code fences from model output (large liked to gift-wrap its judgment).


## [2.9.2] - 2026-10-25
### Changed
- **The History is one bullet per cycle** — each carrying its tally and departures in the timeline's own words; no more dense prose paragraphs.
- **A formal front page** for the judgment PDF: the arena's seal (the bazaar engraving at a quarter width), "In the Matter of" the case name in large italics, the dateline, and one small plate drawn at random from the arena's collection as a footer ornament — a historical legal document's title page.
- **Paragraph spacing fixed**: the press joins blocks with blank lines, so a section heading can never run into the paragraph before it (the overflow bug).
### Fixed
- The press compiles from a temp directory — asset paths (engraving, plates) are now absolute; Python 3.14 hard-errors on invalid escape sequences in the title-page strings (now raw f-strings).


## [2.9.3] - 2026-10-25
### Changed
- **Judgment typography**: the front page's seal now stands alone beneath the ruled line, above the case name (paragraph breaks between the title-page elements — LaTeX was joining them into one line). Every body page carries a running header with the full heading (small italics over a rule) and a centered page number in the footer; the title page stays clean and unnumbered.


## [2.9.4] - 2026-10-25
### Changed
- **The judgment's History now narrates the nights**: each cycle bullet carries the vote tally, the departures, *and the night's secret doings* — sealed night actions with roles and targets, the Detective's investigation findings, and the Family council's deliberation count and declarations. The final bullet is the computed **Conclusion** (the winner and the standing — machine-derived, not model-invented).
- **Appendices, not bilag**: renamed and typeset — each Appendix begins on a fresh page.
- **The front page carries an Abstract**: a 40–60 word executive summary (what happened, who won) in small italics between ruled lines, under the dateline. The seal is now double width (half the page).
### Fixed
- Model output is sanitized for control characters (a stray `\x02` from the large model broke the TeX compile); both the Council and the press strip them.


## [2.9.5] - 2026-10-25
### Changed
- **The History is now nested bullets**: each cycle is a bullet with indented sub-bullets — Vote tally, Night action (sealed actions, the Detective's findings, the Family council), Departures — closing with the computed Conclusion. The press renders arbitrary list nesting (fixed a lonely-\item bug: blank lines inside lists no longer close them).
- **Verdict headers carry the merit**: each verdict opens with '**<Name> (<seat>) — <role> — <merit>/10**' (e.g. '**Yoda (03) — Mafia — 8/10**'), the merit also stated in prose below.
- Final document hygiene: control characters stripped after every transformation (the abstract insertion could carry them in), and known section headings auto-repaired if a model glitch swallows their marker.


## [2.9.6] - 2026-10-25
### Changed
- **The body reads by name**: "Sherlock (10)" is now just "Sherlock" throughout the history, arguments, verdicts, and awards — the seat-number strip is deterministic (model prose included), with the numbers preserved only in the appendices, where a footnote states that the number in parentheses is the merchant's seat number in the arena. Verdict headers follow suit: "**Yoda — Mafia — 8/10**".
- **The front page rides the camel caravan** (the arena's own plate, half-page width) and the footer is bare — only "The bazaar rests." remains; the random bottom ornament is gone.


## [2.10.0] - 2026-10-25
### Changed
- **The library** (`gameplay/library/`): every pressed PDF — Herald editions and Elder Council judgments — now lives in one human archive; the markdowns stay in place for the bots. The library survives arena resets, like the recaps: it is the arena's bookshelf.
- **The Herald has volumes**: editions are now `herald-vol<VV>-cXXX-{morning,evening}.md/.pdf`, the volume rising forever across matches and resets (the counter lives in the vault at `../.bazaar/herald-vol.txt`). The masthead carries the true **Vol. N — No. M** (unpadded inside the paper; the zero-padding is for the file system), and the dateline reads "*Vol. N — Match M, Cycle C*". The nine existing editions were renumbered chronologically as vols 1–9.

## [Unreleased]
### Added
- **`FUTURE.md` (The Early Bell)**: a designed-not-built motion mechanic — "I move the lamps be lit: <target>" rings the vote early on a strict majority of living seats, gated to Afternoon tea onward so evidence gets built first; the 5-minute vote window survives. Intended as a double-edged mechanic (the Family can rush a fake consensus), with guard rails, a five-step implementation plan, and open questions for the next session.
- **`FUTURE.md`** — the design plan for the **Elder Council**: a post-match historian-judge that reviews the complete record (statements, ballots, graveyard, recap, Herald editions, the Family's council transcripts, and a to-be-archived truth file) and delivers a 3–4 page court-style judgment — per-seat verdicts with citations, MVP / Golden Sacrifice / Worst Misjudgment awards — plus a trilogy-end overall AI ranking ledger. Five build phases, open questions, and non-goals; designed 2026-10-25, build resumes next session.

## [2.8.3] - 2026-10-25
### Fixed
- **The council prompts demanded receipts, not echoes**: night 2's council exposed that all three watch-1 proposals recycled the prompt's own canned example ("their ledger is too clean") verbatim — unanimous by anchoring, not deliberation. The proposal/reply/declaration prompts now demand one concrete citation from the day's record and a stance on the cousins' proposals; the canned example is gone. A robust `council_reason()` extractor takes whatever follows the seat ID (any dash style, colon, or comma).
- **`parse_seat_id` accepts what the prompts offer**: "seat-7", bare leading numbers ("4 — the loudest accuser"), and parenthesized IDs all parse now — a live log showed a ballot attempt failing to parse on "seat-8" and retrying. Prose numbers are still safely ignored.

## [2.8.2] - 2026-10-25
### Changed
- **The Compact teaches claim-meta**: the manifest now states that power-role holders (Doctor, Detective) may reveal their role if they judge it advantageous — and warns every merchant that the Family may fake-claim those same roles to steer votes or bait the true power roles out. "A claim is a move, not a proof; test it against the ledger." Bots pick this up on their next act (the manifest is mtime-cached into every prompt; no restart needed).

## [2.8.1] - 2026-10-25
### Fixed
- **Stage directions no longer typeset as section heads**: the press treated *every* italic-only line as a ruled section heading, so a quoted merchant's stage direction (*"Extinguishes the censer…"*) rendered as bold small-caps mid-letter. Short italic lines (≤ 60 chars) stay section labels; long ones flow as italic prose (`\emph`) inside the letter.
### Changed
- **The Tally is evening-only**: the computed election-returns chart is no longer appended to morning editions — the morning paper reports the news, the evening paper carries the day's returns. Guarded in both the Herald (append) and the press (render, both engines); existing morning PDFs re-pressed without the chart, evening keeps it.

## [2.8.0] - 2026-10-25
### Added
- **The Bazaar Compact** (`gameplay/manifest.md`): the villagers were never told what game they were playing — personas say who they are, doctrines how to behave, but the rules lived nowhere the merchants could read. The compact is public game knowledge (purpose, the 3 Family + Doctor + Detective structure, the tea-clock day with the dinner lean, voting, the three night watches, win conditions, the boards, the in-theme vocabulary, and "every match starts with a blank ledger — cycle 1 has no yesterday") and is read into every villager prompt, discussion/vote/night/council alike. This directly targets the confabulated "yesterday's vote" reasoning observed in cycle 1.
- **Structured night council**: the Family's candlelight council is now staged by the tea clock's three watches — *The night* (talk: proposal + replies, up to 4 messages per mafioso), *Night snacks* (the must-state: every mafioso declares their shutter target), *The night watch* (full transcript + declaration tally into the sealed action, converge on the majority). The channel is now append-only JSONL (`c{CCC}-{seat}.jsonl`); the 120-second grace timer is gone — the clock is the synchronizer. A stalled cousin costs their voice, never the shutter. Reset sweeps both channel formats.

## [2.7.1] - 2026-10-24
### Fixed
- **The press now accepts any heading depth**: the Herald's model drifted to `###` section heads this match (the parser handled only `#` and `##`), so `### THE DEPARTED` and friends leaked into the PDF as literal text. Any `#`–`######` heading inside the edition becomes a masthead headline (first) or a ruled section head (rest); verified on the live edition — all sections render, still one A4 page, no hashes in the extracted text.

## [2.7.0] - 2026-10-24
### Changed
- **Model: `mistral-small-2409` → `mistral-small-2603`** for all villagers, with **`reasoning_effort`** wired through the new SDK: `"high"` for the two-stage private-thinking calls (discussion/vote/night reasoning), `"none"` for the public acts (statements, ballots, council proposals) — fast and in-character where the village is watching, harder reasoning where nobody sees.
- **`mistralai` SDK 1.9.11 → 3.4.0** — 1.9.11 silently dropped `reasoning_effort` from requests; 3.4.0 sends it. The client import moved (`from mistralai.client import Mistral`) — villager and Herald updated.
### Fixed
- **High-effort response parsing**: with `reasoning_effort="high"` the API returns message content as a **list of chunks** (ThinkChunk thinking + TextChunk answer) instead of a plain string — `ask()` now extracts the text chunks and discards the thinking (verified live against both effort levels).

## [2.6.1] - 2026-10-24
### Changed
- **Snappier villagers**: poll interval 30s → **20s** (plus the 0–5s jitter) and statement pacing 120s → **90s**, so merchants respond to the village within ~half a minute and fit ~8 statements plus several exchanges into the 25-minute discussion. To watch: git push contention (10 bots × 3 polls/min) and API rate — both behaved at 30s/120s; the push-retry loop is the safety net. Docs swept accordingly (`bot_architecture.md`, `rules.md`, `bot_deployment.md`, the example doctrines).

## [2.6.0] - 2026-10-24
### Changed
- **The 45-minute round** — a new day rhythm, every window a multiple of the GM's 5-minute tick so phase deadlines always land on a tick: discussion **25 min** (`Morning`, `Morning tea`, `Lunch`, `Afternoon tea`, `Dinner` — 5 minutes each on the tea clock), voting **5 min** (`Evening — the lamps are lit and the vote is on`), night **15 min** (`The night`, `Night snacks`, `The night watch`). Was 30/10/10 (50-minute rounds).
- **The Dinner lean**: during Dinner (the discussion's last 5 minutes), every living merchant's statement prompt requires them to state publicly who they lean toward banishing and why. The dinner statement is exempt from the 8-statement budget (once per cycle, journal-tracked); the GM's silence penalty remains the backstop.
- **Family council grace loosened to 120 s** — the 15-minute night gives the candlelight council a whole watch to convene (pass A in *The night*, deliberation over *Night snacks*, the sealed shutter by *The night watch*).
- Docs updated: the tea-clock table (`the_bazaar.md`), phase durations + the dinner rule (`rules.md`), council grace (`bot_architecture.md`).

## [2.5.0] - 2026-10-24
### Added
- **The Family's candlelight council**: Mafiosi can now coordinate at night — a two-pass conclave held **outside the repo**, in `../.bazaar/family/c{CCC}-{seat}.json` (one writer per file, epoch-scoped, ghost-proof; invisible to the village by construction). First night poll: each Mafioso lodges a shutter proposal (target + one line why); later polls: the Family's proposals are read into the sealed-action prompt with instruction to converge on the majority (a split hands the choice to the GM's random tie-break). A 90-second grace keeps a stalled cousin from stalling the shutter; solo Mafiosi skip the council. Plaintext for now — the dossier's `night_channel_key` (dealt but previously unused) is the hook for encrypting it later, at which point the channel could move into the arena repo. `town-reset.py` and `setup/reset_match.sh` clear the channel between matches; documented in the bot architecture guide.

## [2.4.5] - 2026-10-24
### Fixed
- **Seat keys re-aligned mid-match (surgery, no reset)**: the vault's original seat private keys had been overwritten by the accidental `town-setup.py` re-run's regenerated keypairs, so nothing the GM sealed to a seat could be decrypted — every bot failed with `CryptoError` at night and **no night actions were ever submitted** (no kills, no saves, no investigations; the town played blind). The vault keypairs are now canonical: `setup/seats.json` public keys re-derived from them, and the live match's dossiers re-sealed from the GM's registry (same roles and teammates; fresh shared Family night key — the old one was locked inside undecryptable dossiers). Verified: all ten re-sealed dossiers decrypt with the vault keys.

## [2.4.4] - 2026-10-24
### Fixed
- **The press ignored the Herald's section headings**: the Herald wraps each edition in a ` ```markdown ` fence, and `parse_edition` classified *any* fenced block as monospaced code — so `##` subheads printed as literal text in a typewriter block, the real headline was swallowed (the masthead fell back to "The Tally"), and the dateline rules misfired. A ` ```markdown `/` ```md ` fence is now parsed as the edition proper: its `#` line becomes the masthead headline, `##` lines become ruled section heads in both engines, italic-only lines become subheads (the Letter to the Editor gets its heading back), and `---` rules are skipped. All in-flight editions re-pressed; still one A4 page, verified by text extraction.

## [2.4.3] - 2026-10-24
### Changed
- **GM keypair rotated** (`setup/gm_public_key.txt` replaced): the original private key only ever existed as a `/tmp` file piped into the GitHub secret and is lost with `/tmp`. The new private half is vaulted outside the repo (`../.bazaar/gm_private_key.txt`, chmod 600) where the local cron GM reads it. Everything sealed to the old key (role registry, dossiers, night results) is unreadable by design, so the in-flight match is reset and re-dealt with the new key — the GitHub-Actions GM is retired in favour of the operator's own cron-driven GM.

## [2.4.2] - 2026-10-24
### Changed
- **Night shortened to 10 minutes** (was 15): the night is one simultaneous sealed window and the bots submit their actions within seconds of nightfall, so the tail of the window was pure idle. `gm/run.py NIGHT_MINUTES` and the tea-clock's nominal night span (`BAZAAR_NIGHT_MINUTES` default in `gm/utils.py`) both set to 10; the three watches now divide a 10-minute night. Effective from the next night onward. (The night stays a single window by design: there is no private Family channel, so a "mafia discussion then vote" split has nothing to coordinate over.)

## [2.4.1] - 2026-10-24
### Fixed
- **The automatic PDF press has never actually run**: `town-herald.py` tried `from town_press import ...`, but the press lives in the kebab-cased `src/town-press.py`, which Python cannot import by name — every edition logged `press skipped: ModuleNotFoundError` and went out PDF-less. The Herald now loads the press from its file (importlib), and the missing PDFs get a `.pdf` twin committed next to each edition again. (Manual CLI pressing always worked; only the automatic in-Herald call was broken.)

## [2.4.0] - 2026-10-24
### Changed
- **Vault layout**: private files now live in **`../.bazaar/`** (seat keys, signing keys, journals — a sibling of the clone, resolved from `villager.py`/`town-herald.py`'s own location) and **doctrines in `../villagers/<seat>.md`**. The old `../bazaar/` sibling is no longer read. `town-reset.py` and `setup/reset_match.sh` resolve journals as `$VAULT` → `../.bazaar` → `~/.bazaar`; `make_signing_keys.py` examples use `--vault ../.bazaar`. All docs (`docs/`, `AGENTS.md`) swept to the new paths.

## [2.3.3] - 2026-10-24
### Fixed
- **`tools/bazaar-launch.py` default seat-clone path** was `~/Desktop/GAME` (wrong case on case-sensitive filesystems) — now `~/Desktop/Game`, matching `seats-pull.py`; docstring refreshed for the kebab-case name and the retired `.bat` wrapper.
- **`src/town-reset.py` journal vault** defaulted to `~/.bazaar`, so resets silently cleared **0 journals** while the bots' real journals live in the sibling vault `../bazaar` (see `villager.py`'s `BAZAAR_DIR`). Resolution order is now `$VAULT`, the sibling vault, then `~/.bazaar` — stale journals can no longer survive a reset and make restarted bots replay old actions.
### Changed
- **Signing keys regenerated** for all ten seats (`setup/seats.json` now carries each seat's `signing_public_key`): the vault had lost its `seat-XX.sign` files, and `villager.py` refuses to cast a vote without them — ballots were impossible until this. Private `.sign` keys live only in the vault; only public keys are committed.

## [2.3.2] - 2026-10-24
### Changed
- **Docs: game-start procedure brought up to date with the current `tools/` and `src/`** — kebab-cased tool names (`tools/bazaar-launch.py`, `tools/statements-assemble.py`), the removed JSONL repair tool dropped from the docs, the retired Windows/`bazaar-pull.sh` wrappers noted as living in `tools/STORE/` (Windows now invokes the launcher core directly), `src/town-press.py` added to the file tree, the Game Day section in `docs/setup.md` now spells out the launcher commands (subsets, `--no-herald`), the neutral side (`tools/run.sh`) with its one-GM-driver warning, and the `--wipe-recaps` reset flag.

## [2.3.1] - 2026-10-24
### Added
- **`--wipe-recaps` for `src/town-reset.py`**: the full reset also removes match recaps (`gameplay/village/match-XX-recap.md`) when the flag is passed. Without it, recaps are kept exactly as before (history, namespaced by epoch, harmless to a fresh match). The confirmation banner states which way it's going; `--dry-run` previews the recap removal too.

## [2.3.0] - 2026-10-24
### Added
- **Statement mirror tool** (`tools/statements_assemble.py`): assembles the per-seat statements of a cycle into one local transcript — `gameplay/village/statements/_assembled-cXXX.jsonl`, gitignored (never committed or pushed), always overwritten on run; `--watch [SEC]` keeps it fresh, `--cycle N` picks a cycle, `--ignore-epoch` reads finished matches. Runs from any clone (arena = cwd). Dedupes crash-resume duplicates and hides foreign epochs, mirroring the bots' own transcript view. Deliberately a mirror only: the bots already assemble the transcript into their prompts, and the per-seat files remain the single source of truth (one writer per file = no merge conflicts).

## [2.2.0] - 2026-10-24
### Added
- **The tea clock (in-theme day regions)** — `gm.utils.day_region(state)`, computed from the arena clock; no new mechanics, pure flavour as prompt context:
  - Day (discussion): **Dawn → Morning tea → Midday → Afternoon tea → Dusk**; the voting window rides Dusk ("the lamps are lit and the vote is on").
  - Night: **The first watch** (the night guards brew their tea and make their rounds) → **The middle watch** (even the guards' tea has gone cold) → **The last watch** (the darkest hour).
  - Every merchant prompt (discussion, vote, night) carries "Time of day: {region} — {flavour}"; the Herald's digest states the time of print ("printed at Morning tea" / evening editions print at the first watch). Graceful fallbacks when the clock is missing; the setting page documents the full tea clock.
  - Verified: all eight regions at their boundaries, voting, night watches, both fallbacks, villager prompt block, and Herald digest for morning and evening.

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