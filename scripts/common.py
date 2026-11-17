"""Shared utilities for the Ingredient Research & Culinary R&D knowledge base.

Design rules:
- Everything is file-based and reproducible.
- No network access is used anywhere in the pipeline.
- Page numbers are never invented. `printed_page` is only filled when a printed
  page number is directly observed in the page image / text layer. Otherwise it
  stays null and the citation falls back to the PDF page.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"

PAGES_DIR = DATA / "pages"
OCR_DIR = DATA / "ocr"
CHUNKS_DIR = DATA / "chunks"
INDEX_DIR = DATA / "index"
INGREDIENTS_DIR = DATA / "ingredients"
IMAGES_DIR = DATA / "images"

for _d in (PAGES_DIR, OCR_DIR, CHUNKS_DIR, INDEX_DIR, INGREDIENTS_DIR, IMAGES_DIR, REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

_WS_RE = re.compile(r"[ \t\u3000\u00a0]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def load_books() -> list[dict[str, Any]]:
    with open(CONFIG / "books.json", "r", encoding="utf-8") as fh:
        return json.load(fh)["books"]


def get_book(source_id: str) -> dict[str, Any]:
    for book in load_books():
        if book["source_id"] == source_id:
            return book
    raise KeyError(f"unknown source_id: {source_id}")


def book_path(book: dict[str, Any]) -> Path:
    return (ROOT / book["file"]).resolve()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def normalize_text(text: str) -> str:
    """Normalise whitespace without destroying paragraph structure."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


def clean_ocr_text(text: str) -> str:
    """Remove known scan watermarks and OCR artefacts, conservatively."""
    text = normalize_text(text)
    watermarks = [
        r"高清PDF原创",
        r"www\.gqpdf\.com",
        r"高清\s*PDF",
        r"扫描全能王",
    ]
    for pat in watermarks:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def format_citation(rec: dict[str, Any], short: bool = False) -> str:
    """Canonical citation string used by every reference card.

    Example: 《中药学》p.123（PDF p.184）
    When the printed number was not observable: 《中药学》PDF p.184（电子版无印刷页码）
    """
    title = rec.get("short_title") or rec.get("book_title") or rec["source_id"]
    printed = rec.get("printed_page")
    pdf = rec.get("pdf_page")
    if printed:
        base = f"《{title}》p.{printed}"
        if pdf and not short:
            base += f"（PDF {pdf}）"
        return base
    return f"《{title}》PDF {pdf}" + ("" if short else "（电子版无印刷页码）")


def page_label(rec: dict[str, Any]) -> str:
    if rec.get("printed_page"):
        return f"p.{rec['printed_page']}/PDF {rec['pdf_page']}"
    return f"PDF {rec['pdf_page']}"


def parse_printed_page(
    lines: list[dict[str, Any]],
    page_height: float,
    allow_suffix: bool = False,
) -> tuple[int | None, str | None]:
    """Detect a visible printed page number at the top or bottom margin.

    Only directly observed numbers are accepted. Years (19xx/20xx) are rejected.
    """
    candidates: list[tuple[int, int, str]] = []  # priority, value, raw
    for line in lines:
        text = (line.get("text") or "").strip()
        if not text or len(text) > (90 if allow_suffix else 40):
            continue
        y0, y1 = line["bbox"][1], line["bbox"][3]
        margin = 0.09 if allow_suffix else 0.075
        in_top = y1 <= page_height * margin
        in_bottom = y0 >= page_height * (1 - margin)
        if not (in_top or in_bottom):
            continue
        raw = text.replace(" ", "")
        value = None
        m = re.fullmatch(r"[·•\-—]?(\d{1,4})[·•\-—]?", raw)
        if m:
            value = int(m.group(1))
        else:
            m = re.match(r"^(\d{1,4})[丨|｜]", raw)
            if m:
                value = int(m.group(1))
            else:
                m = re.fullmatch(r"第?(\d{1,4})页?", raw)
                if m:
                    value = int(m.group(1))
        if value is None:
            if allow_suffix:
                # Running footers such as "Flavor Matchmaking: The Charts 235"
                # or "048食物与厨艺" carry the page number at one edge.  OCR
                # frequently drops the space, so do not require whitespace.
                m = re.match(r"^(\d{1,4})[^\d].{1,80}$", text)
                if m:
                    value = int(m.group(1))
                else:
                    m = re.match(r"^.{2,80}?[^\d](\d{1,4})$", text)
                    if m:
                        value = int(m.group(1))
            if value is None:
                continue
        if 1900 <= value <= 2100:
            continue
        if value == 0:
            continue
        priority = 0 if in_bottom else 1
        # A bare margin number is stronger evidence than a footer suffix.
        if allow_suffix and value is not None and not re.fullmatch(r"[·•\-—]?\d{1,4}[·•\-—]?", raw):
            priority = 2
        candidates.append((priority, value, text))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1], candidates[0][2]


def snippet(content: str, terms: list[str], width: int = 220) -> str:
    """Return a readable snippet around the first matched term."""
    flat = re.sub(r"\s+", "", content)
    pos = -1
    for term in terms:
        if not term:
            continue
        p = flat.find(term)
        if p >= 0 and (pos < 0 or p < pos):
            pos = p
    if pos < 0:
        return flat[:width] + ("…" if len(flat) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(flat), start + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(flat) else ""
    return prefix + flat[start:end] + suffix


def die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)
