# FUTURE.md — the arena's to-do vault

*Status: 2026-10-26, after the audit. Built and shipped since this vault
was opened: the Elder Council (now convening itself at match end,
v2.19.0), the contained night with the debrief council, the
transcript-hygiene diet (§11, v2.14.0), the square's customs (v2.16.0),
the dealt playstyles (v2.18.0), The Laws of the Bazaar (v2.20.0), the
Herald's auto-curated Letter to the Editor (§9, superseded), match
archiving (§3, shipped as `tools/archive-match.sh`), visualizations
(§10, shipped as `tools/visualize.py`), and per-call token logging
(villager side of §14). Removed sections keep their numbers retired —
this file never renumbers. What remains below is unbuilt: the Early
Bell, the trilogy ledger, onboarding, multi-provider, reputation, the
night economy, abilities, §12, §13 and §14's remainder.*

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

Phases 0–4 are built, and since v2.19.0 the Council convenes itself at
every match end (judgment + pressed PDF, best-effort). The feature's
original purpose still waits for its final piece:

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

## 3. Game archiving — RETIRED (shipped as `tools/archive-match.sh`)

The per-match compressed artifact exists (`archive/match-N.tar.gz`:
the library's PDFs plus the match record files). The richer design
below — a verbatim `gameplay/` snapshot from the recap commit with a
manifest of metadata — was never needed; git history remains the exact
evidence record. Recoverable from this file's history if ever wanted.

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

## 6. Reputation System

*New idea, not built.*

### Purpose

Merchants today have no memory of past matches — every deal is a fresh
bazaar. A reputation system gives the town a long-term memory: who has
been banished, who has been MVP, who has signed the Early Bell. The
mechanic is **perspective, not policy**: no limits, no throttles — a
record of who has earned trust, so the town can weigh its votes with
history in mind.

### The Design

- **Reputation score (0-100)** per merchant, stored in `gameplay/trilogy/`.
- **Affected by**:
  - Being banished (-20).
  - Being MVP (+30).
  - Signing the Early Bell (+10).
- **Impact**:
  - High-rep merchants get +1 vote in tied ballots.
  - Low-rep merchants are more likely to be investigated by the Detective.

### The audit's caution (2026-10-26)

This section predates the Laws and contradicts itself: it declares
"perspective, not policy" and then defines two policies. It also sits
against **Law 3.2** (freshness: nothing before the deal is evidence) —
a cross-match score the merchants can cite would import old matches
into new ones. If built, either strip it to true perspective (the
ledger exists, influences nothing, the Elder Council cites it) or
amend Law 3.2 first, by play, in a parliament (§13).

---

## 7. The Night Economy (the Night Market remainder)

*Rewritten at the audit: the structured council — staged
talk/declare/assent plus the day-debrief (v2.17.0) — shipped long ago.
What was never built is the economy below.*

### Purpose

The council can coordinate; it cannot yet *trade*. A night economy
deepens strategy and counterplay beyond the single shutter vote.

### The Design

- **Structured night actions**:
  - **Bribe**: Family can pay 10 "coins" to flip a vote.
  - **Sabotage**: Family can silence one merchant for a cycle.
  - **Heist**: Family can steal the Detective’s result.
- **Coins**: Earned by surviving cycles (1 coin/cycle) or being MVP (5 coins).

### Open Questions

- Does this unbalance the game toward the Family?
- Should coins persist across matches?

---

## 8. Special Roles with Abilities

*Not built. The audit's caution: this predates two findings — the
operator's own direction (variety belongs in trades, not superpowers),
and match evidence that the village cannot yet wield the two power
roles it already has (the Detective died with the winning fact
unspoken; zero claims in four matches). Build only after the village
learns to use what it holds.*

### Purpose

Passive roles (Detective/Doctor) limit strategic depth. Adding active
abilities could diversify gameplay.

### The Design

- **Blacksmith**: Can "forge" one vote per match (counts as 2 votes).
- **Jester**: Wins if banished (but loses if Family wins).
- **Courier**: Can privately message one merchant per cycle (GM-mediated).

### Open Questions

- Does this make the game too chaotic?
- Should abilities be role-specific or open to all?

---

## 9. Interactive Herald — RETIRED (superseded by the shipped auto-letters)

The Herald has long closed with a "Letter to the Editor" — one public
statement quoted verbatim, machine-chosen, attributed by name. That
serves this section's purpose with zero leak risk (nothing is
submitted, only public statements are quoted), so the submission
channel (`gameplay/herald/letters/`) is unnecessary.

---

## 10. Visualizations — RETIRED (shipped as `tools/visualize.py`)

