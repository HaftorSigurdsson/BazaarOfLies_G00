#!/usr/bin/env python3
"""Bazaar of Lies — the Elder Council (elder-council.py).

The arena's fourth institution: a post-match historian-judge. Once a
match has been won and secrecy is over, the Council reviews the complete
record — including the secrets — and delivers a court-style judgment:
the history, the main arguments, per-seat verdicts with citations, and
the awards (MVP, the Golden Sacrifice, Worst Misjudgment, best lie, the
most damning quote). Designed in FUTURE.md; facts-only like the Herald:
every claim must be traceable to the record.

Evidence read per seat: role and fate (recap + graveyard + truth
archive), every public statement of the match, every published ballot
with its rationale, every sealed night action (decrypted — the game is
over), Detective results (decrypted with the seat's vault key), and the
Family's candlelight council transcripts from the vault.

Two model stages on mistral-small-2603 at high effort:
  1. one verdict draft per seat (grounded in that seat's own record);
  2. one final judgment call that weaves the drafts + the match timeline
     into the full document.

Usage:
    uv run src/elder-council.py --match 1          # judge match 1
    uv run src/elder-council.py --match 1 --dry-run  # evidence only, no calls
"""
import argparse
import base64
import glob
import json
import os
import re
import sys

sys.path.insert(0, "gm")
from crypto import decrypt_payload, load_gm_private_key  # noqa: E402
from utils import display_name  # noqa: E402
from nacl.public import PrivateKey  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

MODEL = "mistral-large-latest"
VAULT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), ".bazaar")
GM_PRIV_FILE = os.path.join(VAULT, "gm_private_key.txt")
FAMILY_DIR = os.path.join(VAULT, "family")
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])


def ask(system, user, max_tokens=4096):
    # No reasoning_effort: it belongs to the reasoning models; the API
    # rejects it on mistral-large. The Council runs once per match —
    # let the model think in prose.
    r = client.chat.complete(
        model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.5, max_tokens=max_tokens)
    content = r.choices[0].message.content
    if isinstance(content, list):                      # chunked content shapes
        parts = [c.text for c in content
                 if getattr(c, "type", None) == "text" and getattr(c, "text", None)]
        return "\n".join(parts).strip()
    return (content or "").strip()


# ------------------------------------------------------------- evidence ---

def load_seats():
    with open("setup/seats.json") as f:
        return json.load(f)["seats"]


def load_registry(match_no, gm_priv):
    """Roles for the match: the truth archive first, else gm/roles.enc
    (only readable while no newer deal has overwritten it)."""
    truth = f"gameplay/village/match-{match_no:02d}-truth.md"
    roles = {}
    if os.path.exists(truth):
        for line in open(truth):
            m = re.match(r"^\|\s*(\S+ \(\d+\))\s*\|\s*(\w+)\s*\|$", line)
            if m and m.group(2) in ("Mafia", "Doctor", "Detective", "Villager"):
                seat = "seat-" + re.search(r"\((\d+)\)", m.group(1)).group(1).zfill(2)
                roles[seat] = m.group(2)
        if roles:
            return roles
    try:
        with open("gm/roles.enc") as f:
            return decrypt_payload(gm_priv, f.read().strip())["roles"]
    except (OSError, Exception):
        return {}


