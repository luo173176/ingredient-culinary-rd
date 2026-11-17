"""Re-derive printed page numbers from existing OCR line boxes.

The first OCR pass for the three 《食物与厨艺》 volumes ran before the footer
parser understood footers such as ``048食物与厨艺``.  Re-running OCR would
cost more than an hour, so this script re-parses the saved ``lines`` arrays and
snaps each candidate to the book's observed PDF-to-printed offset.

Direct observation wins: a candidate is accepted only when it is a visible
margin number within one page of the offset expected from the rest of the
book.  Otherwise ``printed_page`` becomes null and the raw text is kept for
review.  Nothing is invented.

Usage:
    python scripts/fix_printed_pages.py --book MCG-V1-2013
    python scripts/fix_printed_pages.py --all-mcg
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PAGES_DIR, get_book, load_books, save_json, write_jsonl  # noqa: E402


def margin_lines(page: dict[str, Any]) -> list[dict[str, Any]]:
    height = float((page.get("image_size") or [0, 0])[1] or 0)
    if not height:
        return []
    out = []
    for line in page.get("lines") or []:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        y0, y1 = float(line["bbox"][1]), float(line["bbox"][3])
        if y1 <= height * 0.10 or y0 >= height * 0.90:
            out.append(line)
    return out


def numeric_candidates(page: dict[str, Any]) -> list[tuple[int, int, str]]:
    """Return (priority, value, raw).  Lower priority is stronger."""
    height = float((page.get("image_size") or [0, 0])[1] or 0)
    cands: list[tuple[int, int, str]] = []
    for line in margin_lines(page):
        text = (line.get("text") or "").strip()
        raw = text.replace(" ", "")
        y1 = float(line["bbox"][3])
        top = y1 <= height * 0.10
        value = None
        # Bare margin number.
        m = re.fullmatch(r"[·•\-—]?(\d{1,4})[·•\-—]?", raw)
        if m:
            value = int(m.group(1))
        else:
            # OCR often appends a stray digit to a zero-padded page number:
            # "0461" for 046, "0981 食物时艺" for 098.
            m = re.match(r"^(0\d{2})\d(?=\D|$)", raw)
            if m:
                value = int(m.group(1))
            else:
                m = re.match(r"^(\d{3})(?=\D)", raw)
                if not m:
                    m = re.search(r"(\d{3})$", raw)
                if m:
                    value = int(m.group(1))
        if value is None or value == 0 or 1900 <= value <= 2100:
            continue
        prio = 0 if top else 1
        cands.append((prio, value, text))
    return cands


def infer_offset(rows: list[dict[str, Any]]) -> int | None:
    diffs: Counter[int] = Counter()
    for page in rows:
        raw = (page.get("printed_page_raw") or "").replace(" ", "")
        if re.fullmatch(r"\d{3}", raw):
            value = int(raw)
            if 1900 <= value <= 2100 or value == 0:
                continue
            diffs[value - int(page["pdf_page"])] += 1
    if not diffs:
        return None
    diff, count = diffs.most_common(1)[0]
    # Require some corroboration before using a global offset.
    if count < 5:
        return None
    return diff


def fix_page(page: dict[str, Any], offset: int | None) -> str:
    old = page.get("printed_page")
    old_raw = page.get("printed_page_raw")
    cands = numeric_candidates(page)
    chosen: tuple[int, int, str] | None = None
    if offset is not None:
        expected = int(page["pdf_page"]) + offset
        close = [c for c in cands if abs(c[1] - expected) <= 1]
        if close:
            close.sort(key=lambda c: (c[0], abs(c[1] - expected)))
            chosen = close[0]
    elif cands:
        cands.sort(key=lambda c: c[0])
        chosen = cands[0]

    status = "unchanged"
    if chosen:
        value, raw = chosen[1], chosen[2]
        if value != old:
            status = "fixed"
        page["printed_page"] = value
        page["printed_page_raw"] = raw
    else:
        if old is not None:
            status = "cleared"
        page["printed_page"] = None
        if old_raw:
            page["printed_page_raw_old"] = old_raw
        page["printed_page_raw"] = None
    return status


def run(book: dict[str, Any]) -> dict[str, Any]:
    sid = book["source_id"]
    path = PAGES_DIR / f"{sid}.ocr.jsonl"
    if not path.exists():
        raise SystemExit(f"missing OCR pages: {path}")
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    rows.sort(key=lambda r: r["pdf_page"])
    offset = infer_offset(rows)
    counts: Counter[str] = Counter()
    for page in rows:
        counts[fix_page(page, offset)] += 1
    write_jsonl(path, rows)
    stats = {
        "source_id": sid,
        "pages": len(rows),
        "inferred_offset": offset,
        "fixed": counts["fixed"],
        "cleared": counts["cleared"],
        "unchanged": counts["unchanged"],
        "printed_page_present": sum(1 for r in rows if r.get("printed_page") is not None),
    }
    save_json(PAGES_DIR / f"{sid}.pagefix.json", stats)
    print(json.dumps(stats, ensure_ascii=False))
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--all-mcg", action="store_true")
    args = ap.parse_args()
    books = load_books()
    if args.all_mcg:
        targets = [b for b in books if b.get("series") == "食物与厨艺"]
    elif args.book:
        targets = [get_book(args.book)]
    else:
        raise SystemExit("--book or --all-mcg is required")
    for book in targets:
        run(book)


if __name__ == "__main__":
    main()
