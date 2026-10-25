#!/usr/bin/env python3
"""Bazaar of Lies — the elder press (elder-press.py).

Renders an Elder Council judgment (markdown) into a multi-page PDF in
the register of a court document: serif, ruled sections, a centered
caption block — the dignified sibling of the Herald's one-page paper.

    uv run src/elder-press.py gameplay/village/match-01-judgment.md

Markdown handled: # title, ## sections, ### subsections, **bold**,
*italic*, > quotes, - bullets, --- rules, plain paragraphs. Everything
else passes as prose. The PDF lands next to the markdown.
"""
import os
import re
import subprocess
import sys
import tempfile

PACKAGES = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=2.4cm]{geometry}
\usepackage{parskip}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{fancyhdr}
"""


def header_setup(full_title):
    """Running header (the full heading, small italics, under a rule) and
    centered page numbers in the footer, on every page of the body."""
    return (PACKAGES
            + r"\pagestyle{fancy}" + "\n"
            + r"\fancyhf{}" + "\n"
            + r"\fancyhead[L]{\small\itshape "
            + latex_escape(full_title) + "}" + "\n"
            + r"\fancyhead[R]{}" + "\n"
            + r"\fancyfoot[C]{\thepage}" + "\n"
            + r"\renewcommand{\headrulewidth}{0.4pt}" + "\n"
            + r"\setlength{\headheight}{14pt}" + "\n"
            + r"\begin{document}" + "\n")

POSTAMBLE = "\n\\end{document}\n"


def latex_escape(text):
    return (text.replace("\\", r"\textbackslash{}")
                .replace("&", r"\&").replace("%", r"\%")
                .replace("#", r"\#").replace("_", r"\_")
                .replace("{", r"\{").replace("}", r"\}")
                .replace("~", r"\textasciitilde{}")
                .replace("^", r"\textasciicircum{}"))


def latex_inline(text):
    text = latex_escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*(.+?)\*", r"\\emph{\1}", text)
    return text



PLATES_DIR = os.path.abspath("docs/assets/plates")
ENGRAVING = os.path.abspath("docs/assets/images/bazaar-engraving.png")


def front_page(md):
    """A formal title page in the spirit of a historical legal document:
    the arena's seal (the engraving, a quarter of the width), the case
    name, the dateline — and one small plate chosen at random from the
    arena's own collection as an ornament."""
    lines = [l.strip() for l in md.splitlines() if l.strip()]
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    case = title.split(" — ", 1)[-1] if " — " in title else title
    dateline = ""
    for i, l in enumerate(lines):
        if l.startswith("# "):
            for cand in lines[i + 1:i + 3]:
                if not cand.startswith("#"):
                    dateline = cand.strip("*").strip()
                    break
            break
    import random
    plates = sorted(f for f in os.listdir(PLATES_DIR) if f.endswith(".png"))
    ornament = os.path.join(PLATES_DIR, random.choice(plates)) if plates else ""
    tex = [r"\begin{titlepage}", r"\centering",
           r"{\scshape\small THE BAZAAR OF LIES \par}",
           r"{\scshape\small THE ARENA RECORD \par}",
           r"\vspace{0.5cm}\rule{0.5\textwidth}{0.5pt}\vspace{0.9cm}",
           rf"\includegraphics[width=0.25\textwidth]{{{ENGRAVING}}}",
           r"\vspace{1.1cm}",
           r"{\Large\scshape In the Matter of\par}",
           r"\vspace{0.3cm}",
           rf"{{\LARGE\itshape {latex_escape(case)}\par}}",
           r"\vspace{0.45cm}",
           r"{\large The Judgment of the Council of Elders\par}"]
    if dateline:
        tex += [r"\vspace{0.55cm}",
                rf"{{\itshape {latex_inline(dateline)}\par}}"]
    tex += [r"\vfill"]
    if ornament:
        tex += [rf"\includegraphics[width=0.16\textwidth]{{{ornament}}}",
                r"\vspace{0.4cm}"]
    tex += [r"{\small\itshape The bazaar rests.\par}",
            r"\end{titlepage}", ""]
    return "\n\n".join(tex)


