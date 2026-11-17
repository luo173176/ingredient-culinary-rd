"""Extract page-level text from digital (text-layer) PDFs.

Usage:
    python scripts/ingest_digital.py --book MM-ZYX-2016
    python scripts/ingest_digital.py --all-digital

Output: data/pages/<source_id>.jsonl
Each record keeps the PDF page, the directly observed printed page (if any),
the TOC heading path, line-level extraction metadata, and warnings.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    PAGES_DIR,
    book_path,
    get_book,
    load_books,
    normalize_text,
    parse_printed_page,
    save_json,
    write_jsonl,
)


def toc_map(doc) -> list[tuple[int, int, str]]:
    """Return (level, page_1based, title) sorted by page then level."""
    out = []
    for level, title, page in doc.get_toc(simple=True):
        if page and page > 0:
            out.append((int(level), int(page), normalize_text(title)))
    out.sort(key=lambda x: (x[1], x[0]))
    return out


def heading_for(
    page: int, toc: list[tuple[int, int, str]]
) -> tuple[str | None, str | None, str | None, list[str]]:
    path: list[str] = []
    for level, p, title in toc:
        if p > page:
            break
        if level <= 3:
            path.append(title)
    # Keep only a single path: rebuild from the last level-1/2 anchors.
    part = None
    chapter = None
    section = None
    for level, p, title in toc:
        if p > page:
            break
        if level == 1:
            part = title
            chapter = None
            section = None
        elif level == 2:
            chapter = title
            section = None
        elif level == 3:
            section = title
    if chapter is None and part:
        chapter = part
        part = None
    return part, chapter, section, path[-4:]


def extract_page(page, toc: list[tuple[int, int, str]], allow_suffix: bool = False) -> dict[str, Any]:
    d = page.get_text("dict")
    lines: list[dict[str, Any]] = []
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            # PyMuPDF sometimes emits one span per word with no trailing
            # space.  Joining blindly produces "Water(moisture)isthe..." and
            # destroys both search and citation fidelity.  Re-insert a space
            # when the horizontal gap between spans is visible.
            parts: list[str] = []
            prev = None
            for s in spans:
                t = s.get("text", "")
                if prev is not None and t:
                    gap = s["bbox"][0] - prev["bbox"][2]
                    if gap > 0.8 and parts and not parts[-1].endswith((" ", "\n")):
                        parts.append(" ")
                parts.append(t)
                prev = s
            text = "".join(parts).strip()
            if not text:
                continue
            sizes = [s.get("size", 0) for s in spans if s.get("text", "").strip()]
            lines.append(
                {
                    "text": text,
                    "bbox": [round(v, 1) for v in line["bbox"]],
                    "size": round(max(sizes) if sizes else 0, 1),
                }
            )
    lines.sort(key=lambda x: (round(x["bbox"][1], 0), x["bbox"][0]))
    text = normalize_text("\n".join(line["text"] for line in lines))
    printed, raw = parse_printed_page(lines, page.rect.height, allow_suffix=allow_suffix)
    part, chapter, section, path = heading_for(page.number + 1, toc)
    warnings: list[str] = []
    if len(text) < 30:
        warnings.append("near_empty_text_layer")
    if not lines:
        warnings.append("no_text_lines")
    sizes = sorted(line["size"] for line in lines if line["size"])
    return {
        "source_id": None,
        "pdf_page": page.number + 1,
        "printed_page": printed,
        "printed_page_raw": raw,
        "method": "text_layer",
        "text": text,
        "text_raw": "\n".join(line["text"] for line in lines),
        "n_lines": len(lines),
        "median_font_size": sizes[len(sizes) // 2] if sizes else None,
        "chapter": chapter,
        "section": section,
        "part": part,
        "toc_path": path,
        "warnings": warnings,
    }


def run(book: dict[str, Any]) -> dict[str, Any]:
    pdf = book_path(book)
    if not pdf.exists():
        raise SystemExit(f"missing PDF: {pdf}")
    t0 = time.time()
    doc = pymupdf.open(pdf)
    toc = toc_map(doc)
    rows = []
    for i in range(doc.page_count):
        rec = extract_page(doc[i], toc, allow_suffix=bool(book.get("page_number_suffix")))
        rec["source_id"] = book["source_id"]
        rows.append(rec)
    doc.close()
    out = PAGES_DIR / f"{book['source_id']}.jsonl"
    write_jsonl(out, rows)
    stats = {
        "source_id": book["source_id"],
        "title": book["title"],
        "pages": len(rows),
        "pages_with_text": sum(1 for r in rows if len(r["text"]) >= 30),
        "near_empty_pages": [r["pdf_page"] for r in rows if len(r["text"]) < 30],
        "chars": sum(len(r["text"]) for r in rows),
        "printed_page_detected": sum(1 for r in rows if r["printed_page"]),
        "toc_entries": len(toc),
        "elapsed_s": round(time.time() - t0, 1),
        "output": str(out.relative_to(out.parents[2])),
    }
    save_json(PAGES_DIR / f"{book['source_id']}.stats.json", stats)
    print(
        f"[{book['source_id']}] pages={stats['pages']} text={stats['pages_with_text']} "
        f"chars={stats['chars']} printed_detected={stats['printed_page_detected']} "
        f"time={stats['elapsed_s']}s"
    )
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--all-digital", action="store_true")
    args = ap.parse_args()
    books = load_books()
    if args.all_digital:
        targets = [b for b in books if b["kind"] == "digital"]
    elif args.book:
        targets = [get_book(args.book)]
    else:
        raise SystemExit("--book or --all-digital is required")
    for b in targets:
        run(b)


if __name__ == "__main__":
    main()
