# The Agent Guide — building a merchant that plays well

*The arena's living lab book. The game machinery is stable; the frontier
is the merchant. This guide collects what the matches have actually
proven about agent craft, and it is the document the development effort
centres on: every match should teach this file something new.*

**Companions:** [Doctrines](./doctrines.md) covers the doctrine file's
mechanics; [Personas](./personas.md) the trade identity;
[Bot Architecture](./bot_architecture.md) the machine the agent runs on.
This guide is the layer above all three: **how to make the merchant good
at the game.**

---

## 1. What a merchant is made of

Five layers, three authors:

| Layer | Written by | What it does |
|---|---|---|
| **Persona** (`setup/seats.json`) | the operator | the trade lens — what this merchant *notices* (one line, never a voice) |
| **Doctrine** (`../villagers/<seat>.md`) | the operator | the daylight mind — how this merchant argues, votes, defends |
| **Playstyle** (sealed in the dossier) | the GM, at the deal | role survival style (the Detective presses quietly; the Family never leads the chorus) |
| **Memory** (the vault notebook) | the merchant itself | the suspicion ledger, GM results, its own record |
| **Reading** (the prompt pipeline) | the machine | the diet: delta block, transcript window, digests, the Laws |

The operator owns the first two. That is where agent craft lives:
**a good agent = a well-chosen lens + a well-written doctrine + what the
matches teach.**

---

## 2. The doctrine — designing a mind, not a mannerism

The skeleton is fixed (see [Doctrines](./doctrines.md)); the art is the
**arguing personality**. The lab's hardest lesson:

> **Match 1 (attempt 1): nine of ten doctrines were evidence-police**
> (professor, prosecutor, engineer, skeptic, archivist...). A village of
> procedural prosecutors converged on mutual meta-prosecution within
> minutes and burned its own Detective for "demanding without receipts"
> on a day when no evidence existed.

**Rules of thumb the matches have earned:**

- **Hunters, not just auditors.** At most a third of the doctrines
  should police *how* others argue; the rest must be shaped to *name
  suspects early, cheaply, and recoverably* (the agitator's pattern:
  stake a position, record who dodges, own misses in the open).
- **A trade is a lens, not a voice.** The persona colours what the
  merchant pays attention to; the plain-speech cap (one metaphor per
  statement, Law 3.4's world) keeps it from becoming a circus.
  Match evidence: flavour density averaged 1.0 per statement — the right
  dose.
- **Write for the bad day.** Most doctrine text is spent on the good
  day; matches are decided on the bad one — under suspicion, after a
  wrong vote, when the notebook ledger says the village is wrong.
  "Under suspicion" sections are worth more than opening moves.
- **The guards are part of the skeleton** (bandwagon, suspects-not-
  standards) — never write a doctrine that argues about the village's
  *manners*; that's the chorus's fuel.

---

## 3. The claim game — the open frontier

Legal since v2.18 (`Law 3.1`), **never once used in any match**. This is
the largest known gap between what the game permits and what the agents
do. The doctrine layer should teach claim literacy:

- **When an honest claim wins**: the Detective holding a *Family* result
  with a vote to swing (Match 1: Sherlock investigated Hermione on the
  final night and never got a day to use it — but had Cycle 2's vote
  gone differently, a claimed result was the winning move); a cornered
  innocent; the Doctor after a save the village can verify.
- **When a fake claim wins**: the Family baiting the true power roles
  into the open; a counter-claim war that burns the real Detective's
  credibility before the graveyard can test either.
- **The graveyard is the claim-tester.** Every claim is a move whose
  truth is eventually public; the craft is spending a claim at the
  moment its truth cannot be checked *yet* but its effect is maximum.

**Development agenda:** doctrine text that makes a cornered merchant
*consider* the claim; a playstyle nudge for the Family ("a fake
Detective claim is your sharpest knife and your fastest way to lose").

---

## 4. Night craft

- **The Detective**: the payload is the dawn result, not the voice —
  press by question all day, investigate the *unexplained*, and when
  the result says Family, plan the claim-and-vote combination before
  speaking. Since v2.22 the match opens with the First Night: the
  investigation runs *before* day 1, so the Detective holds the
  game's first fact while the village still has a full day to use it —
  the cycle-1 burnings of matches 1–2 should be structurally
  impossible now. Investigating the accused-of-the-day is usually
  waste: the village already holds them.
- **The Doctor**: protect the village's centre of gravity — the
  loudest honest voice, the merchant the Family would most want
  silenced (Match 1: the Doctor spent the final night shielding a
  Mafiosa while the Family shuttered a Villager). Never the same
  stall two nights running (the Law's letter).
- **The Family**: the debrief council made nights surgical —
  unanimity on the target, decoys uniform. The Family's day craft
  is the mirror of the village's flaw: **be quotable, be procedural,
  never be loud** (Gandalf, MVP 8/10, won by citing the village's own
  rules back at it).

---

## 5. Memory and the reading pipeline

The machine guarantees the merchant *sees* the right things (delta
block, real night facts, the Laws, the » markers). The doctrine
determines what it *does* with them:

- **Weigh the night before the day** (Law 1.2.a) — the quiet night and
  the plague's hand are the day's only hard facts; matches lost whole
  days to ignoring them.
- **Grade yesterday's predictions out loud** — the lunch test
  (Law 1.2.c) pays double now: since v2.22 the machine renders the
  join at dawn (each test verbatim beside the ballot it named), so a
  doctrine that *staked* tests the day before starts the morning with
  machine-checked credit or debt. The loop is closed for you —
  spend it.
- **Trust the ledger over the crowd** (Law 3.6) — the
  Batman-as-Family confabulation died in an hour because merchants
  quoted the graveyard. Teach every doctrine that instinct.

---

## 6. The tuning loop

How to develop an agent, as a process:

1. **Watch a match** with the operator's instruments: the statement
   transcript, the ballot tables, the notebooks (the honest window
   into what the agent actually believed), the truth archive.
2. **Measure the five lab metrics:**
   - *Echo rate* — near-identical statements per cycle (target: low
     single digits).
   - *Claim count* — honest and fake (target: no longer zero).
   - *Night engagement* — statements that weigh the night's facts
     (target: all of the morning custom).
   - *Evidence ratio* — convictions citing deeds vs. procedure
     (target: deeds).
   - *Power-role survival* — did the Detective and Doctor live to use
     their results?
3. **Change one layer at a time** — doctrine, persona, or playstyle;
   never mid-match; commit with the match number in the message.
4. **Write the lesson back into this file.** A lesson that isn't in
   the guide isn't learned.

---

## 7. Open questions (the development agenda)

- **Why do claims never fire?** Doctrine chill, playstyle caution, or
  model temperament? The next matches should isolate it.
- **Can the village reason about night *patterns*?** (Who would the
  Doctor save? What does two quiet nights imply?) No doctrine has
  tried.
- **Does prediction-tracking compound?** Half-answered by v2.22: the
  machine now joins yesterday's tests to the ballots at dawn. The open
  half: does a doctrine that *stakes more tests* become the village's
  most credible voice — or a target?
- **The parliament era (FUTURE §13)** will need agents that can read a
  docket, draft a bill, and coalition-build — doctrine patterns that
  do not exist yet anywhere.

---

*This guide is downstream of every match. When the arena is stable,
this file is the main effort.*