def _table_tex(rows):
    """Markdown table rows -> a ruled LaTeX tabular (left-aligned)."""
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    body = []
    for r in rows[2:]:                      # skip the --- separator
        body.append([c.strip() for c in r.strip("|").split("|")])
    cols = "l" * len(header)
    out = [r"\begin{center}\begin{tabular}{" + cols + "}",
           r"\hline",
           " & ".join(latex_inline(c) for c in header) + r" \\",
           r"\hline"]
    for row in body:
        cells = row + [""] * (len(header) - len(row))
        out.append(" & ".join(latex_inline(c) for c in cells[:len(header)])
                   + r" \\")
    out += [r"\hline", r"\end{tabular}\end{center}"]
    return "\n".join(out)


def md_to_tex(md):
    out, in_quote, in_item = [], False, False
    table = []
    first_title = True
    for raw in md.splitlines():
        s = raw.strip()
        if s.startswith("|"):
            table.append(s)
            continue
        if table:
            out.append(_table_tex(table))
            table = []
        if in_quote and not s.startswith(">"):
            out.append(r"\end{quote}")
            in_quote = False
        if in_item and not s.startswith("- "):
            out.append(r"\end{itemize}")
            in_item = False
        if not s:
            continue
        if s.startswith("# "):                      # the front page owns it
            if first_title:
                first_title = False
                continue
            out.append(r"\begin{center}{\Large\bfseries "
                       + latex_inline(s[2:]) + r"}\end{center}")
            out.append(r"\begin{center}\rule{0.6\textwidth}{0.5pt}\end{center}")
        elif s.startswith("## "):
            out.append(r"\section*{" + latex_inline(s[3:]) + "}")
        elif s.startswith("### "):
            out.append(r"\subsection*{" + latex_inline(s[4:]) + "}")
        elif s.startswith(">"):
            if not in_quote:
                out.append(r"\begin{quote}")
                in_quote = True
            out.append(latex_inline(s.lstrip("> ").strip()) + r" \\[2pt]")
        elif s.startswith("- "):
            if not in_item:
                out.append(r"\begin{itemize}")
                in_item = True
            out.append(r"\item " + latex_inline(s[2:]))
        elif set(s) <= {"-"}:                        # a --- rule
            out.append(r"\noindent\rule{\textwidth}{0.4pt}")
        else:
            out.append(latex_inline(s))
    if table:
        out.append(_table_tex(table))
    if in_quote:
        out.append(r"\end{quote}")
    if in_item:
        out.append(r"\end{itemize}")
    return "\n\n".join(out) + "\n"


def compile_judgment(md_path):
    with open(md_path) as f:
        md = f.read()
    lines = [l.strip() for l in md.splitlines() if l.strip()]
    full_title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    tex = (header_setup(full_title) + "\n"
           + front_page(md) + "\n" + md_to_tex(md) + POSTAMBLE)
    with tempfile.TemporaryDirectory() as td:
        tex_path = os.path.join(td, "judgment.tex")
        with open(tex_path, "w") as f:
            f.write(tex)
        r = subprocess.run(["tectonic", "-o", td, tex_path],
                           capture_output=True, text=True, timeout=240)
        pdf_path = os.path.join(td, "judgment.pdf")
        if r.returncode != 0 or not os.path.exists(pdf_path):
            print(r.stdout[-800:], r.stderr[-800:])
            raise RuntimeError("tectonic failed to compile the judgment")
        out_pdf = os.path.splitext(md_path)[0] + ".pdf"
        with open(pdf_path, "rb") as src, open(out_pdf, "wb") as dst:
            dst.write(src.read())
    return out_pdf


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: elder-press.py <judgment.md>")
    print("pressed", compile_judgment(sys.argv[1]))
