"""Inventory figures, page scans, and table candidates without inventing captions.

The output is deliberately conservative:

- every record is anchored to a real PDF page and a bounding box;
- text near a figure is stored as ``caption_candidate`` and marked
  ``needs_human_review`` rather than treated as a verified caption;
- scanned pages are recorded as ``page_scan`` (the OCR text is already the
  page-level transcription), not misrepresented as hundreds of independent
  food photographs;
- table detection is a line-density heuristic and is labelled
  ``table_candidate``.

No image is redistributed; the manifest preserves provenance and pointers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, IMAGES_DIR, PAGES_DIR, book_path, load_books, read_jsonl, write_jsonl  # noqa: E402

PAGE_FILES = {
    "MM-ZYX-2016": PAGES_DIR / "MM-ZYX-2016.jsonl",
    "CN-DIDAO-2011": PAGES_DIR / "CN-DIDAO-2011.ocr.jsonl",
    "FS-SFAH-2023": PAGES_DIR / "FS-SFAH-2023.jsonl",
    "DK-INGREDIENTS": PAGES_DIR / "DK-INGREDIENTS.ocr.jsonl",
    "MCG-V1-2013": PAGES_DIR / "MCG-V1-2013.ocr.jsonl",
    "MCG-V2-2013": PAGES_DIR / "MCG-V2-2013.ocr.jsonl",
    "MCG-V3-2013": PAGES_DIR / "MCG-V3-2013.ocr.jsonl",
    "FC-BELITZ-2009": PAGES_DIR / "FC-BELITZ-2009.jsonl",
    "FB-PAGE-2008": PAGES_DIR / "FB-PAGE-2008.jsonl",
    "CR-WXY-2003": PAGES_DIR / "CR-WXY-2003.ocr.jsonl",
}


def clean(text: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", "", text or "")
    return text[:limit] + ("…" if len(text) > limit else "")


def bbox_area(bbox: tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return (dx * dx + dy * dy) ** 0.5


def nearby_text(
    blocks: list[tuple[Any, ...]],
    bbox: tuple[float, float, float, float],
) -> tuple[str, str]:
    """Return (candidate text, status) from the closest text blocks."""
    candidates = []
    for b in blocks:
        if len(b) < 7 or b[6] != 0:
            continue
        text = clean(b[4], 500)
        if not text:
            continue
        candidates.append((gap(bbox, b[:4]), text))
    candidates.sort(key=lambda x: x[0])
    selected = [text for d, text in candidates if d <= 110][:2]
    if selected:
        return clean(" ".join(selected), 280), "needs_human_review"
    return "", "no_nearby_text_needs_review"


def table_candidates(page: pymupdf.Page, allow_text_tables: bool = False) -> list[dict[str, Any]]:
    """Return review candidates; never claims a fully parsed table."""
    candidates: list[dict[str, Any]] = []
    if allow_text_tables:
        try:
            found = page.find_tables(strategy="text")
            for t in found.tables:
                if t.col_count < 3 or t.row_count < 3:
                    continue
                preview = []
                for row in (t.extract() or [])[:3]:
                    preview.append([clean(str(cell), 80) for cell in row[:4]])
                candidates.append(
                    {
                        "bbox": [round(float(x), 2) for x in t.bbox],
                        "rows": t.row_count,
                        "cols": t.col_count,
                        "method": "pymupdf_table_text",
                        "preview": preview,
                    }
                )
        except Exception:
            pass

    try:
        drawings = page.get_drawings()
    except Exception:
        return candidates
    h = v = 0
    xs: list[float] = []
    ys: list[float] = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) <= 1.2:
                    h += 1
                    ys.extend([p1.y, p2.y])
                elif abs(p1.x - p2.x) <= 1.2:
                    v += 1
                    xs.extend([p1.x, p2.x])
    if h < 8 or v < 8:
        return candidates
    bbox = (
        min(xs) if xs else 0.0,
        min(ys) if ys else 0.0,
        max(xs) if xs else page.rect.width,
        max(ys) if ys else page.rect.height,
    )
    candidates.append(
        {
            "bbox": [round(x, 2) for x in bbox],
            "h_lines": h,
            "v_lines": v,
            "method": "vector_line_heuristic",
            "preview": [],
        }
    )
    return candidates


def main() -> int:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    stats_by_book: list[dict[str, Any]] = []

    for book in load_books():
        sid = book["source_id"]
        page_map = {r["pdf_page"]: r for r in read_jsonl(PAGE_FILES[sid])}
        doc = pymupdf.open(book_path(book))
        n_images = n_page_scans = n_tables = 0
        try:
            for page in doc:
                pdf_page = page.number + 1
                page_rec = page_map.get(pdf_page, {})
                printed = page_rec.get("printed_page")
                page_area = page.rect.width * page.rect.height
                infos = page.get_image_info(xrefs=True)
                blocks = page.get_text("blocks")

                for i, info in enumerate(infos, 1):
                    bbox = tuple(float(x) for x in info["bbox"])
                    coverage = bbox_area(bbox) / page_area if page_area else 0.0
                    is_page_scan = book["kind"] == "scanned" and coverage >= 0.8
                    if is_page_scan:
                        kind = "page_scan"
                        caption = clean(page_rec.get("text") or "", 220)
                        status = "page_scan_text_excerpt"
                        n_page_scans += 1
                    else:
                        kind = "image"
                        caption, status = nearby_text(blocks, bbox)
                        n_images += 1
                    rows.append(
                        {
                            "visual_id": f"{sid}:p{pdf_page}:i{i}",
                            "source_id": sid,
                            "book_title": book["short_title"],
                            "pdf_page": pdf_page,
                            "printed_page": printed,
                            "kind": kind,
                            "xref": info.get("xref"),
                            "width": info.get("width"),
                            "height": info.get("height"),
                            "bbox": [round(x, 2) for x in bbox],
                            "coverage": round(coverage, 4),
                            "caption_candidate": caption,
                            "caption_status": status,
                            "extraction_method": "pdf_image_metadata",
                        }
                    )

                for j, tc in enumerate(table_candidates(page, allow_text_tables=book["kind"] == "digital"), 1):
                    bbox = tuple(tc["bbox"])
                    caption, status = nearby_text(blocks, bbox)
                    rows.append(
                        {
                            "visual_id": f"{sid}:p{pdf_page}:t{j}",
                            "source_id": sid,
                            "book_title": book["short_title"],
                            "pdf_page": pdf_page,
                            "printed_page": printed,
                            "kind": "table_candidate",
                            "xref": None,
                            "width": None,
                            "height": None,
                            "bbox": tc["bbox"],
                            "coverage": None,
                            "caption_candidate": caption,
                            "caption_status": status,
                            "extraction_method": tc["method"],
                            "h_lines": tc.get("h_lines"),
                            "v_lines": tc.get("v_lines"),
                            "rows": tc.get("rows"),
                            "cols": tc.get("cols"),
                            "table_preview": tc.get("preview"),
                        }
                    )
                    n_tables += 1
        finally:
            doc.close()
        stats_by_book.append(
            {
                "source_id": sid,
                "images": n_images,
                "page_scans": n_page_scans,
                "table_candidates": n_tables,
            }
        )
        print(f"{sid}: images={n_images} page_scans={n_page_scans} table_candidates={n_tables}")

    manifest = IMAGES_DIR / "manifest.jsonl"
    n = write_jsonl(manifest, rows)
    stats = {
        "records": n,
        "images": sum(x["images"] for x in stats_by_book),
        "page_scans": sum(x["page_scans"] for x in stats_by_book),
        "table_candidates": sum(x["table_candidates"] for x in stats_by_book),
        "books": stats_by_book,
        "caveat": "caption_candidate 是邻近文字候选，不是经人工确认的图注；table_candidate 是文本/线框启发式，不是经人工确认的表格结构。",
    }
    (IMAGES_DIR / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
