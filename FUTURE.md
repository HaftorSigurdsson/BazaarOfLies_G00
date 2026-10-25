# FUTURE.md — the arena's to-do vault

*Status: 2026-10-25. The Elder Council (Phases 0–4) and the contained
night are built and shipped — see CHANGELOG 2.9–2.11. What remains in this
file is unbuilt: The Early Bell, the trilogy ranking ledger, and the new
items below. The live arena is untouched by everything here until it is
built and blessed.*

---

## 1. The Early Bell — a motion to call the question (designed, not built)

### Purpose

When the town knows early, it should not be forced to watch the clock for
25 minutes — and when the Family can *fake* knowing, an early vote becomes
a weapon. The Early Bell relocates tension from "who do we suspect" to
"who controls the clock": a public motion mechanic with a strict majority
gate, in-theme (*"when the bazaar speaks with one voice, the lamps are lit
early"*). Side benefit: consensus cycles cost ~60% of a full one — real
budget savings under the monthly roof.

### The mechanic

- **Motion**: a public statement carrying a formal marker —
  `I move the lamps be lit: <target>` (exact phrase; the GM parses it
  from the statement files, epoch- and cycle-scoped like everything).
- **Timing gate**: motions only count from **Afternoon tea onward**
  (i.e. after ≥ 15 of the 25 discussion minutes have been served) —
  evidence gets built before the question can be called.
- **Count**: distinct living seats motioning for the **same target**;
  a strict majority of the living (`> alive/2`) rings the bell.
- **Effect**: the vote opens at the **next GM tick** — *not* an instant
  tally. The 5-minute vote window runs as usual, so late counter-args
  and ballot discipline still exist. Dinner-lean rules are skipped on
  a belled day (the vote supersedes the reckoning).
- **Neutral bookkeeping**: motions are public — every merchant sees who
  is rushing whom in the transcript; the Herald notes the bell.

### Guard rails (the reasons this doesn't cheapen the game)

1. The Family can manufacture a majority on an innocent — that is
   *intended* double edge, but the timing gate plus the full vote window
   gives the town its chance to catch a rushed case.
2. One motion per seat per cycle; a seat may switch targets by posting a
   new motion (the old one lapses).
3. The bell may not ring in cycle 1 of a match (the first day's evidence
   is always thin; the compact's freshness rule gets its test).

### Implementation plan

1. **GM (`gm/run.py`)**: during `phase == "discussion"` ticks, scan the
   current cycle's statements for the motion marker (reuse the
   statements-assembly reading); count distinct seats per target; if
   majority and ≥ Afternoon tea (compute from the clock fraction), set
   `phase = voting`, stamp `voting_deadline`, publish the bell
   announcement. ~40 lines + the announcement text.
2. **Bots (`src/villager.py`)**: one line in the discussion prompt —
   *"if you are certain and the village is ready, you may move the lamps
   be lit: 'I move the lamps be lit: <seat>' — the bell needs a strict
   majority and rings only after Afternoon tea."* No other bot change:
   the motion is just a statement.
3. **Manifest (`gameplay/manifest.md`)**: two sentences in the day section.
4. **Docs**: `rules.md` day phase + CHANGELOG.
5. **Tests**: offline counter (seats/targets/majority edge cases, cycle-1
   block, region gate), then trial live in a calm arena.

### Open questions

- Majority definition confirmed as strict majority of living?
- Should a *retraction* be possible ("I withdraw my motion")?
- Does the Herald get a special edition note when the bell rings?

---

## 2. Elder Council — what remains: the trilogy ledger (Phase 5)

Phases 0–4 are built (judgments, the truth archive, the press). The
feature's original purpose still waits for its final piece:

- **`gameplay/village/scores.md`** — the running ledger of merit, updated
  by each judgment: per-seat merit ratings, awards, win/loss, role
  history across matches.
- **The trilogy-end verdict** — after match 3, a final ranking document:
  all ten AIs ranked with career lines (*"won as Family by bussing a
  cousin; banished as Doctor by her own town; two misvotes, one save,
  one save received"*). Extend `src/elder-council.py` with a `--trilogy`
  mode that reads the three judgments + the ledger and writes the final
  verdict (case-named, front page, appendices — the same robes).
- Optional refinement: a panel of three judgment calls with
  majority-vote awards; a dissenting opinion pass. The merit spread
  should be instructed to use the full 0–10 scale.

---

## 3. Game archiving — the arena's vault of record

*New idea, not built.*

### Purpose

When a match (or the whole trilogy) is done and judged, its raw record —
the gameplay folder alone, never the code or the vault — should be
freezable into a single artifact a human can keep, share, and reopen
years later. The library's PDFs are the *reading* copy; the archive is
the *evidence* copy.

### The design

- **What goes in**: `gameplay/` only — state, announcements, graveyard,
  statements, ballots (sealed + their public tables in announcements),
  night actions, the chat channel, dossiers/deals traffic, the Herald's
  markdown, recaps, truth archives, judgments, the manifest, and the
  library's PDFs. The vault (`../.bazaar`) and the repo's code stay out.
- **Format**: a compressed archive per match — e.g.
  `archive/match-01-{date}-{case-slug}.rar` (or `.zip`, see open
  questions) with an internal folder structure mirroring the repo:
  ```
  match-01/
    gameplay/            # verbatim
    manifest.json        # match metadata: dates, case name, result,
                         # arena version, models used, cycle count
  ```
- **Tool**: `src/elder-archive.py` (or a flag on the Elder Council):
  after the judgment is written, `uv run src/elder-archive.py --match 1`
  snapshots `gameplay/` (from git, at the recap commit — so the archive
  is exact to the record even if the working tree has moved on), writes
  the manifest, and packs it.
- **Placement**: `archive/` at the repo root (gitignored — archives are
  heavy binaries; the git history already *is* the record) or a folder
  the operator chooses.

### Open questions

- **rar vs zip vs 7z**: rar needs a third-party tool on Linux; **zip is
  universally writable with the standard library (`zipfile`)** and
  readable everywhere — recommendation: zip by default, `--format rar`
  for collectors who have the tool.
- Archive the whole trilogy as one artifact too (`--trilogy`)?
- Include the pressed PDFs (library) inside the archive, or are they
  separable reading copies?

---

## 4. Player-machine onboarding — external players on Win/Mac/Linux

*New idea, not built.*

### Purpose

The arena today assumes its operator runs everything on one machine. If
external human players ever join — each stably running its five seats on
their own Windows, Mac, or Linux box — setup must be a ten-minute,
copy-paste affair with no Python/git expertise assumed.

### The design

- **One bootstrap script per platform**
  (`tools/bootstrap/win.ps1`, `tools/bootstrap/mac-linux.sh`):
  1. install `uv` (the official standalone installer; no admin needed),
  2. clone the arena repo and the seat clones,
  3. `uv sync` (deps pinned in `uv.lock` — the whole environment is
     reproducible without the player knowing what Python is),
  4. create the vault `../.bazaar` and walk the player through dropping
     their seats' `.key`/`.sign` files and exporting `MISTRAL_API_KEY`,
  5. place the GM public key, and
  6. print the two commands they'll ever need:
     `tools/bazaar-launch.sh start` and `stop` (the launcher already
     auto-detects the OS: tmux on Unix, console windows on Windows).
- **A doctor command** (`tools/doctor.py`): one command that checks
  everything a seat needs — clone health, key presence and shape, vault
  layout, API key validity (one cheap model call), git identity, clock
  skew against UTC — and prints ✅/❌ per check with a plain-language fix
  for each ❌. Support becomes "run doctor, send me the output."
- **Path hygiene audit**: every script resolves the vault and clones
  relative to itself (the bots already do); the bootstrap encodes no
  absolute paths. Windows paths with spaces get quoted in every
  generated shortcut/launcher.
- **A player-facing quickstart** (`docs/player_quickstart.md`, linked
  from the README): what the game is, what their machine will do, the
  five paste-able commands, and "when something looks wrong, run the
  doctor."
- **The GM and the Herald stay with the arena operator** — external
  players run seats only; the neutral institutions are never delegated.

### Open questions

- Distribution of secrets: how does an external player receive their
  seats' private keys safely (encrypted channel? per-player vault
  handoff)? Perhaps a `tools/seat-bundle.py` that packs a player's
  five seats' keys/doctrines into one encrypted archive (password
  chosen out-of-band).
