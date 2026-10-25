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

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=2.4cm]{geometry}
\usepackage{parskip}
\usepackage{microtype}
\pagestyle{plain}
\begin{document}
"""

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
        if s.startswith("# "):                      # the caption/title
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
    return "\n".join(out) + "\n"


def compile_judgment(md_path):
    with open(md_path) as f:
        md = f.read()
    tex = PREAMBLE + md_to_tex(md) + POSTAMBLE
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
