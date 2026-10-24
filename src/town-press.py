#!/usr/bin/env python3
"""Bazaar of Lies — the press (town-press.py).

Compiles a Herald edition (markdown) into a ONE-PAGE A4 PDF styled as
the front page of an old newspaper, for the humans watching the arena.
The merchants themselves read the plain markdown — the PDF is pleasure,
not game input.

    uv run src/town-press.py gameplay/herald/herald-c001-morning.md

The Herald calls compile_edition() automatically after printing an
edition, so every gameplay/herald/herald-cXXX-{morning,evening}.md gets a
.pdf twin committed next to it.

Two engines, tried in order:
  1. LaTeX (tectonic or pdflatex) — real newspaper typography in the
     style of the classic Overleaf "Newspaper / News-letter" template:
     Times-like type, hyphenation + microtype, drop cap, thin column
     rule, ruled section heads, double-rule masthead.
  2. fpdf2 fallback — pure-Python, no system deps; plainer but always
     available. Used only when no LaTeX engine is on PATH.

The front page also carries PDF-only flourish that never enters the
markdown the merchants read: a woodcut plate at the head of the first
column, content-keyed to the edition (a stall-shuttered paper gets a
different plate than a quiet market morning) from the motif pool in
docs/assets/plates/ — ingested from raw art by setup/make_plates.py,
with docs/assets/images/bazaar-engraving.png as the static fallback —
plus three deterministic filler boxes at the foot of the page: the
weather & the market, PERSONALS classifieds, and "The Bazaar Whisper"
humour column.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_HEADLINE = {
    "morning": "The Bazaar Awakens",
    "evening": "Night Falls on the Bazaar",
}
COLOPHON = ("Printed by the arena press for the humans watching the "
            "merchants. The merchants themselves read the plain markdown "
            "\u2014 this page is pleasure, not game input.")
MOTTO = "All the facts fit to print \u2014 the rumours you may trade elsewhere."

# Non-game filler for the PDF-only humour column. Deterministically picked
# per edition (match, cycle, part) so every paper differs but a given paper
# always re-presses the same way.
WHISPER_ITEMS = [
    "The sparrow that lives in the mint-seller's awning has learned to say "
    "'best price in town'. The mint-seller denies teaching it.",
    "A camel was seen queueing at the fountain this morning. It had exact "
    "change and refused to explain itself.",
    "Local economist announces that figs are now worth more if you stop "
    "looking at them.",
    "The night watch reports that the moon has been 'keeping regular hours "
    "and setting a good example'. The moon declined to comment.",
    "Breaking: nothing happened in the alley behind the rope-maker's shop "
    "again today, for the ninth consecutive day.",
    "The fortune-teller's parrot has started giving refunds.",
    "A rug merchant was heard arguing with a rug. Witnesses say the rug "
    "was winning.",
    "Weather forecast: dust in the morning, dust in the afternoon, with "
    "scattered dust towards evening.",
    "The town's fastest gossip reports she is now hearing rumours before "
    "they happen. She calls this 'the early edition'.",
    "An anonymous benefactor has paid off the pigeon coop's debts. The "
    "pigeons remain ungrateful.",
    "Reminder from the editors: never buy a lantern at dusk, a date at "
    "midnight, or an opinion at any hour.",
    "The baker's apprentice has invented a bread that lasts forever. It "
    "tastes like it, too.",
    "Classified ad, unchanged for eleven years: 'WANTED: quieter cricket. "
    "Reward.'",
    "The tea house has introduced a new blend called 'The Long Pause'. "
    "It is served only after you have finished speaking.",
    "Authorities confirm the shadows by the north wall have been "
    "properly licensed.",
    "A travelling poet claims he can rhyme 'bazaar'. He has been asked "
    "to leave town twice.",
]


def whisper_column(meta):
    """Two deterministic non-game items for the foot of the front page."""
    part_no = 0 if meta["part"] == "morning" else 1
    try:
        seed = int(meta["match"]) * 31 + int(meta["cycle"]) * 7 + part_no
    except ValueError:
        seed = part_no
    first = seed % len(WHISPER_ITEMS)
    second = (seed + 3 + seed % 5) % len(WHISPER_ITEMS)
    if second == first:
        second = (first + 1) % len(WHISPER_ITEMS)
    return [WHISPER_ITEMS[first], WHISPER_ITEMS[second]]


# Woodcut plate at the head of the first column. The static plate below
# is the fallback; per-edition content-keyed motifs live in
# docs/assets/plates/ (ingested from raw art by setup/make_plates.py).
STATIC_PLATE = os.path.join(REPO_ROOT, "docs", "assets", "images",
                            "bazaar-engraving.png")
PLATES_DIR = os.path.join(REPO_ROOT, "docs", "assets", "plates")

# Content keys → plate filename, in priority order: game events first,
# then personas, then scenery. Missing motifs simply fall through to the
# next match; the chat.mistral prompt uses these exact filenames.
PLATE_RULES = [
    (re.compile(r"shutter|night kill|found dead", re.I),
     "shuttered-stall.png"),
    # NB: the "quiet nights in a row" stat line must NOT match — only the
    # event phrasing earns the moon.
    (re.compile(r"night passed quietly|quiet nights?(?!s?\s+in a row)"
                r"|without a (?:funeral|departure)", re.I), "moon-and-stars.png"),
    (re.compile(r"banish", re.I), "scales-of-judgement.png"),
    (re.compile(r"ballot|\bvot(?:e|es|ing|ed)\b", re.I), "ballot-urn.png"),
    (re.compile(r"banish", re.I), "tombstones-cypress.png"),
    (re.compile(r"graveyard|funeral|obituar", re.I), "tombstones-cypress.png"),
    (re.compile(r"carpet weaver|loom", re.I), "weavers-loom.png"),
    (re.compile(r"moneylender|ledger", re.I), "ledger-and-quill.png"),
    (re.compile(r"perfumer|scent", re.I), "perfume-bottles.png"),
    (re.compile(r"coppersmith|copper", re.I), "copper-pots.png"),
    (re.compile(r"potter|kiln", re.I), "potters-kiln.png"),
    (re.compile(r"tea seller|tea house|over tea", re.I), "tea-house-stove.png"),
    (re.compile(r"bird merchant|nightingale|birds say", re.I),
     "nightingales-birdcage.png"),
    (re.compile(r"rope", re.I), "rope-coils.png"),
    (re.compile(r"mint", re.I), "mint-bowl.png"),
    (re.compile(r"spice", re.I), "spice-sacks.png"),
    (re.compile(r"caravan|camel", re.I), "camel-caravan.png"),
    (re.compile(r"livestock|\bdonkeys?\b|\bgoats?\b|geese", re.I),
     "market-day-animals.png"),
    (re.compile(r"fountain", re.I), "fountain-with-camel.png"),
    (re.compile(r"lantern", re.I), "lantern-in-the-dark.png"),
    (re.compile(r"eclipse|sun darkened|strange sky", re.I), "solar-eclypse.png"),
    (re.compile(r"thiev|thief|stolen|pickpocket|cutpurse", re.I),
     "cutpurse-in-crowd.png"),
    (re.compile(r"fortune|fate|prophec|foretold", re.I), "fortune-teller.png"),
    (re.compile(r"counting|counted the", re.I), "moneylender-counting.png"),
    (re.compile(r"porter|basket", re.I), "porter-with-basket.png"),
    (re.compile(r"puppet|marionette|entertain", re.I), "puppeteer-show.png"),
    (re.compile(r"scribe|manuscript", re.I), "scribe-at-work.png"),
    (re.compile(r"weigh", re.I), "spice-merchant-weighing.png"),
    (re.compile(r"tea vendor|poured|served tea", re.I), "tea-vendor-serving.png"),
    (re.compile(r"water-carrier|thirsty|drought|\bwater\b", re.I),
     "water-carrier.png"),
    (re.compile(r"butcher|\bcow\b|meat", re.I), "cow-in-butchers-shop.png"),
    (re.compile(r"town square|crowd|gathered", re.I), "market-place-city.png"),
    (re.compile(r"clock|noon\b|hour", re.I), "old-stree-with-clock.png"),
    (re.compile(r"girl|child|apprentice", re.I), "girl-at-marked.png"),
    (re.compile(r"thriving|brisk (?:business|trade)|bustling", re.I),
     "thriving-marked-evening.png"),
    (re.compile(r"quiet evening|calm evening|peaceful evening", re.I),
     "quiet-evening-marked.png"),
    (re.compile(r"\bmarket|stalls", re.I), "market-street.png"),
    (re.compile(r"spice market|buyers", re.I),
     "spice-market-people-buying.png"),
    (re.compile(r"haggling|bargain", re.I), "merchants-haggling.png"),
]
PLATE_DEFAULTS = {
    "morning": "sunrise-over-domes.png",
    "evening": "sunset-over-stalls.png",
}


def plate_for_edition(md_text, part):
    """The plate this edition earns, chosen from its own text (PDF-only
    flourish — the markdown is unaffected). Deterministic: same edition,
    same plate. Falls back to the static engraving when nothing matches
    or the plates folder is empty."""
    candidates = [name for rx, name in PLATE_RULES if rx.search(md_text)]
    candidates.append(PLATE_DEFAULTS[part])
    for name in candidates:
        path = os.path.join(PLATES_DIR, name)
        if os.path.exists(path):
            return path
    return STATIC_PLATE


WEATHER_ITEMS = [
    "Hot at noon, hotter at dusk, with a light breeze of gossip from the "
    "north gate.",
    "Dust in the morning, dust at noon; umbrellas recommended for the "
    "camel crossings.",
    "Clear skies over the minarets; the pigeons report excellent flying.",
    "A chance of shade in the cloth district; elsewhere, relentless sun.",
    "Warm with scattered haggling; the evening promises a full moon and "
    "full purses.",
    "Breezy. The awnings are flapping and so are the merchants.",
    "Oppressive heat by the fountain, conspiratorial coolness in the "
    "alleys.",
    "Sunrise was at the usual time. The Herald checked twice.",
]

MARKET_ITEMS = [
    "Pepper: firm. Saffron: smug. Camel feed: suspiciously cheap.",
    "Rugs are up, figs are down, opinions remain at an all-time high.",
    "Lantern oil steady; candle wax nervous ahead of the night shift.",
    "Copper is trading at exactly what the Coppersmith says it is worth.",
    "Tea is up on rumors. The rumors are also up, mostly on tea.",
    "Perfume closed higher; nobody can say why, and everybody can smell it.",
    "Rope: knotty. Dates: pitted. Spices: spicy. Market report concludes.",
    "The moneylender's interest rates are unchanged, which is itself "
    "priceless.",
]


def weather_market(meta):
    """One deterministic weather line + one market line (PDF-only filler)."""
    part_no = 0 if meta["part"] == "morning" else 1
    try:
        seed = int(meta["match"]) * 37 + int(meta["cycle"]) * 11 + part_no
    except ValueError:
        seed = part_no
    return (WEATHER_ITEMS[seed % len(WEATHER_ITEMS)],
            MARKET_ITEMS[(seed + 1) % len(MARKET_ITEMS)])


PERSONALS_ITEMS = [
    "LOST: one brass key, opens nothing the owner will admit. Reward and "
    "questions at the fountain.",
    "WANTED: apprentice for the lantern stall. Must not fear the dark or "
    "its customers.",
    "FOR SALE: slightly singed rug, story included at no extra cost.",
    "SEEKING WORK: scribe, discreet, remembers nothing by morning.",
    "FOUND: a goat with excellent manners. Claim at the spice gate before "
    "it claims you.",
    "NOTICE: the perfumer's 'Eau de Alibi' is sold out again.",
    "WANTED: witnesses to nothing in particular. Apply at the Herald.",
    "FOR SALE: telescope, sees only what you expect. Slightly bent.",
    "LOST: a nightingale that sings only rumours. Answers to no one.",
    "WANTED: porter for the night shift. Applicants must have a night.",
    "MATRIMONIAL: merchant seeks someone who counts higher than three.",
    "LOST: camel, answers to no name. Finder may keep the grudge.",
    "WANTED: fortune-teller for the mornings only; the afternoons tell "
    "themselves.",
    "NOTICE: someone keeps leaving mint on the moneylender's doorstep.",
]


def personals_column(meta):
    """Two deterministic classifieds for the PDF-only foot (invented
    flavour — like the Whisper, never game input)."""
    part_no = 0 if meta["part"] == "morning" else 1
    try:
        seed = int(meta["match"]) * 41 + int(meta["cycle"]) * 13 + part_no
    except ValueError:
        seed = part_no
    first = seed % len(PERSONALS_ITEMS)
    second = (first + 5 + seed % 4) % len(PERSONALS_ITEMS)
    if second == first:
        second = (first + 1) % len(PERSONALS_ITEMS)
    return [PERSONALS_ITEMS[first], PERSONALS_ITEMS[second]]


# ------------------------------------------------------------- parsing ----
def sanitize(text):
    """Keep typographic quotes/dashes that LaTeX likes; drop the rest."""
    return (text.replace("\u2019", "'").replace("\u201c", "``")
                .replace("\u201d", "''"))


def parse_edition(md_text, md_path):
    """Split an edition into masthead metadata and printable blocks."""
    name = os.path.basename(md_path)
    m = re.match(r"herald-c(\d+)-(morning|evening)\.md", name)
    if m:
        cycle, part = m.group(1), m.group(2)
    else:               # e.g. the docs sample: herald-sample-evening.md
        part = "evening" if "evening" in name else "morning"
        dm = re.search(r"Cycle\s+(\d+)", md_text)
        cycle = dm.group(1) if dm else "000"

    match_no = 1
    mm = re.search(r"\*Match\s+(\d+)", md_text)
    if mm:
        match_no = mm.group(1)

    headline, blocks = None, []
    in_code, code_lines = False, []
    for line in md_text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            if in_code:                   # end of a fenced block
                text = "\n".join(code_lines)
                kind = ("chart" if "\u2593" in text or "\u2588" in text
                        else "code")
                blocks.append((kind, text))
                in_code, code_lines = False, []
            else:
                in_code, code_lines = True, []
            continue
        if in_code:
            code_lines.append(s)
            continue
        if not s:
            continue
        if s.startswith("# "):            # edition title — masthead covers it
            continue
        if s.startswith("## "):
            text = sanitize(s[3:].strip().strip("*"))
            if headline is None:          # first section heading = headline
                headline = text
            else:
                blocks.append(("subhead", text))
        elif re.fullmatch(r"\*[^*]+\*", s):   # *Match 1, Cycle 001* → dateline
            continue
        elif s.startswith("- "):
            blocks.append(("para", "\u2022 " + sanitize(s[2:])))
        else:
            blocks.append(("para", sanitize(s.strip())))
    return {
        "match": match_no,
        "cycle": cycle,
        "part": part,
        "headline": headline or DEFAULT_HEADLINE[part],
        "blocks": blocks,
        "plate": plate_for_edition(md_text, part),
    }


# ---------------------------------------------------------------- latex ----
def parse_chart_rows(text):
    """A tally chart block → (header lines, [(label, count), …]).
    ASCII separator rules are dropped — the engines draw their own."""
    header, bars = [], []
    for line in text.splitlines():
        m = re.match(r"^(.*?)\s+[\u2593\u2588]+\s*(\d+)\s*$", line)
        if m:
            bars.append((m.group(1).strip(), int(m.group(2))))
        elif line and set(line) <= {"-"}:
            continue
        else:
            header.append(line)
    return header, bars


def latex_escape(text):
    return (text.replace("\\", r"\textbackslash{}")
                .replace("&", r"\&").replace("%", r"\%")
                .replace("#", r"\#").replace("_", r"\_")
                .replace("{", r"\{").replace("}", r"\}")
                .replace("~", r"\textasciitilde{}")
                .replace("^", r"\textasciicircum{}"))


def latex_inline(text):
    """Light markdown → LaTeX: **bold**, *italic*."""
    text = latex_escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*(.+?)\*", r"\\emph{\1}", text)
    return text


def chart_tex(text):
    """The tally chart as an old-style election-returns graphic: ruled
    frame, small-caps caption, solid black bars on a common baseline."""
    header, bars = parse_chart_rows(text)
    top = max((n for _, n in bars), default=1)
    rows = []
    for label, n in bars:
        w = max(0.9, 4.5 * n / top)
        rows.append("%s & \\rule{%.2fem}{1.2ex} & %s \\\\" %
                    (latex_escape(sanitize(label)), w, n))
    head = [latex_escape(sanitize(l)) for l in header]
    tex = ["\\begin{center}",
           "\\hrule height .6pt\\vspace{5pt}"]
    if head:
        tex.append("{\\footnotesize\\scshape\\textbf{%s}}\\\\" % head[0])
        for extra in head[1:]:
            tex.append("\\textit{\\footnotesize %s}\\\\[2pt]" % extra)
    tex.append("\\vspace{3pt}")
    tex.append("\\begin{tabular}{@{}l@{\\hspace{8pt}}l@{\\hspace{8pt}}r@{}}")
    tex += rows
    tex.append("\\end{tabular}")
    tex.append("\\vspace{4pt}\\hrule height .6pt")
    tex.append("\\end{center}\n")
    return "\n".join(tex)


def build_tex(meta, date_str, size, linespread):
    """A one-page newspaper front page, Overleaf-template style."""
    body, first_para_done = [], False
    for kind, text in meta["blocks"]:
        if kind == "subhead":
            body.append(r"\section*{%s}" % latex_escape(text))
        elif kind == "chart":
            body.append(chart_tex(text))
        elif kind == "code":
            body.append("\\begin{quote}\\small\\ttfamily\\obeylines\n"
                        + latex_escape(text) + "\n\\end{quote}")
        else:
            if not first_para_done:          # drop cap on the opening paragraph
                words = text.split()
                if len(words) >= 2:
                    body.append(
                        r"\lettrine[lines=2,findent=2pt,nindent=0pt]{%s}{%s}%s "
                        % (latex_escape(words[0][0]),
                           latex_escape(words[0][1:]),
                           latex_inline(" ".join(words[1:]))))
                else:
                    body.append(latex_inline(text))
                first_para_done = True
            else:
                body.append(latex_inline(text))
        body.append("\n")

    # "The Weather & The Market" and "The Bazaar Whisper" — PDF-only filler
    # boxes, ruled off at the foot of the page after the news columns.
    # Never enters the markdown the merchants read.
    weather, market = weather_market(meta)
    whisper_items = whisper_column(meta) if meta["blocks"] else []
    foot = ""
    if whisper_items:
        personals = personals_column(meta)
        foot = (
            "\\vspace{4pt}\\hrule height .5pt\n"
            "{\\footnotesize\\bfseries\\itshape THE WEATHER "
            "\\& THE MARKET\\par}\n"
            "\\vspace{2pt}{\\footnotesize\\itshape %s\\par}\n"
            "\\vspace{2pt}{\\footnotesize\\itshape %s\\par}\n"
            "\\vspace{4pt}\\hrule height .5pt\n"
            "{\\footnotesize\\bfseries\\itshape PERSONALS\\par}\n"
            "\\vspace{2pt}{\\footnotesize\\itshape %s\\par}\n"
            "\\vspace{2pt}{\\footnotesize\\itshape %s\\par}\n"
            "\\vspace{4pt}\\hrule height .5pt\n"
            "{\\footnotesize\\bfseries\\itshape THE BAZAAR WHISPER\\par}\n"
            "\\vspace{2pt}\n"
            % (latex_escape(sanitize(weather)),
               latex_escape(sanitize(market)),
               latex_escape(sanitize(personals[0])),
               latex_escape(sanitize(personals[1]))) +
            "\n\\vspace{2pt}\n".join(
                "{\\footnotesize\\itshape %s\\par}" % latex_escape(sanitize(i))
                for i in whisper_items))

    # Woodcut plate: a column-width illustration at the TOP of the FIRST
    # (left) column, above the drop cap — content-keyed per edition
    # (best-effort; a missing plate never breaks a paper).
    plate = meta.get("plate")
    if meta["blocks"] and plate and os.path.exists(plate):
        body.insert(0, "\\includegraphics[width=\\linewidth]{%s}\n"
                      "\\vspace{3pt}\n"
                      % latex_escape(plate.replace(os.sep, "/")))

    return r"""\documentclass[{size}pt]{{extarticle}}
