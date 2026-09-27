# -*- coding: utf-8 -*-
"""Post-process the rendered PDF:
1. Find each chapter's page via invisible pgmark text
2. Inject real page numbers into TOC (Persian digits) in build/book.html
3. Stamp footers (page number + book title) with proper RTL via insert_htmlbox
4. Set metadata + add bookmarks (outline)
Usage: python post.py [--render-only]
"""
import io, json, os, re, subprocess, sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)
SKILL = r"C:\Users\MahdiLpTp\.zcode\cli\plugins\cache\zcode-plugins-official\document-skills\0.1.4\skills\pdf"
H2P = os.path.join(SKILL, "scripts", "html2pdf-next.js")

MANIFEST = json.load(io.open(os.path.join(ROOT, "src", "manifest.json"), encoding="utf-8"))

def farsi(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

def render(html_path, pdf_path):
    r = subprocess.run(
        ["node", H2P, html_path, "--output", pdf_path],
        cwd=ROOT, capture_output=True, text=True, shell=False,
    )
    sys.stdout.write(r.stdout[-2500:] if r.stdout else "")
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit("render failed")
    return pdf_path

def find_pages(pdf_path):
    doc = pymupdf.open(pdf_path)
    marks = {"ABOUT-PAGE": None, "TOC-PAGE": None}
    for ch in MANIFEST["chapters"]:
        marks[f"CHAPTER-{ch['id'][2:]}"] = None
    for pno in range(len(doc)):
        text = doc[pno].get_text()
        for m in marks:
            if marks[m] is None and m in text:
                marks[m] = pno + 1  # 1-based
    total = len(doc)
    doc.close()
    return marks, total

def inject_toc(book_html_path, marks):
    html = io.open(book_html_path, encoding="utf-8").read()
    for ch in MANIFEST["chapters"]:
        pg = marks.get(f"CHAPTER-{ch['id'][2:]}")
        assert pg, f"page not found for {ch['id']}"
        html = html.replace(
            f'<span class="t-pg" data-toc="{ch["id"]}">…</span>',
            f'<span class="t-pg" data-toc="{ch["id"]}">{farsi(pg)}</span>',
        )
    io.open(book_html_path, "w", encoding="utf-8").write(html)

FOOTER_CSS = """
@font-face { font-family:'vz'; src:url('Vazirmatn-Regular.ttf'); }
body { margin:0; }
.fb { width:100%; font-family:'vz',sans-serif; direction:rtl; color:#64748B; font-size:8.5px; }
.fb .num { color:#334155; font-weight:700; font-size:9px; }
.fb .t { letter-spacing:.4px; }
"""

def stamp_footers(src_pdf, dst_pdf):
    doc = pymupdf.open(src_pdf)
    arch = pymupdf.Archive(os.path.join(ROOT, "fonts"))
    W, H = doc[0].rect.width, doc[0].rect.height
    for pno in range(1, len(doc)):  # skip cover (page 0)
        page = doc[pno]
        num = pno + 1
        rect = pymupdf.Rect(40, H - 34, W - 40, H - 14)
        page.insert_htmlbox(
            rect,
            f'<div class="fb"><span class="t">{MANIFEST["book"]["title"]}</span>'
            f' &nbsp;·&nbsp; <span class="num">{farsi(num)}</span></div>',
            css=FOOTER_CSS,
            archive=arch,
        )
    doc.subset_fonts()
    doc.save(dst_pdf, garbage=4, deflate=True, clean=True)
    doc.close()

def set_meta_and_toc(src_pdf, dst_pdf, marks):
    doc = pymupdf.open(src_pdf)
    doc.set_metadata({
        "title": MANIFEST["book"]["title"] + " — دورهٔ جامع فارسی",
        "author": "Z.ai",
        "subject": MANIFEST["book"]["subtitle"],
        "keywords": "zustand, tanstack query, react, فارسی, دوره",
        "creator": "Z.ai",
    })
    toc = [[1, "جلد", 1], [1, "دربارهٔ این دوره", marks["ABOUT-PAGE"] or 2], [1, "فهرست مطالب", marks["TOC-PAGE"] or 3]]
    for ch in MANIFEST["chapters"]:
        pg = marks[f"CHAPTER-{ch['id'][2:]}"]
        toc.append([1, f"فصل {ch['num']}: {ch['title']}", pg])
    doc.set_toc(toc)
    doc.subset_fonts()
    doc.save(dst_pdf, garbage=4, deflate=True, clean=True)
    doc.close()

if __name__ == "__main__":
    book_html = os.path.join(BUILD, "book.html")
    raw_pdf = os.path.join(BUILD, "book-raw.pdf")
    numbered_pdf = os.path.join(BUILD, "book-numbered.pdf")
    final_pdf = os.path.join(OUT, "دوره-صفر-تا-صد-Zustand-TanStackQuery.pdf")

    # pass 1: render + find chapter pages
    render(book_html, raw_pdf)
    marks, total = find_pages(raw_pdf)
    print("marks:", marks, "pages:", total)

    # pass 2: inject TOC numbers, re-render, re-verify
    inject_toc(book_html, marks)
    render(book_html, raw_pdf)
    marks2, total2 = find_pages(raw_pdf)
    assert marks2 == marks and total2 == total, f"pagination shifted: {marks} -> {marks2}"
    print("pagination stable, pages:", total2)

    # footers + metadata + bookmarks
    stamp_footers(raw_pdf, numbered_pdf)
    set_meta_and_toc(numbered_pdf, final_pdf, marks)
    print("OK final:", final_pdf)