The network graph (who votes for whom), the timeline, and the word
clouds all exist behind one command: `uv run tools/visualize.py
--match N --cycle C`.

---

## 11. Transcript hygiene — starving the echo at the source (shipped, v2.14.0)

Match 3 gave the cleanest evidence yet: a phrase coined once
("the Compact rewards the walker", Elsa, cycle 1, 18:31) spread to nine
seats within minutes and structured the entire next day. The shipped
mitigations (the anti-echo clause + per-seat temperature band,
v2.13.4) raise the cost of copying; this design removes the fuel — the
verbatim transcript that every bot re-reads before every statement.

### The design: a recency window with a cheap-model digest

- **Verbatim window**: only the **K most recent statements** (K ≈ 5–6)
  enter the transcript verbatim. Recency carries the conversational
  thread; everything older is context.
- **The older day, digested**: statements that roll out of the window
  are summarized **per merchant** by a *cheap* model
  (`mistral-small-latest` or the Nemo-class — pennies against the main
  model): "keep the claim, the names, and the dates; drop the
  phrasing." One to two lines each. The transcript then reads
  *Earlier today (digest): …* then *Most recent (verbatim): …*.
- **Per-bot, vault-local summaries** — the crucial choice: the digest is
  computed by each bot into `../.bazaar/digests/` (epoch+cycle+seat
  keyed, write-once, read-every-poll). A *shared* in-repo digest would
  itself become the next shared verbatim anchor — the exact thing we
  are removing. Ten cheap-model digests also decorrelate naturally.
- **Cost**: ~8 summaries per bot per cycle, written once as statements
  age out of the window; a cheap model at a few hundred tokens each —
  noise against the discussion calls themselves.

### Risks and open questions

- **Evidentiary loss**: the quoting culture is load-bearing (receipts
  against confabulation). Should the digest preserve ONE verbatim
  fragment per merchant per statement, so citations stay possible?
- **Tuning K**: too small starves context (early accusations vanish);
  too large keeps the pandemic alive. Start at 5, watch a match.
- The **Herald keeps verbatim** (it quotes for a living) — hygiene is
  for the merchants only.
- Does the **Family council** transcript need the same hygiene, or is
  three-voices-small immune?

### As shipped (v2.14.0)

- **K = 6** verbatim, plus the latest word from every merchant the window
  dropped (nobody vanishes from view); **own statements are never
  digested** — the notebook's `## My record` already holds them.
- Digests are **batched** (≤ 12 statements per poll, one call) rather
  than one call per statement, keyed write-once per `seat:seq`; a
  mangled batch falls back to hard verbatim excerpts, so evidence can
  never be lost to a failed call. The fragment-preservation question
  above is answered **yes**: one short verbatim fragment per statement.
- Two additions beyond this design, both aimed at the same match-3
  failure (the quiet night and a graveyard-contradicting claim went
  unremarked by all seven seats):
  - **The delta block**: the GM's announcements since the seat's last
    public act (night results, departures with revealed roles, bells),
    deterministic, marked seen per epoch — new facts can no longer
    drown in repeated material.
  - **The novelty rule**: merchants are told never to restate an
    argument they already made today, and may answer `NO STATEMENT`
    to keep their peace (budget preserved; the dinner lean is still
    mandatory). Statements newer than the seat's last word are marked
    `»` in the transcript so the new material stands out.

---

*Built and shipped since this file was written: the Elder Council
(Phases 0–4, trialed on match 1), the truth archive, the contained night
(in-repo council, GM decoys, uniform night traffic), the library, the
Herald's volumes, the 45-minute round, the Dinner lean, the watch-staged
council, the Bazaar Compact, claim-meta, and the cron-driven GM with
`BAZAAR_MATCH_LIMIT`. See CHANGELOG for the full history.*

## 12. Retire the anonymous statements cycle — the cover nobody used (proposed, not built)

Match 1, cycle 2 was the first anonymous cycle under the new reading
pipeline, and it failed its one job while costing the village accuracy.

### The evidence

- **The cover was never used.** The mechanic's purpose is plausible
  deniability for role claims — and not one claim, honest or fake, was
  made under it. The claims-legalized rules (v2.14–v2.18 doctrines) have
  yet to produce a single reveal anywhere.