\usepackage[a4paper,left=14mm,right=14mm,top=13mm,bottom=16mm]{{geometry}}
\usepackage{{newtxtext}}
\usepackage{{microtype}}
\usepackage{{multicol}}
\usepackage{{titlesec}}
\usepackage{{lettrine}}
\usepackage{{graphicx}}
\linespread{{{linespread}}}

\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{3pt}}
\setlength{{\columnsep}}{{7mm}}
\setlength{{\columnseprule}}{{0.3pt}}

% section heads: ruled, bold, centred — the newspaper look
\titleformat{{\section}}[block]
  {{\normalsize\bfseries\centering\MakeUppercase}}{{}}{{0pt}}{{}}
  [{{\vspace{{1pt}}\titlerule[0.5pt]}}]
\titlespacing*{{\section}}{{0pt}}{{9pt}}{{5pt}}

\newcommand{{\doubleRule}}{{%
  \par\nointerlineskip\vspace{{3pt}}\hrule height .9pt
  \vspace{{2.5pt}}\hrule height .3pt\vspace{{5pt}}}}

\begin{{document}}
\thispagestyle{{empty}}

% ---- masthead ------------------------------------------------------------
\begin{{center}}
{{\fontsize{{33}}{{37}}\selectfont\bfseries THE BAZAAR HERALD\par}}
\doubleRule
{{\small\itshape Vol. {match} --- No. {cycle} \quad|\quad {edition} Edition
  \quad|\quad {date} \quad|\quad Price: one spiced date\par}}
