"""OCR a scanned PDF into page-level JSONL with reading-order reconstruction.

Usage:
    python scripts/ocr_book.py --book CN-DIDAO-2011 --workers 4

Resumable: already processed pages are skipped. Progress is written to
data/ocr/<source_id>/progress.json. One JSON object per page is appended to
data/pages/<source_id>.ocr.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    OCR_DIR,
    PAGES_DIR,
    append_jsonl,
    book_path,
    clean_ocr_text,
    get_book,
    load_books,
    normalize_text,
    parse_printed_page,
    read_jsonl,
    save_json,
)

_ENGINE = None
_DOC = None
_DOC_PATH = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    return _ENGINE


def _get_doc(path: str):
    global _DOC, _DOC_PATH
    import pymupdf

    if _DOC is None or _DOC_PATH != path:
        if _DOC is not None:
            _DOC.close()
        _DOC = pymupdf.open(path)
        _DOC_PATH = path
    return _DOC


def _bbox_from_points(points) -> list[float]:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _reading_order(boxes: list[dict[str, Any]], width: float, height: float) -> tuple[list[dict[str, Any]], str]:
    """Reconstruct reading order for multi-column Chinese pages.

    Strategy: cluster boxes into columns by horizontal centre, then order
    columns left-to-right (horizontal text) or right-to-left (vertical text),
    and sort each column top-to-bottom. This is deliberately simple and
    explainable; pathological layouts are flagged by the caller.
    """
    if not boxes:
        return [], "empty"

    vertical = sum(
        1
        for b in boxes
        if (b["bbox"][3] - b["bbox"][1]) > 2.2 * max(1.0, b["bbox"][2] - b["bbox"][0])
        and len(b["text"]) >= 5
    )
    layout = "vertical" if vertical >= max(3, len(boxes) * 0.25) else "horizontal"

    heights = sorted(b["bbox"][3] - b["bbox"][1] for b in boxes)
    med_h = heights[len(heights) // 2] if heights else 20.0
    gap_threshold = max(width * 0.045, med_h * 1.4)

    centres = sorted((b["bbox"][0] + b["bbox"][2]) / 2 for b in boxes)
    clusters: list[list[float]] = []
    for c in centres:
        if clusters and c - clusters[-1][-1] <= gap_threshold:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    # Absorb tiny clusters into the nearest large cluster (headers, side notes).
    big = [cl for cl in clusters if len(cl) >= 2]
    if len(big) > 4 or not big:
        ordered = sorted(boxes, key=lambda b: (round(b["bbox"][1] / max(med_h, 1)), b["bbox"][0]))
        return ordered, layout + "+y-sort"

    bounds = [(min(cl), max(cl)) for cl in big]
    if vertical:
        bounds = sorted(bounds, key=lambda x: -x[0])
    else:
        bounds = sorted(bounds, key=lambda x: x[0])

    def col_index(b):
        c = (b["bbox"][0] + b["bbox"][2]) / 2
        best, bestd = 0, 1e18
        for i, (lo, hi) in enumerate(bounds):
            d = 0 if lo <= c <= hi else min(abs(c - lo), abs(c - hi))
            if d < bestd:
                best, bestd = i, d
        return best

    for b in boxes:
        b["_col"] = col_index(b)
    ordered = sorted(boxes, key=lambda b: (b["_col"], b["bbox"][1], b["bbox"][0]))
    for b in ordered:
        b.pop("_col", None)
    return ordered, layout


def _assemble_text(boxes: list[dict[str, Any]], layout: str) -> str:
    """Join OCR lines, inserting newlines at semantic labels and sentence ends."""
    label_re = re.compile(
        r"^(材料|做法|功效|别名|性味|主产地|成熟期|品种群|营养|食用|搭配|经典食谱|"
        r"加热烹调|切制|贮存|保存|挑选|备注|提示|注意|小贴士|原料|调料|步骤)"
    )
    out: list[str] = []
    for b in boxes:
        t = normalize_text(b["text"])
        if not t:
            continue
        if out and label_re.match(t):
            out.append("\n" + t)
        elif out and re.search(r"[。！？；：]$", out[-1]) and len(t) > 4:
            out.append("\n" + t)
        elif layout.startswith("vertical") and out:
            out.append("\n" + t)
        else:
            out.append(t)
    return clean_ocr_text("".join(out))


def ocr_page(args: tuple[str, int, float, bool]) -> dict[str, Any]:
    path, page_index, dpi, allow_suffix = args
    import pymupdf

    t0 = time.time()
    doc = _get_doc(path)
    page = doc[page_index]
    pix = page.get_pixmap(dpi=int(dpi), colorspace=pymupdf.csGRAY, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    engine = _get_engine()
    result, _ = engine(img)
    boxes: list[dict[str, Any]] = []
    warnings: list[str] = []
    if result:
        for item in result:
            pts, text, score = item[0], item[1], float(item[2])
            text = (text or "").strip()
            if not text:
                continue
            boxes.append({"text": text, "score": score, "bbox": _bbox_from_points(pts)})
    ordered, layout = _reading_order(boxes, float(pix.width), float(pix.height))
    text = _assemble_text(ordered, layout)
    printed, raw = parse_printed_page(ordered, float(pix.height), allow_suffix=allow_suffix)
    scores = [b["score"] for b in ordered]
    mean_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    low = sum(1 for s in scores if s < 0.75)
    if not boxes:
        warnings.append("no_text_detected")
    if mean_score and mean_score < 0.75:
        warnings.append("ocr_low_mean_confidence")
    if boxes and low / len(boxes) > 0.25:
        warnings.append("ocr_many_low_confidence_lines")
    if len(text) < 30 and boxes:
        warnings.append("ocr_sparse_text")
    return {
        "source_id": None,
        "pdf_page": page_index + 1,
        "printed_page": printed,
        "printed_page_raw": raw,
        "method": "ocr",
        "text": text,
        "text_raw": "\n".join(b["text"] for b in ordered),
        "lines": ordered,
        "n_lines": len(ordered),
        "mean_score": mean_score,
        "low_confidence_lines": low,
        "layout": layout,
        "image_size": [pix.width, pix.height],
        "dpi": dpi,
        "warnings": warnings,
        "elapsed_s": round(time.time() - t0, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dpi", type=float, default=150)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--pages", default="", help="comma separated 1-based pdf pages")
    args = parser.parse_args()

    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("ORT_NUM_THREADS", "2")

    book = get_book(args.book)
    pdf = book_path(book)
    if not pdf.exists():
        raise SystemExit(f"missing PDF: {pdf}")

    import pymupdf

    doc = pymupdf.open(pdf)
    total = doc.page_count
    doc.close()

    out_path = PAGES_DIR / f"{book['source_id']}.ocr.jsonl"
    done = {r["pdf_page"] for r in read_jsonl(out_path)}
    if args.pages:
        wanted = [int(x) for x in args.pages.split(",") if x.strip()]
    else:
        wanted = list(range(1, total + 1))
    if args.limit:
        wanted = wanted[: args.limit]
    todo = [p for p in wanted if p not in done]
    print(f"[{book['source_id']}] total={total} done={len(done)} todo={len(todo)} workers={args.workers}")
    if not todo:
        return

    progress_path = OCR_DIR / book["source_id"] / "progress.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    ok = failed = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(ocr_page, (str(pdf), p - 1, args.dpi, bool(book.get("page_number_suffix")))): p
            for p in todo
        }
        for i, fut in enumerate(as_completed(futures), 1):
            page_no = futures[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                failed += 1
                append_jsonl(
                    OCR_DIR / book["source_id"] / "failures.jsonl",
                    {"pdf_page": page_no, "error": repr(exc), "traceback": traceback.format_exc()},
                )
                print(f"  ! page {page_no} failed: {exc}")
                continue
            rec["source_id"] = book["source_id"]
            append_jsonl(out_path, rec)
            ok += 1
            elapsed = time.time() - started
            rate = ok / elapsed if elapsed else 0
            eta = (len(todo) - i) / rate / 60 if rate else 0
            if i % 10 == 0 or i == len(todo):
                print(
                    f"  {i}/{len(todo)} ok={ok} fail={failed} "
                    f"{rate:.2f} pages/s eta={eta:.1f} min last=p{page_no} chars={len(rec['text'])}"
                )
                save_json(
                    progress_path,
                    {
                        "source_id": book["source_id"],
                        "total": total,
                        "completed": len(done) + ok,
                        "failed": failed,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                )

    print(f"done ok={ok} failed={failed} in {(time.time()-started)/60:.1f} min -> {out_path}")


if __name__ == "__main__":
    main()
