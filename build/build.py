# -*- coding: utf-8 -*-
"""Assemble chapter fragments into build/book-raw.html"""
import json, os, re, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)

with io.open(os.path.join(SRC, "manifest.json"), encoding="utf-8") as f:
    M = json.load(f)

def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()

def farsi(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

# ---------- front matter (cover + about) ----------
front = read(os.path.join(SRC, "front.html"))

# ---------- TOC ----------
toc_rows = []
part_seen = set()
for ch in M["chapters"]:
    p = ch["part"]
    cls = {"zustand": "pz", "tq": "pt", "both": "pv", "ref": "ps"}[p]
    if p not in part_seen:
        part_seen.add(p)
        label = next(x["label"] for x in M["parts"] if x["id"] == p)
        c = {"zustand": "var(--z)", "tq": "var(--t)", "both": "var(--v)", "ref": "var(--s)"}[p]
        toc_rows.append(f'<div class="toc-part" style="color:{c}">{label}<span class="rule"></span></div>')
    toc_rows.append(
        f'<div class="toc-row {cls}">'
        f'<span class="t-num">فصل {ch["num"]}</span>'
        f'<span class="t-title">{ch["title"]}</span>'
        f'<span class="t-dots"></span>'
        f'<span class="t-pg" data-toc="{ch["id"]}">…</span>'
        f'</div>'
    )
toc = (
    '<section class="toc-page" id="toc">'
    '<div class="pgmark">TOC-PAGE</div>'
    '<h2>فهرست مطالب</h2>'
    + "\n".join(toc_rows) +
    '</section>'
)

# ---------- chapters ----------
chapters_html = []
for ch in M["chapters"]:
    frag = read(os.path.join(SRC, ch["file"]))
    chapters_html.append(frag.strip())

body = "\n".join([front, toc] + chapters_html)

html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{M["book"]["title"]}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
{body}
</body>
</html>
"""

out = os.path.join(BUILD, "book-raw.html")
with io.open(out, "w", encoding="utf-8") as f:
    f.write(html)

# copy style.css next to build for relative font paths
with io.open(os.path.join(SRC, "style.css"), encoding="utf-8") as f:
    css = f.read()
# fonts live in ROOT/fonts — build html sits in build/ so relative path ../fonts works
with io.open(os.path.join(BUILD, "style.css"), "w", encoding="utf-8") as f:
    f.write(css)

print("OK wrote", out, len(html), "chars")