\vspace{{1pt}}
{{\footnotesize\itshape {motto}\par}}
\vspace{{2pt}}\hrule height .3pt
\end{{center}}

% ---- headline ------------------------------------------------------------
\begin{{center}}
{{\fontsize{{19}}{{23}}\selectfont\bfseries {headline}\par}}
\end{{center}}
\vspace{{2pt}}
\begin{{multicols}}{{2}}
{body}
\end{{multicols}}

% ---- PDF-only filler: weather, market, The Bazaar Whisper ----------------
{foot}

% ---- colophon ------------------------------------------------------------
\vfill
\begin{{center}}
\rule{{0.35\linewidth}}{{0.3pt}}\\[3pt]
{{\footnotesize\itshape {colophon}}}
\end{{center}}
\end{{document}}
""".format(size=size, linespread=linespread,
           match=latex_escape(meta["match"]), cycle=latex_escape(meta["cycle"]),
           edition=latex_escape(meta["part"].capitalize()),
           date=latex_escape(date_str),
           headline=latex_escape(meta["headline"]),
           body="".join(body), foot=foot,
           motto=latex_escape(sanitize(MOTTO)),
           colophon=latex_escape(sanitize(COLOPHON)))


def find_engine():
    for exe in ("tectonic", "pdflatex"):
        if shutil.which(exe):
            return exe
    return None


def run_engine(engine, tex_path, outdir, timeout=180):
    if engine == "tectonic":
        cmd = [engine, "-o", outdir, tex_path]
    else:
        cmd = [engine, "-interaction=nonstopmode",
               "-output-directory", outdir, tex_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(tex_path))[0]
                       + ".pdf")
    if r.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError(f"{engine} failed:\n{r.stdout[-500:]}\n{r.stderr[-300:]}")
    return pdf


def count_pages(pdf_path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return 1     # cannot count — assume it fit


def compile_latex(meta, date_str, out_path):
    """Ladder down in type size until the edition fits one A4 page.
    If nothing fits (an overlong edition), print the smallest one anyway —
    two pages beat no paper."""
    engine = find_engine()
    ladder = [(10, 1.06), (9, 1.06), (9, 1.0), (8, 1.0), (8, 0.94)]
    last_bytes = None
    for size, spread in ladder:
        tex = build_tex(meta, date_str, size, spread)
        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "herald.tex")
            with open(tex_path, "w") as f:
                f.write(tex)
            try:
                pdf = run_engine(engine, tex_path, tmp)
            except Exception:
                continue
            if count_pages(pdf) <= 1:
                shutil.move(pdf, out_path)
                return out_path, 1
            if last_bytes is None:      # keep the biggest type as the fallback
                with open(pdf, "rb") as f:
                    last_bytes = f.read()
    if last_bytes is None:
        raise RuntimeError(f"{engine} could not compile the edition")
    with open(out_path, "wb") as f:
        f.write(last_bytes)
    return out_path, count_pages(out_path)


# --------------------------------------------------------------- fpdf2 ----
PAGE_W, PAGE_H = 210.0, 297.0          # A4, mm
MARGIN = 15.0
GUTTER = 6.0
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2.0
BODY_TOP = 62.0
BODY_BOTTOM = PAGE_H - 18.0
LEAD = 0.46


def fpdf_sanitize(text):
    return (text.replace("\u2019", "'").replace("\u201c", '"')
                .replace("\u201d", '"')
                .encode("cp1252", errors="replace").decode("cp1252"))


def _wrap_lines(pdf, w, text):
    lines, current = 0, ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if pdf.get_string_width(trial) <= w or not current:
            current = trial
        else:
            lines += 1
            current = word
    return lines + (1 if current else 0)


def render_fpdf(meta, date_str, size):
    """The fpdf2 fallback: plainer, but dependency-free."""
    from fpdf import FPDF

    class Paper(FPDF):
        def footer(self):
            pass

    pdf = Paper("P", "mm", "A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_margins(MARGIN, 15, MARGIN)

    pdf.set_font("Times", "B", 40)
    pdf.cell(0, 16, "The Bazaar Herald", align="C")
    pdf.set_y(pdf.get_y() + 1)
    pdf.set_line_width(0.8)
    pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
    pdf.set_line_width(0.25)
    pdf.line(MARGIN, pdf.get_y() + 1.2, PAGE_W - MARGIN, pdf.get_y() + 1.2)
    pdf.set_y(pdf.get_y() + 2.0)

    pdf.set_font("Times", "I", 9.5)
    dateline = (f"Vol. {meta['match']} \u2014 No. {meta['cycle']}"
                f"   |   {meta['part'].capitalize()} Edition"
                f"   |   {date_str}   |   Price: one spiced date")
    pdf.cell(0, 5, fpdf_sanitize(dateline), align="C")
    pdf.line(MARGIN, pdf.get_y() + 1.2, PAGE_W - MARGIN, pdf.get_y() + 1.2)

    pdf.set_y(pdf.get_y() + 1.8)
    pdf.set_font("Times", "I", 8)
    pdf.cell(0, 3.5, fpdf_sanitize(MOTTO), align="C")

    pdf.set_y(pdf.get_y() + 3.5)
    pdf.set_font("Times", "B", 22)
    pdf.multi_cell(0, 10, fpdf_sanitize(meta["headline"]), align="C")
    pdf.set_y(pdf.get_y() + 1.0)

    # woodcut plate at the top of the FIRST (left) column — content-keyed
    engr_h = 0.0
    plate = meta.get("plate")
    if meta["blocks"] and plate and os.path.exists(plate):
        from PIL import Image
        with Image.open(plate) as im:
            ew, eh = im.size
        try:
            pdf.image(plate, x=MARGIN, y=BODY_TOP, w=COL_W)
            engr_h = COL_W * eh / ew + 3.0
        except Exception:
            engr_h = 0.0          # a bad plate must never stop the paper

    leading = size * LEAD
    col_x = [MARGIN, MARGIN + COL_W + GUTTER]

    # PDF-only filler boxes above the colophon: weather & market, Whisper.
    full_w = PAGE_W - 2 * MARGIN
    pdf.set_font("Times", "I", 8.5)
    foot_h = 0.0
    foot_rows = []
    if meta["blocks"]:
        weather, market = weather_market(meta)
        foot_rows = [("B", "The Weather & The Market"),
                     ("I", weather), ("I", market), ("S", ""),
                     ("B", "Personals"),
                     ("I", personals_column(meta)[0]),
                     ("I", personals_column(meta)[1]), ("S", ""),
                     ("B", "The Bazaar Whisper")]
        foot_rows += [("I", i) for i in whisper_column(meta)]
        for kind, text in foot_rows:
            if kind == "S":
                foot_h += 2.0
            elif kind == "B":
                foot_h += 6.0
            else:
                foot_h += _wrap_lines(pdf, full_w, text) * 4.0 + 2.0

    col_top = [BODY_TOP + engr_h, BODY_TOP]   # left column starts under the plate
    body_bottom = BODY_BOTTOM - foot_h

    col, y = 0, col_top[0]
    for kind, text in meta["blocks"]:
        if kind == "chart":
            header, bars = parse_chart_rows(text)
            block_h = (6.0 + len(header) * 4.0 + len(bars) * 5.0 + 6.0)
        elif kind == "code":
            block_h = len(text.splitlines()) * 4.0 + 4.0
        else:
            pdf.set_font("Times", "B" if kind == "subhead" else "", size)
            block_h = (_wrap_lines(pdf, COL_W, text) * leading
                       + (3.0 if kind == "subhead" else 1.6))
        if y + block_h > body_bottom:
            if col == 0:
                col, y = 1, col_top[1]
            else:
                return pdf, False
        pdf.set_xy(col_x[col], y)
        if kind == "chart":
            top_n = max((n for _, n in bars), default=1)
            pdf.set_line_width(0.4)
            pdf.line(col_x[col], y + 0.8, col_x[col] + COL_W, y + 0.8)
            pdf.set_line_width(0.25)
            cy = y + 2.0
            pdf.set_font("Times", "BI", size)
            for hl in header:
                pdf.set_xy(col_x[col], cy)
                pdf.cell(COL_W, 4, fpdf_sanitize(hl), align="C")
                cy += 4.0
            cy += 1.0
            for label, n in bars:
                pdf.set_xy(col_x[col], cy)
                pdf.set_font("Times", "", size)
                pdf.cell(27, 4, fpdf_sanitize(label), align="L")
                bw = max(3.0, (COL_W - 27 - 9) * n / top_n)
                pdf.set_fill_color(20, 20, 20)
                pdf.rect(col_x[col] + 28, cy + 0.9, bw, 2.6, style="F")
                pdf.set_xy(col_x[col] + COL_W - 8, cy)
                pdf.cell(8, 4, str(n), align="R")
                cy += 5.0
            pdf.line(col_x[col], cy + 1.0, col_x[col] + COL_W, cy + 1.0)
            y = cy + 4.0
        elif kind == "code":
            pdf.set_font("Courier", "", size - 1)
            pdf.multi_cell(COL_W, 4, fpdf_sanitize(text), align="L")
            y = pdf.get_y() + 1.2
        elif kind == "subhead":
            pdf.set_font("Times", "B", size + 1)
            pdf.multi_cell(COL_W, leading, text.upper(), align="L")
            y = pdf.get_y() + 1.8
        else:
            pdf.multi_cell(COL_W, leading, text, align="J")
            y = pdf.get_y() + 1.2

    pdf.set_auto_page_break(False)
    if foot_rows:
        fy = BODY_BOTTOM - foot_h + 2.0
        pdf.set_line_width(0.25)
        pdf.line(MARGIN, fy - 2.0, PAGE_W - MARGIN, fy - 2.0)
        for kind, text in foot_rows:
            if kind == "S":
                pdf.set_y(pdf.get_y() + 2.0)
                continue
            pdf.set_xy(MARGIN, pdf.get_y() + (1.0 if kind == "I" else 0.5))
            pdf.set_font("Times", "BI" if kind == "B" else "I", 9 if kind == "B" else 8.5)
            if kind == "B":
                pdf.cell(0, 4, text, align="C")
                pdf.set_y(pdf.get_y() + 4)
            else:
                pdf.multi_cell(0, 4, fpdf_sanitize(text), align="C")
    pdf.line(MARGIN, BODY_BOTTOM + 2.5, PAGE_W - MARGIN, BODY_BOTTOM + 2.5)
    pdf.set_font("Times", "I", 8.5)
    pdf.set_xy(MARGIN, BODY_BOTTOM + 3.5)
    pdf.multi_cell(0, 4, fpdf_sanitize(COLOPHON), align="C")
    return pdf, True


def compile_fpdf(meta, date_str, out_path):
    for size in (10.0, 9.5, 9.0, 8.5, 8.0, 7.5):
        pdf, fits = render_fpdf(meta, date_str, size)
        if fits:
            pdf.output(out_path)
            return out_path
    raise RuntimeError("edition does not fit on one A4 page (fpdf2)")


# --------------------------------------------------------------- entry ----
def compile_edition(md_path, out_path=None, quiet=False):
    """Compile one edition markdown into its one-page A4 PDF twin.
    Prefers LaTeX (tectonic/pdflatex); falls back to fpdf2."""
    with open(md_path) as f:
        meta = parse_edition(f.read(), md_path)
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    out_path = out_path or os.path.splitext(md_path)[0] + ".pdf"

    engine = find_engine()
    if engine:
        try:
            out_path, pages = compile_latex(meta, date_str, out_path)
            if not quiet:
                note = "" if pages == 1 else f" ({pages} pages — a long edition)"
                print(f"==> pressed {out_path} (LaTeX/{engine}){note}")
            return out_path
        except Exception as e:
            if not quiet:
                print(f"==> LaTeX press failed, using fpdf2 fallback: {e}")
    else:
        if not quiet:
            print("==> no LaTeX engine (install tectonic for the fine "
                  "edition); using fpdf2 fallback")
    compile_fpdf(meta, date_str, out_path)
    if not quiet:
        print(f"==> pressed {out_path} (fpdf2 fallback)")
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Bazaar of Lies — compile a Herald edition to a "
                    "one-page A4 newspaper-front-page PDF.")
    ap.add_argument("edition", help="Path to herald-cXXX-{morning,evening}.md")
    ap.add_argument("-o", "--output", default=None,
                    help="Output PDF path (default: same stem, .pdf)")
    args = ap.parse_args()

    compile_edition(args.edition if os.path.isabs(args.edition)
                    else os.path.join(REPO_ROOT, args.edition),
                    os.path.join(REPO_ROOT, args.output)
                    if args.output and not os.path.isabs(args.output)
                    else args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