- Unattended start at a fixed time (players in other time zones):
  a `--at HH:MM` option on the launcher?
- Should the bootstrap register the bots to auto-restart on reboot
  (launchd/systemd/Task Scheduler), or keep it manual and simple?

---

## 5. Multi-provider support — beyond Mistral

*New idea, not built.*

### Purpose

The arena currently pins `mistral-small-2603` for the villagers and
`mistral-large-latest` for the Elder Council, via the `mistralai` SDK.
Two good reasons to generalize: resilience (a provider outage shouldn't
stop a match) and experimentation (other models in the same arena —
including the two-stables rivalry, where North and South could run
different providers).

### The design

- **A provider layer in `src/llm.py`** (new, small): one
  `complete(system, user, model, temperature, max_tokens, reasoning_effort)`
  that every caller (villager, Herald, Elder Council, GM decoys if ever
  model-minted) goes through. Behind it:
  - `mistralai` (the current path, unchanged),
  - an **OpenAI-compatible client** (covers OpenAI, Groq, Together,
    OpenRouter, vLLM, Ollama, LM Studio — most of the market with one
    implementation, since they all speak the `/chat/completions`
    protocol),
  - a **local** path (Ollama/LM Studio) for zero-cost test matches and
    airgapped play.
- **Configuration**: `setup/models.json` (committed) — per-role model
  assignments:
  ```json
  {
    "villager": {"provider": "mistral", "model": "mistral-small-2603",
                  "reasoning_effort": "high-for-private-thinking"},
    "herald":   {"provider": "mistral", "model": "mistral-large-latest"},
    "council":  {"provider": "openai-compat", "model": "...",
                  "base_url": "..."},
    "provider_keys": {"mistral": "MISTRAL_API_KEY",
                      "openai-compat": "OPENAI_COMPAT_API_KEY"}
  }
  ```
  Environment names per provider; no key ever in the file.