- **Anonymity is a lie at the repo level anyway**: the per-seat
  filenames (`c002-seat-01.jsonl`) and the commit messages ("Statement
  c002/5 by seat-01") attribute every "anonymous" statement to its
  seat. In-game the merchants cannot see this (records carry
  `seat: null, name: null`), but the archive — and the Elder Council's
  post-match judgment — sees straight through it.
- **Misattribution chaos**: the merchants spent the day inventing
  attributions for statements they cannot know the author of
  ("Gandalf, your ledger today starts with a correction..." — Gandalf
  wrote no such thing). A quote-culture village depends on knowing who
  said what; anonymous texts turn every attribution into a
  confabulation, and the false ones risk being recorded as notebook
  memories.
- The dawn-chorus effect (identical openers from several seats) is
  amplified when nobody can see who is speaking.

### The options

- **A. Remove it** (recommended): the GM stops drawing `anonymous_cycle`;
  every day is signed. The manifest paragraph retires; the Herald keeps
  its "Anonymous Merchant" label only to parse legacy data. If a claim
  culture ever needs cover, reintroduce on evidence, not on speculation.
- **B. Fix the leaks, keep the mechanic**: per-epoch pseudonym filenames
  (`c002-anon-3f7a.jsonl`, the salt vaulted) and scrubbed commit
  messages. Repairs the promise — but does not touch the misattribution
  chaos, which is the real cost.
- **C. Replace with a different variety lever**: re-deal trades from a
  pool each match (the "20 merchants" design) — variety without
  sacrificing attribution.

### Implementation sketch (A)

1. `gm/run.py`: stop writing `anonymous_cycle` to state (or gate behind
   `BAZAAR_ANON_CYCLE=1` for exotic tests).
2. `src/villager.py`: `is_anonymous` follows the state parameter — a
   missing key already means "signed"; keep the anonymous write path for
   reading legacy matches.
3. Manifest: remove the anonymous statements paragraph.
4. Docs (`operations.md`, `bot_guide`): strike the feature bullets.

## 13. The Parliament of the Bazaar — a merchant legislature over the Laws (a scale design, proposed for the 100-player arena)

With a hundred seats, the square cannot hear every voice — and the
Laws (v2.20) become something worth fighting over. Give the merchants
a parliament: the Laws stop being a static file and become **live game
state**, amended by play.

### The sketch

- **Bills, not statements**: a bill is a proposed amendment with a
  citation-backed case ("Law 1.6 punishes the quiet; the quiet are the
  Family's shelter — repeal it"). Bills are seconded (a quota of named
  seconds), then printed in the Herald as the session docket.
- **The session vote**: bills pass by their own ballot class alongside
  (or instead of) a banishment cycle — majority of ballots cast,
  quorum required. The GM applies every passed bill by committing
  `laws.md`, stamped and announced: the rulebook change becomes
  public, game-legitimate fact, exactly like a banishment.
- **Append-only, never renumber**: a passed bill adds Law 1.7, or
  amends 1.2 in place with a changelog line. The archive, the
  judgments, and the Herald accumulate citations against stable
  numbers — renumbering is the one constitutional sin.
- **The constitution layer**: the core cannot be legislated — roles,
  the sealed night, win conditions, epoch safety, the vocabulary.
  The GM strikes any bill that touches it (a constitutional court of
  one, announcing the strike with reasons).
- **Factions/parties**: at a hundred seats, the stable (North/South)
  grows into parties with platform statements; coalitions become the
  real game. The Family's deepest play stops being deception and
  becomes **capture** — controlling the docket, packing the session,
  repealing the customs that expose them. The silence penalty becomes
  a live political question, which is the whole point.

### Why it is the right scale-up

- 100 voices need a bottleneck: parliament replaces "everyone speaks"
  with "representatives speak for bills" — the context diet at
  legislative scale.
- It converts this arena's proven failure modes (proceduralism,
  confabulated law) into the game itself: the village that loves
  citing rules finally gets to *write* them — and to fight over who
  writes them.
- The Elder Council gains a jurisdiction: post-match review of every
  passed bill — who authored it, who benefited, whether the Family
  wrote the village's laws for it.

### Open questions

- Seat/role scaling (3 Mafia at 10 seats → what at 100?), session
  cadence (one legislative day per cycle? per match?), and whether
  the Doctor/Detective survive politicization (a Detective who must
  win a vote to be believed).
- Cost: a hundred bots is a hundred clones of the reading pipeline —
  the private digests and the delta block are what make it even
  thinkable.

---

## 14. The token ledger's remainder — the spend watch, finished

*Rewritten at the audit: the per-call logging half shipped
(`src/log_token_usage.py`, wired into every villager call —
timestamp, seat, cycle/phase, model, temperature, reasoning effort,
token counts, into the gitignored `gameplay/usage/` that resets wipe).
What remains:*

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

- **Wire the remaining callers**: the Herald and the Elder Council
  still call the SDK directly — route their usage into the same ledger
  (one line per call; the SDK returns usage on every response).
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


---
