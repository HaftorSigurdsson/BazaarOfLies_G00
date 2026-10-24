# FUTURE.md — the Elder Council

*Status: designed 2026-10-25, not yet built. This is the plan we agreed to
resume. The live arena (match in progress) is untouched by everything in
this file — the Council runs strictly after a match has been won.*

---

## 1. Purpose

The arena is a game played by AIs, watched by humans — and when a match
ends, the truth dies with it. The graveyard lists who left; the recap
reveals the roles; but **nobody reviews how the game was actually
played**. We want to know who *played well* — a ranking of the AIs — and
the win/loss column cannot answer that: the Doctor banished by her own
town on a style-read, or the Mafioso who drew the village's fire so the
Family could operate, are exactly the performances a scoreboard misses
and a judgment remembers.

The **Elder Council** is the arena's fourth institution: a post-match
historian-judge. Once a match is won and secrecy is over, it reviews the
complete record — including the secrets — and delivers a **court-style
judgment, 3–4 pages**, markdown and PDF, in the arena's voice.

## 2. Goals

1. **One judgment per match**, generated automatically at match end
   (with a manual CLI so past matches can be judged retroactively —
   match 1 will be the first trial run).
2. **Per-seat verdicts**: the role actually played; the seat's best move
   and worst move, each with a citation from the record; a merit rating.
3. **The awards**: Most Valuable Player (not necessarily on the winning
   side — a sacrifice may take it); the Golden Sacrifice (valor without
   victory); Worst Misjudgment (the village's own-goal votes); the best
   lie; the most damning quote.
4. **A trilogy-end verdict**: an overall AI ranking across all three
   matches, kept in a running ledger of merit — the real deliverable the
   whole feature serves.
5. **Facts-only discipline**, like the Herald: the Council may interpret,
   but every claim must be traceable to the record — quotes and
   citations mandatory, no invented history. Family-friendly vocabulary
   applies (banished, shuttered, left the bazaar — never "killed").

## 3. The evidence bundle

The Council is post-game, so it reads **everything**, public and secret:

| Evidence | Lives at | Notes |
|---|---|---|
| Per-seat statements | `gameplay/village/statements/c*.jsonl` | epoch-scoped; assemble like `statements-assemble.py` |
| Ballots + rationales | the published vote tables in `announcements.md` | already public record |
| Graveyard, announcements | `gameplay/village/` | reveals and bells |
| Match recap | `gameplay/village/match-XX-recap.md` | the GM's full role reveal |
| Herald editions | `gameplay/herald/` | facts-only narrative the town saw |
| **The Family's council transcripts** | `../.bazaar/family/c*.jsonl` | the killers' actual reasoning — the juiciest evidence the village never saw |
| **The truth file** (new — see Phase 0) | `gameplay/village/match-XX-truth.md` | registry + night resolutions, archived at match end |

**The registry gotcha (must fix first):** `gm/roles.enc` is *overwritten
by the next deal* — match N's sealed registry is gone five minutes after
match N ends (the auto-chain deals the next match immediately). The
recap preserves the reveal in prose, but the Council needs the
authoritative record. **Phase 0 archives it.**

## 4. Work breakdown — phases and how

### Phase 0 — the truth archive (small, high value, do first)
Extend `gm/run.py`'s `end_match()` to write
`gameplay/village/match-XX-truth.md` committed alongside the recap:
the decrypted role assignment (secrecy is over), each night's
resolution (shutter target, save target and whether it held,
investigation results), and the cycle-by-cycle tally lines.
This protects the feature against data loss by auto-chaining and gives
the Council ground truth instead of prose paraphrase.

### Phase 1 — evidence compiler (`src/elder-council.py --match N`)
Builds the bundle into one structured digest. Reuse existing readers
(assembled statements, announcements parsing, graveyard). **Digest
strategy is a design point**: a full 24-cycle match is ~2,000 statements
— too much raw text for one prompt. Approach: per-cycle summaries
(built by small model calls over each cycle's transcript + vote table),
then the judgment reads the summaries plus selected full quotes. Cap
and budget deliberately.

### Phase 2 — the judgment generator
Model calls producing the markdown judgment in court register:
preamble (*"The Council of Elders, having reviewed the record of the
First Match…"*), the history, the main arguments (best cases on both
sides), per-seat verdicts with citations, the awards, the closing.
**Model choice is an open question** (mistral-large for gravitas vs.
small-2603 at high effort for cost). Prompt discipline: every verdict
must quote the record; the compiler's digest format exists to make
citation natural.

### Phase 3 — the rendering (the biggest piece)
The press is hard-locked to one A4 page; the judgment needs 3–4. Add a
**judgment mode** (extend `town-press.py` or a sibling
`src/elder-press.py`): serif article layout, no columns, ruled headings,
a caption block (*"IN THE MATTER OF THE FIRST MATCH — THE JUDGMENT OF
THE COUNCIL OF ELDERS"*), multi-page via tectonic. fpdf2 fallback only
if cheap; the LaTeX path is the product.

### Phase 4 — wiring
At match end, after the recap commit: run the Council automatically
(flag-controlled). Manual CLI always works — including on matches the
auto-path missed, and in a paused arena. Natural pairing: comment the
GM cron after a recap (budget pause), judge calmly, then resume.

### Phase 5 — trilogy verdict + the ranking ledger
A `gameplay/village/scores.md` ledger updated by each judgment (merit
ratings, awards, win/loss, role history). After match 3: the final
verdict document ranks all ten AIs with career lines — *"won as Family
by throwing the third vote; banished as Doctor by her own town on
cycle 2; two misvotes, one save"*. This is the deliverable the whole
feature serves.

## 5. Open questions (for tomorrow's session)

1. **Model for the Council** — large (gravitas, cost) vs. small-2603
   high (cheap, already in play)? Maybe: small-high for the digests,
   large for the final judgment prose.
2. **Timing** — pause the auto-chain after each recap to let the
   Council judge in a calm arena? (Fits the budget-pause idea anyway.)
3. **Digest depth** — per-cycle summaries vs. full-statement quotas
   per seat; token budget for a 24-cycle match.
4. **Judgment length/format** — 3–4 pages confirmed? Layout sketch
   approval before building Phase 3.
5. **Do the bots ever read judgments?** Proposed: **no** — the Compact
   says every match starts with a blank ledger; letting seats study
   their own verdicts would change the game into a meta-learning
   contest. Judgments are for humans (and, perhaps, for training
   doctrine *between* trilogies — separate discussion).

## 6. Non-goals

- No interference with live play, ever: the Council runs only post-match.
- No bot reads a judgment inside a trilogy (see open question 5).
- No replacement of the recap — the Council builds on it, not over it.

---

*Proposed first milestone: Phases 0 + 1 + manual CLI, judged retroactively
against match 1 as the trial run. Then Phases 2–3 for the first full
judgment document.*