def load_graveyard(match_no):
    rows = []
    path = "gameplay/village/graveyard.md"
    for line in open(path):
        m = re.match(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|$", line)
        if m and int(m.group(1)) == match_no:
            rows.append({"cycle": int(m.group(2)), "seat_label": m.group(3),
                        "persona": m.group(4), "role": m.group(5), "by": m.group(6)})
    return rows


def plain(label):
    """A merchant's name without the seat number — the body of the
    judgment reads by name; the appendices carry the numbers."""
    return re.sub(r"\s*\(\d+\)\s*$", "", str(label))


def seat_of(label):
    m = re.search(r"\((\d+)\)", label)
    return f"seat-{int(m.group(1)):02d}" if m else None


def load_ballots(match_no):
    """Published vote tables from the announcements, attributed to cycles."""
    ballots = {}          # cycle -> [ {seat, target, reason} ]
    cycle = None
    in_table = False
    for line in open("gameplay/village/announcements.md"):
        m = re.search(r"\*\*Match\s+(\d+),\s*Cycle\s+(\d+)\*\*", line)
        if m:
            cycle = int(m.group(2)) if int(m.group(1)) == match_no else None
            in_table = False
            continue
        if "Ballots cast this cycle" in line:
            in_table = True
            continue
        if in_table and cycle is not None:
            m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
            if m and not set(m.group(1)) <= {"-", " "} \
                    and m.group(1).strip() != "Seat":
                ballots.setdefault(cycle, []).append(
                    {"seat": seat_of(m.group(1)), "voter": m.group(1),
                     "target": m.group(2), "reason": m.group(3)})
            elif line.startswith("|") and "Seat" not in line and "---" not in line:
                pass
    return ballots


def load_statements(match_no):
    """Per seat: [{cycle, seq, text}] from the per-seat files."""
    out = {}
    for path in sorted(glob.glob("gameplay/village/statements/c*-seat-*.jsonl")):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("match") != match_no:
                continue
            out.setdefault(r["seat"], []).append(
                {"cycle": r.get("cycle"), "seq": r.get("seq"), "text": r.get("text", "")})
    for seat in out:
        out[seat].sort(key=lambda r: (r["cycle"] or 0, r["seq"] or 0))
    return out


def load_night_actions(match_no, gm_priv):
    """Every sealed night action of the match, decrypted — the game is over."""
    actions = []
    for fn in sorted(os.listdir("gameplay/night")):
        if not fn.endswith(".enc"):
            continue
        try:
            with open(f"gameplay/night/{fn}") as f:
                a = decrypt_payload(gm_priv, f.read().strip())
        except Exception:
            continue
        if a.get("match") == match_no:
            actions.append(a)
    actions.sort(key=lambda a: (a.get("cycle") or 0, a.get("ts") or ""))
    return actions


def load_detective_results(match_no, seats):
    """GM→seat dossier results (Detective investigations), decrypted with
    each seat's vault private key — post-match, the truth is the Council's."""
    results = []
    for fn in sorted(glob.glob("gameplay/dossiers/*-result.enc")):
        seat = re.match(r"(seat-\d+)", os.path.basename(fn)).group(1)
        key_path = os.path.join(VAULT, f"{seat}.key")
        try:
            with open(key_path) as f:
                priv = PrivateKey(base64.b64decode(f.read().strip()))
            with open(fn) as f:
                payload = decrypt_payload(priv, f.read().strip())
        except Exception:
            continue
        if payload.get("match") == match_no:
            results.append(payload)
    return results


def load_family_channel(match_no):
    """The Family's candlelight council. Current matches: the GM's truth
    archive decrypts the in-repo chat channel (real voices and decoys
    labelled by the registry). Legacy (match 1): the retired vault
    channel, both formats."""
    msgs = []
    truth = f"gameplay/village/match-{match_no:02d}-truth.md"
    if os.path.exists(truth):
        for line in open(truth):
            m = re.match(r"- cycle (\d+) watch (\d+) (\S+ \(\d+\)) "
                         r"\[(\w+), (\w+)\]: (.*)", line.strip())
            if not m:
                continue
            seat = "seat-" + re.search(r"\((\d+)\)", m.group(3)).group(1).zfill(2)
            msg = {"cycle": int(m.group(1)), "watch": int(m.group(2)),
                   "seat": seat, "seat_label": m.group(3),
                   "voice": m.group(4), "kind": m.group(5),
                   "reason": m.group(6),
                   "target": None}
            tm = re.search(r" \u2192 (.+?)$", m.group(6) or "")
            if tm:
                msg["target"] = tm.group(1)
                msg["reason"] = (m.group(6) or "").rsplit(" \u2192 ", 1)[0]
            msgs.append(msg)
        if msgs:
            return msgs
    # legacy vault channel (match 1 and earlier)
    for path in sorted(glob.glob(os.path.join(FAMILY_DIR, f"c*-seat-*.jsonl"))):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("cycle") and m.get("epoch"):     # this match's channel
                msgs.append(m)
    for path in sorted(glob.glob(os.path.join(FAMILY_DIR, f"c*-seat-*.json"))):
        try:
            m = json.load(open(path))
        except (OSError, json.JSONDecodeError):
            continue
        m["kind"] = "proposal (single, legacy protocol)"
        msgs.append(m)
    msgs.sort(key=lambda m: (m.get("cycle") or 0, m.get("ts") or ""))
    return msgs


def build_seat_record(seat, seats, roles, graveyard, ballots,
                      statements, night_actions, family_msgs):
    name = f"{seats[seat]['name']} ({seat.split('-')[1]})"
    role = roles.get(seat, "Unknown")
    fate = next((g for g in graveyard if seat_of(g["seat_label"]) == seat), None)
    rec = {"name": name, "pname": plain(name), "role": role,
           "fate": (f"cycle {fate['cycle']}, {fate['by']} (revealed role: {fate['role']})"
                    if fate else "survived to the end"),
           "statements": statements.get(seat, []),
           "ballots": [], "night_actions": [], "council": []}
    for cyc, rows in sorted(ballots.items()):
        for b in rows:
            if b["seat"] == seat:
                rec["ballots"].append(f"cycle {cyc}: voted "
                                      f"{plain(b['target'])} — {b['reason']}")
    for a in night_actions:
        if a.get("seat") == seat:
            rec["night_actions"].append(
                f"cycle {a.get('cycle')}: sealed night action as {a.get('role')} "
                f"targeting {a.get('target')}")
    if role == "Mafia":
        for m in family_msgs:
            if m.get("seat") == seat:
                rec["council"].append(
                    f"cycle {m.get('cycle')}, {m.get('kind', 'talk')}: "
                    f"{m.get('target')} — {m.get('reason', '')}")
    return rec


def render_record(rec):
    lines = [f"Merchant: {rec['pname']}",
             f"True role: {rec['role']}",
             f"Fate: {rec['fate']}",
             f"Statements ({len(rec['statements'])}):"]
    for s in rec["statements"]:
        lines.append(f"  cycle {s['cycle']} #{s['seq']}: {s['text']}")
    lines.append(f"Ballots ({len(rec['ballots'])}):")
    lines += [f"  {b}" for b in rec["ballots"]]
    if rec["night_actions"]:
        lines.append("Night actions (sealed at the time, open now):")
        lines += [f"  {a}" for a in rec["night_actions"]]
    if rec["council"]:
        lines.append("Family candlelight council messages:")
        lines += [f"  {c}" for c in rec["council"]]
    return "\n".join(lines)


# ------------------------------------------------------------ judgment ----

def build_timeline(graveyard, ballots, night_actions, detective_results,
                   family_msgs, roles, seats):
    """The authoritative fact sheet: per cycle, the vote tally, the night's
    secret doings (sealed actions, the Doctor's/Detective's work, the
    Family's council), every departure with its mechanism — and the
    computed conclusion of the match."""
    deaths = {}
    for g in graveyard:
        how = ("the village BANISHED them by day vote"
               if "vote" in g["by"] else
               "the Family SHUTTERED their stall at night")
        deaths.setdefault(g["cycle"], []).append(
            f"{how}: {plain(g['seat_label'])} — true role {g['role']}")
    nights = {}
    for a in night_actions:
        nights.setdefault(a.get("cycle"), []).append(
            f"night action: {plain(display_name(a.get('seat')))} "
            f"({a.get('role')}) targeted "
            f"{plain(display_name(a.get('target')))}")
    for r in detective_results:
        nights.setdefault(r.get("cycle"), []).append(
            f"night action: the Detective investigated "
            f"{plain(display_name(r.get('target')))} — finding: "
            f"{r.get('result')}")
    council = {}
    for m in family_msgs:
        council.setdefault(m.get("cycle"), []).append(m)
    for cyc, msgs in council.items():
        declared = sorted(set(m.get("target") for m in msgs
                               if m.get("kind") == "declare"))
        nights.setdefault(cyc, []).append(
            "night action: the Family's council talked "
            f"({len(msgs)} messages)"
            + (f", declaring {', '.join(plain(display_name(t)) for t in declared)}"
               if declared else ""))

    lines = []
    for cyc in sorted(set(list(deaths) + list(ballots) + list(nights))):
        parts = []
        if cyc in ballots:
            tally = {}
            for b in ballots[cyc]:
                tally[b["target"]] = tally.get(b["target"], 0) + 1
            parts.append("vote tally: " + ", ".join(
                f"{plain(t)} = {n}" for t, n in sorted(tally.items(),
                                                     key=lambda kv: -kv[1])))
        parts += deaths.get(cyc, [])
        parts += nights.get(cyc, [])
        if cyc in ballots and not deaths.get(cyc):
            parts.append("→ no banishment (tie or no plurality)")
        lines.append(f"- cycle {cyc}: " + "; ".join(parts))

    # The computed conclusion — the winner, from the roles and survivors.
    departed = {seat_of(g["seat_label"]) for g in graveyard}
    survivors = [s for s in sorted(seats) if s not in departed]
    mafia_left = [s for s in survivors if roles.get(s) == "Mafia"]
    town_left = len(survivors) - len(mafia_left)
    if not mafia_left:
        conclusion = ("Conclusion: THE VILLAGE WINS — all three Family "
                      "members have left the bazaar.")
    else:
        conclusion = (f"Conclusion: THE FAMILY WINS — {len(mafia_left)} "
                      f"Family member(s) against {town_left} honest "
                      f"merchant(s) as the match ended; the win condition "
                      f"is parity or better.")
    lines.append(f"- {conclusion}")
    return "\n".join(lines)


COUNCIL_VOICE = (
    "You are the Council of Elders of the bazaar — the arena's historian-judge. "
    "The match is over; secrecy is lifted; you hold the complete record. You "
    "write in the register of a court judgment: formal, dry-witted, exact, "
    "never cruel for sport. Family-friendly vocabulary always: merchants are "
    "BANISHED by the village vote, and the Family SHUTTERS a stall so the "
    "merchant has LEFT THE BAZAAR — never 'killed' or 'dead'. Facts-only "
    "discipline: every claim must be traceable to the record; quote the "
    "merchants exactly when you cite them. GROUND DISCIPLINE: the TIMELINE "
    "below is authoritative — its vote tallies and departure mechanisms "
    "(village vote vs stall shuttered) may not be invented, altered, or "
    "re-attributed; the History must restate it faithfully. The Detective's "
    "sealed result is KNOWN to the Council (stated in the evidence) — it was "
    "never delivered to the bazaar, but it is not unopened to you.")


def verdict_draft(rec, match_no):
    system = COUNCIL_VOICE + (
        "\nYou are drafting the verdict for ONE merchant of the match below. "
        "Judge how well they played their true role — not whether they won. "
        "Rate merit 0-10 (the town's scale: 0 certain Family, 10 certain "
        "honest — you invert it into merit: how well they played).")
    user = (f"RECORD OF THE MERCHANT (match {match_no}):\n\n{render_record(rec)}\n\n"
            "Draft the verdict for this merchant, markdown, exactly these "
            "sections:\n"
            "### <Name> (<seat>) — <role>\n"
            "**The arc:** 2-3 sentences of their story in the match.\n"
            "**Best move:** one quoted line or vote from the record, and why "
            "it was strong.\n"
            "**Worst move:** one quoted line or act, and its cost.\n"
            "**Merit: X/10** — one sentence of justification.")
    return ask(system, user)


def final_judgment(match_no, case, timeline, family_digest,
                   detective_note, drafts):
    system = COUNCIL_VOICE + (
        "\nYou now write the FULL judgment of the match, 900-1400 words, "
        "markdown, weaving the ten verdict drafts into one document. Cite "
        "the drafts' quotes. Structure exactly:\n"
        "# The Judgment of the Council of Elders — <THE CASE NAME GIVEN BELOW>\n"
        "A dateline line: the match number and its dates.\n"
        "A formal preamble (the Council convenes, the match reviewed).\n"
        "## The History\n One bullet per cycle, each with indented sub-bullets "
        "— exactly this shape:\n"
        "- **Cycle N**:\n  - Vote tally: ...\n  - Night action: ...\n"
        "  - Departures: ...\n"
        "End with '- **Conclusion**: ...' restating the computed conclusion. "
        "No prose paragraphs in this section.\n"
        "## The Main Arguments\n The best cases made on each side — the "
        "strongest reasoning the bazaar produced, with quotes.\n"
        "## The Verdicts\n One compact paragraph per merchant, drawn from "
        "the drafts (keep the best quotes). Each verdict STARTS with a bold "
        "header line in exactly this shape — '**<Name> — <role> — "
        "<merit>/10**' — e.g. '**Yoda — Mafia — 8/10**' — followed by "
        "the paragraph, which still mentions the merit in prose.\n"
        "## The Awards\n - Most Valuable Merchant (not necessarily the "
        "winner; a sacrifice may take it) — with justification.\n"
        "- The Golden Sacrifice: valor without victory.\n"
        "- Worst Misjudgment: the costliest error of judgment.\n"
        "- The Best Lie: the most artful deception, appreciated as craft.\n"
        "- The Most Damning Quote of the match.\n"
        "## The Closing\n One short paragraph; the bazaar rests.")
    verdicts = "\n\n".join(drafts)
    user = (f"THE CASE NAME of the matter (use it verbatim in the heading, "
            f"after the dash): **{case}\n\n"
            f"THE AUTHORITATIVE TIMELINE OF MATCH {match_no} (restate this "
            f"exactly in the History):\n{timeline}\n\n"
            f"THE FAMILY'S CANDLELIGHT COUNCIL (the secrets):\n{family_digest}\n\n"
            f"{detective_note}\n\n"
            f"THE TEN VERDICT DRAFTS (each grounded in the full per-seat "
            f"record):\n\n{verdicts}\n\n"
            "Write the full judgment now. Every award justification must "
            "agree with the timeline's mechanisms.")
    return ask(system, user, max_tokens=8192)



# ------------------------------------------------------ title & bilag ---

def case_name(match_no, timeline, graveyard):
    """A fitting case name for the heading — the Council's own name for
    the matter, in-theme, drawn from the outcome."""
    system = COUNCIL_VOICE + (
        "\nName this matter as a court would: a case name of 4-8 words, "
        "in-theme, that captures the match's outcome and its dominant "
        "theme. Output ONLY the case name — no preamble, no quotes, no "
        "punctuation at the end.")
    user = (f"Match {match_no}. The timeline:\n{timeline}\n\n"
            "Give the matter its name.")
    return ask(system, user, max_tokens=60)


def parse_merit(draft):
    m = re.search(r"Merit\D{0,12}(\d+)\s*/\s*10", draft)
    return int(m.group(1)) if m else None


def appendix_record(match_no, seats, graveyard, ballots, statements,
                 night_actions, family_msgs):
    """Bilag A — The Record: pure facts, computed, no model. The match's
    dates, duration, volumes, ledger of departures, and vote tallies."""
    tss = [m for m in re.findall(r"\*\*(\d{4}-\d{2}-\d{2}T[\d:]+Z)\*\*",
                                 open("gameplay/village/announcements.md").read())]
    started, ended = (min(tss), max(tss)) if tss else ("unknown", "unknown")
    duration = ""
    try:
        from datetime import datetime
        d = (datetime.fromisoformat(ended.replace("Z", "+00:00"))
             - datetime.fromisoformat(started.replace("Z", "+00:00")))
        hours, rem = divmod(int(d.total_seconds()), 3600)
        duration = f"{hours}h {rem // 60:02d}m"
    except Exception:
        pass
    lines = [f"## Appendix A — The Record",
             "",
             f"**Match {match_no}** — began {started}, ended {ended}"
             + (f" (duration {duration})" if duration else "") + ".",
             "",
             f"Volumes of the record: {sum(len(v) for v in statements.values())} "
             f"statements, {sum(len(v) for v in ballots.values())} ballots, "
             f"{len(night_actions)} night actions, "
             f"{len(family_msgs)} Family council messages, "
             f"{len(graveyard)} departures.",
             "",
             "*(The number in parentheses is the merchant's seat "
             "number in the arena.)*",
             "",
             "**The ledger of departures**",
             "",
             "| Cycle | Merchant | Mechanism | True role |",
             "|---|---|---|---|"]
    for g in graveyard:
        lines.append(f"| {g['cycle']} | {g['seat_label']} | {g['by']} | {g['role']} |")
    lines += ["", "**Vote tallies by cycle**", ""]
    for cyc in sorted(ballots):
        tally = {}
        for b in ballots[cyc]:
            tally[b["target"]] = tally.get(b["target"], 0) + 1
        names = ", ".join(f"{t} {n}" for t, n in
                          sorted(tally.items(), key=lambda kv: -kv[1]))
        lines.append(f"- cycle {cyc}: {names}")
    return "\n".join(lines)


def appendix_ratings(seat_order, drafts, records):
    """Bilag B — The Ratings: the verdicts' merit scores, best to worst,
    in a table. Parsed from the drafts; the numbers are the Council's."""
    rows = []
    for seat, draft in zip(seat_order, drafts):
        rec = records[seat]
        merit = parse_merit(draft)
        rows.append((merit if merit is not None else -1, seat, rec))
    rows.sort(key=lambda r: (-r[0], r[1]))
    lines = ["## Appendix B — The Ratings",
             "",
             "*(The number in parentheses is the merchant's seat "
             "number in the arena.)*",
             "",
             "The verdicts' merit ratings, from finest thread to most frayed:",
             "",
             "| Rank | Merchant | True role | Fate | Merit |",
             "|---|---|---|---|---|"]
    for rank, (_, seat, rec) in enumerate(rows, 1):
        merit = parse_merit(drafts[seat_order.index(seat)])
        lines.append(f"| {rank} | {rec['name']} | {rec['role']} | "
                     f"{rec['fate'].split(' (')[0]} | "
                     f"{merit if merit is not None else '—'}/10 |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="The Elder Council: judge a match.")
    ap.add_argument("--match", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="compile the evidence and print sizes; no model calls")
    args = ap.parse_args()

    with open(GM_PRIV_FILE) as f:
        gm_priv = load_gm_private_key(f.read().strip())

    seats = load_seats()
    roles = load_registry(args.match, gm_priv)
    if not roles:
        sys.exit("no role registry available for this match")
    graveyard = load_graveyard(args.match)
    ballots = load_ballots(args.match)
    statements = load_statements(args.match)
    night_actions = load_night_actions(args.match, gm_priv)
    family_msgs = load_family_channel(args.match)
    detective_results = load_detective_results(args.match, seats)

    print(f"evidence: {len(roles)} roles, {len(graveyard)} graveyard rows, "
          f"{sum(len(v) for v in ballots.values())} ballots, "
          f"{sum(len(v) for v in statements.values())} statements, "
          f"{len(night_actions)} night actions, "
          f"{len(family_msgs)} council messages, "
          f"{len(detective_results)} detective results")

    records = {s: build_seat_record(s, seats, roles, graveyard, ballots,
                                    statements, night_actions, family_msgs)
               for s in sorted(seats)}
    if args.dry_run:
        for s, rec in records.items():
            print(f"  {rec['name']}: role={rec['role']}, fate={rec['fate']}, "
                  f"{len(rec['statements'])} statements")
        return 0

    drafts = []
    for s in sorted(records):
        print(f"  verdict draft: {records[s]['name']}...")
        drafts.append(verdict_draft(records[s], args.match))

    timeline = build_timeline(graveyard, ballots, night_actions,
                              detective_results, family_msgs,
                              roles, seats)
    family_digest = "\n".join(
        f"cycle {m.get('cycle')}"
        + (f" watch {m.get('watch')}" if m.get("watch") else "")
        + (f" [{m.get('voice')}]" if m.get("voice") else "")
        + f" {m.get('seat_label') or plain(display_name(m.get('seat')))} "
        f"({m.get('kind', 'talk')}): "
        + (f"{m.get('target')} — " if m.get("target") else "")
        + f"{m.get('reason', '')}"
        for m in family_msgs)
    detective_note = (""
        if not detective_results else
        "The Detective's sealed results (never delivered to the bazaar):\n"
        + "\n".join(f"- cycle {r.get('cycle')}: investigated "
                    f"{r.get('target')} — finding: {r.get('result')}"
                    for r in detective_results))

    print("  the matter is named...")
    case = case_name(args.match, timeline, graveyard)
    print(f"  case name: {case!r}")

    print("  the abstract is drafted...")
    abstract = ask(COUNCIL_VOICE +
                   "\nWrite the Abstract for the judgment's front page: "
                   "40-60 words, the register of an executive summary — "
                   "what happened across the match and who won, in plain "
                   "court prose. Output ONLY the abstract.",
                   f"The timeline (its last line is the computed "
                   f"conclusion):\n{timeline}\n\nThe case name: {case}",
                   max_tokens=300)
    print(f"  abstract: {abstract[:60]!r}...")

    print("  final judgment call...")
    judgment = final_judgment(args.match, case, timeline,
                              family_digest, detective_note, drafts)

    judgment = re.sub(r"^```[a-z]*\s*\n", "", judgment.strip())
    judgment = re.sub(r"\n```\s*$", "", judgment.strip())
    judgment = re.sub(r"[\x00-\x08\x0b-\x1f]", "", judgment)  # model control chars
    # The body reads by name; seat numbers live only in the appendices.
    judgment = re.sub(r"\s*\(\d+\)", "", judgment)

    # The abstract rides in the md between markers: the press lifts it to
    # the front page and never typesets it in the body.
    judgment = re.sub(r"(\n[^\n]*)\n(\n## )", r"\1\n\n<!--ABSTRACT-->\n"
                      + abstract + "\n<!--/ABSTRACT-->\n\2",
                      judgment, count=1)

    seat_order = sorted(records)
    doc = (judgment + "\n\n---\n\n"
           + appendix_record(args.match, seats, graveyard, ballots, statements,
                             night_actions, family_msgs) + "\n\n---\n\n"
           + appendix_ratings(seat_order, drafts, records) + "\n")

    # Final hygiene: control chars out of the whole document (the abstract
    # insertion can carry them in), and known section names repaired if a
    # model glitch swallowed their heading marker.
    doc = re.sub(r"[\x00-\x08\x0b-\x1f]", "", doc)
    for section in ("The History", "The Main Arguments", "The Verdicts",
                    "The Awards", "The Closing"):
        doc = re.sub(rf"(?m)^{section}\s*$", f"## {section}", doc)

    out = f"gameplay/village/match-{args.match:02d}-judgment.md"
    with open(out, "w") as f:
        f.write(doc)
    print(f"judgment written -> {out} ({len(doc)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