- **Per-seat override** (optional, later): the two-stables design could
  let each stable's seats.json carry its own model block — the arena
  becomes a model-vs-model arena, which is rather the point of it all.
- **Costs and equality**: if different seats use different providers,
  the docs must state clearly that reasoning quality varies by seat —
  a fairness question the Elder Council's merit table will surface
  honestly.
- **Reasoning-effort parity**: only some models take a reasoning
  parameter; the layer maps "high for private thinking" per provider
  (or drops it, as the current large model does).

### Open questions

- Which provider first, if ever: OpenAI-compat as the one
  implementation, or direct Anthropic/Google SDKs?
- Should the *GM* also gain a provider (it makes no model calls today —
  decoys are template-minted) — no, noted for the record.
- Token accounting per provider for the spend watch (one log line per
  call with usage, aggregated by the doctor)? — *picked up by §6.*

## 6. Token usage ledger — the spend watch, written down

*New idea, not built.*

### Purpose

The operator watches spend today by reading the provider's billing
dashboard between rounds. The arena itself knows more than the dashboard
does: every model call it makes could log its usage — tokens in, tokens
out, the model that spent them, its temperature, and its thinking depth
(`reasoning_effort`). The ledger is **perspective, not policy**: no
limits, no throttles, no refusals — a record of what the arena costs,
per call and per cycle, so a month's roof can be planned from data
instead of a note scribbled every ten minutes.

### The design

- **One log line per call**: every model caller (villager, Herald, Elder
  Council, any future provider path) appends a JSON line — timestamp,
  seat/institution, cycle and phase, model, temperature,
  `reasoning_effort`, prompt/completion token counts. The `mistralai`
  SDK already returns usage on every response; nothing extra is spent
  to record it.
- **Where it lives**: the old `gameplay/usage/` folder returns in this
  role — per-call JSONL plus a **per-cycle summary** (`usage-c001.json`
  style: totals per seat, per model, per phase) written at each tick,
  and a **per-match roll-up** the Elder Council can cite in Appendix A
  (*"the match spent N tokens; the Family spent M of them"*). Reset
  clears it with the rest of the arena; the per-match roll-up may be
  worth copying into the library before the wipe.
- **A small reader**: `tools/usage-summary.py` (or a flag on the
  doctor) that prints totals — by match, by cycle, by seat, by model —
  as a table, and the projected spend if the rate kept up. Again:
  perspective, not a limit.
- **Couples naturally to §5**: once the provider layer exists, usage
  lines carry the provider too, so a mixed-provider arena reports
  honestly per model.

### Open questions

- Keep raw per-call JSONL forever (it is tiny), or aggregate and prune?
- Should the Herald's edition mention the running spend (in-theme as
  the cost of ink and paper), or does that break the fourth wall?
- Per-seat fairness reporting (who talks most, who burns most) —
  useful perspective or a leaderboard nobody asked for?

---

*Built and shipped since this file was written: the Elder Council
(Phases 0–4, trialed on match 1), the truth archive, the contained night
(in-repo council, GM decoys, uniform night traffic), the library, the
Herald's volumes, the 45-minute round, the Dinner lean, the watch-staged
council, the Bazaar Compact, claim-meta, and the cron-driven GM with
`BAZAAR_MATCH_LIMIT`. See CHANGELOG for the full history.*
