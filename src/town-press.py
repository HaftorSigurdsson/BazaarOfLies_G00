#!/usr/bin/env python3
"""Bazaar of Lies — the press (town-press.py).

Compiles a Herald edition (markdown) into a ONE-PAGE A4 PDF styled as
the front page of an old newspaper, for the humans watching the arena.
The merchants themselves read the plain markdown — the PDF is pleasure,
not game input.

    uv run src/town-press.py gameplay/news/herald-c001-morning.md

The Herald calls compile_edition() automatically after printing an
edition, so every gameplay/news/herald-cXXX-{morning,evening}.md gets a
.pdf twin committed next to it.

Layout (A4 portrait, Times):
    masthead  THE BAZAAR HERALD, double rules
    dateline  Vol/No | edition | date | price
    headline  from the edition's first heading (or a default per edition)
    body      two justified columns; auto-shrinks until it fits one page
    footer    rule + colophon

FUTURE (deliberately not built yet, hooks in place):
    - a woodcut-style engraving between headline and columns
      (reserve ~30mm with pdf.image(...) when artwork exists);
    - "The Bazaar Whisper": a narrow third column of non-game humour,
      routed from a `## Bazaar Whisper` section of the markdown.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone

from fpdf import FPDF

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGE_W, PAGE_H = 210.0, 297.0          # A4, mm
MARGIN = 15.0                          # left/right
GUTTER = 6.0
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2.0
BODY_TOP = 62.0                        # first baseline area under dateline
BODY_BOTTOM = PAGE_H - 18.0            # above the footer
LEAD = 0.46                            # leading as a fraction of font size

DEFAULT_HEADLINE = {
    "morning": "The Bazaar Awakens",
    "evening": "Night Falls on the Bazaar",
}


def sanitize(text):
    """Core fonts speak cp1252 — keep everything else from exploding."""
    return (text.replace("\u2019", "'").replace("\u201c", '"')
                .replace("\u201d", '"')
                .encode("cp1252", errors="replace").decode("cp1252"))


def parse_edition(md_text, md_path):
    """Split an edition into masthead metadata and printable blocks."""
    name = os.path.basename(md_path)
    m = re.match(r"herald-c(\d+)-(morning|evening)\.md", name)
    cycle, part = (m.group(1), m.group(2)) if m else ("000", "morning")

    match_no = 1
    mm = re.search(r"\*Match\s+(\d+)", md_text)
    if mm:
        match_no = mm.group(1)

    headline, blocks = None, []
    for line in md_text.splitlines():
        s = line.strip()
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
    }


class Paper(FPDF):
    def footer(self):  # auto page break footer only (overflow pages)
        pass


def _wrap_lines(pdf, w, text):
    """Number of text lines a justified block needs at the current font."""
    lines, current = 0, ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if pdf.get_string_width(trial) <= w or not current:
            current = trial
        else:
            lines += 1
            current = word
    return lines + (1 if current else 0)


def render(meta, date_str, size):
    """Render one candidate layout. Returns the FPDF and whether it fit
    on a single page."""
    pdf = Paper("P", "mm", "A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_margins(MARGIN, 15, MARGIN)

    # ---- masthead ----------------------------------------------------
    pdf.set_font("Times", "B", 40)
    pdf.cell(0, 16, "The Bazaar Herald", align="C")
    pdf.set_y(pdf.get_y() + 1)
    pdf.set_line_width(0.8)
    pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
    pdf.set_line_width(0.25)
    pdf.line(MARGIN, pdf.get_y() + 1.2, PAGE_W - MARGIN, pdf.get_y() + 1.2)
    pdf.set_y(pdf.get_y() + 2.0)

    # ---- dateline bar -------------------------------------------------
    pdf.set_font("Times", "I", 9.5)
    dateline = (f"Vol. {meta['match']} \u2014 No. {meta['cycle']}"
                f"   |   {meta['part'].capitalize()} Edition"
                f"   |   {date_str}   |   Price: one spiced date")
    pdf.cell(0, 5, sanitize(dateline), align="C")
    pdf.set_line_width(0.25)
    pdf.line(MARGIN, pdf.get_y() + 1.2, PAGE_W - MARGIN, pdf.get_y() + 1.2)

    # ---- headline ------------------------------------------------------
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font("Times", "B", 22)
    pdf.multi_cell(0, 10, meta["headline"], align="C")
    pdf.set_y(pdf.get_y() + 1.5)

    # FUTURE: woodcut engraving here — pdf.image(...), ~30mm tall.

    # ---- body: two justified columns ------------------------------------
    leading = size * LEAD
    col_x = [MARGIN, MARGIN + COL_W + GUTTER]
    col, y = 0, BODY_TOP

    for kind, text in meta["blocks"]:
        pdf.set_font("Times", "B" if kind == "subhead" else "", size)
        w = COL_W
        n_lines = _wrap_lines(pdf, w, text)
        block_h = n_lines * leading + (3.0 if kind == "subhead" else 1.6)
        if y + block_h > BODY_BOTTOM:
            if col == 0:
                col, y = 1, BODY_TOP
            else:                        # ran past column two → page two
                return pdf, False
        pdf.set_xy(col_x[col], y)
        if kind == "subhead":
            pdf.set_font("Times", "B", size + 1)
            pdf.multi_cell(w, leading, text.upper(), align="L")
        else:
            pdf.multi_cell(w, leading, text, align="J")
        y = pdf.get_y() + (1.8 if kind == "subhead" else 1.2)

    # ---- footer ---------------------------------------------------------
    pdf.set_auto_page_break(False)   # colophon lives in the bottom margin
    pdf.set_line_width(0.25)
    pdf.line(MARGIN, BODY_BOTTOM + 2.5, PAGE_W - MARGIN, BODY_BOTTOM + 2.5)
    pdf.set_font("Times", "I", 8.5)
    pdf.set_xy(MARGIN, BODY_BOTTOM + 3.5)
    pdf.multi_cell(0, 4,
                   sanitize("Printed by the arena press for the humans watching the "
                            "merchants. The merchants themselves read the plain "
                            "markdown \u2014 this page is pleasure, not game input."),
                   align="C")
    # FUTURE: "The Bazaar Whisper" humour column (third narrow column).

    return pdf, True


def compile_edition(md_path, out_path=None):
    """Compile one edition markdown into its one-page A4 PDF twin."""
    with open(md_path) as f:
        meta = parse_edition(f.read(), md_path)
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    out_path = out_path or os.path.splitext(md_path)[0] + ".pdf"

    for size in (10.0, 9.5, 9.0, 8.5, 8.0, 7.5):   # auto-fit: one page or bust
        pdf, fits = render(meta, date_str, size)
        if fits:
            pdf.output(out_path)
            return out_path
    raise RuntimeError("edition does not fit on one A4 page")


def main():
    ap = argparse.ArgumentParser(
        description="Bazaar of Lies — compile a Herald edition to a "
                    "one-page A4 newspaper-front-page PDF.")
    ap.add_argument("edition", help="Path to herald-cXXX-{morning,evening}.md")
    ap.add_argument("-o", "--output", default=None,
                    help="Output PDF path (default: same stem, .pdf)")
    args = ap.parse_args()

    out = compile_edition(os.path.join(REPO_ROOT, args.edition)
                          if not os.path.isabs(args.edition) else args.edition,
                          os.path.join(REPO_ROOT, args.output)
                          if args.output and not os.path.isabs(args.output)
                          else args.output)
    print(f"==> pressed {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
