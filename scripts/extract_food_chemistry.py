"""Build a page-anchored Food Chemistry topic index.

This is a structural index, not a summary.  It preserves chapter, section,
heading text, PDF page and observed printed page so that an answer can point
back to the original page.  Mechanisms and numeric conditions must still be
quoted from the page; the index only helps find them.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, INDEX_DIR, book_path, get_book, load_json, read_jsonl, save_json, write_jsonl  # noqa: E402

SOURCE_ID = "FC-BELITZ-2009"
ROOT = Path(__file__).resolve().parent.parent
CHAPTER_MAPS = load_json(ROOT / "config" / "chapter_maps.json", {})

TOPIC_RE = re.compile(r"^(?:\d{1,2}(?:\.\d{1,3}){0,4})\s+[A-Z][A-Za-z].{1,110}$")
CHAPTER_RE = re.compile(r"^(?:\d{1,2})\s+[A-Z][A-Za-z].{1,90}$")
SENTENCE_RE = re.compile(r"[.!?]$")

# Unnumbered run-in headings that carry the core culinary-chemistry topics.
# They are matched as standalone short lines, not as free-text substrings.
KEY_TOPIC_RE = re.compile(
    r"^(Gelatinization|Retrogradation|Glass Transition|Maillard Reaction|"
    r"Caramelization|Lipid Oxidation|Peroxidation|Autoxidation|"
    r"Emulsions?|Emulsifiers?|Water Activity|Denaturation|Coagulation|"
    r"Enzymatic Browning|Nonenzymatic Browning|Antioxidants?|"
    r"Aroma Compounds?|Flavor Compounds?|Pigments?|Colorants?|"
    r"Proteins?|Lipids?|Carbohydrates?|Vitamins?|Minerals?)$",
    re.IGNORECASE,
)


def chapter_for(pdf_page: int) -> str | None:
    chapter = None
    for item in CHAPTER_MAPS.get(SOURCE_ID, {}).get("chapters", []):
        if pdf_page >= item["start"]:
            chapter = item["chapter"]
    return chapter


def page_lines(page) -> tuple[list[dict[str, Any]], float]:
    d = page.get_text("dict")
    lines: list[dict[str, Any]] = []
    sizes: list[float] = []
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if (s.get("text") or "").strip()]
            if not spans:
                continue
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
            sizes.extend(s.get("size", 0) for s in spans)
            lines.append(
                {
                    "text": text,
                    "bbox": [round(v, 1) for v in line["bbox"]],
                    "size": round(max(s.get("size", 0) for s in spans), 1),
                    "bold": any(("bold" in (s.get("font") or "").lower()) or (s.get("flags", 0) & 16) for s in spans),
                }
            )
    lines.sort(key=lambda r: (round(r["bbox"][1], 0), r["bbox"][0]))
    sizes.sort()
    body = sizes[len(sizes) // 2] if sizes else 9.5
    return lines, body


def main() -> None:
    book = get_book(SOURCE_ID)
    pdf = book_path(book)
    pages = {r["pdf_page"]: r for r in read_jsonl(DATA / "pages" / f"{SOURCE_ID}.jsonl")}
    doc = pymupdf.open(pdf)
    topics: list[dict[str, Any]] = []
    current_section: str | None = None
    for i in range(doc.page_count):
        page_rec = pages.get(i + 1)
        if not page_rec:
            continue
        chapter = chapter_for(i + 1)
        if chapter is None:
            continue
        lines, body = page_lines(doc[i])
        page_text = page_rec.get("text") or ""
        for rec in lines:
            text = rec["text"]
            text = re.sub(r"^(\d{1,2}(?:\.\d{1,3}){1,4})(?=[A-Z])", r"\1 ", text)
            if len(text) < 3 or len(text) > 150:
                continue
            is_chapter = bool(CHAPTER_RE.match(text)) and rec["size"] >= body + 1.0 and rec["bold"]
            numbered = bool(re.match(r"^\d{1,2}(?:\.\d{1,3}){1,4}\s+\S", text))
            # Section headings in this PDF are often the same point size as
            # body text and not flagged bold.  A leading hierarchical number
            # plus a short, non-sentence line is still strong structural
            # evidence; body references usually end with a period.
            is_topic = bool(TOPIC_RE.match(text)) and (
                (rec["bold"] and rec["size"] >= body + 0.4)
                or (numbered and not SENTENCE_RE.search(text) and len(text) <= 120)
            )
            if KEY_TOPIC_RE.match(text.strip()) and len(text) <= 50:
                is_topic = True
            if not (is_chapter or is_topic):
                continue
            if SENTENCE_RE.search(text) and not is_chapter:
                continue
            if is_topic and not is_chapter:
                current_section = text
            pos = page_text.find(text)
            quote = page_text[max(0, pos - 20): pos + 360].replace("\n", " ").strip() if pos >= 0 else page_text[:360].replace("\n", " ").strip()
            topics.append(
                {
                    "topic_id": f"{SOURCE_ID}:p{i+1}:t{len(topics)+1}",
                    "chapter": chapter,
                    "section": current_section,
                    "topic": text,
                    "source_id": SOURCE_ID,
                    "pdf_page": i + 1,
                    "printed_page": page_rec.get("printed_page"),
                    "evidence_quote": quote,
                    "keywords": [w for w in re.split(r"[^A-Za-z0-9αβγ]+", text) if len(w) > 2][:12],
                    "confidence": "high" if rec["bold"] else "medium",
                }
            )
    doc.close()
    seen: set[tuple[int, str]] = set()
    unique: list[dict[str, Any]] = []
    for t in topics:
        key = (t["pdf_page"], t["topic"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)
    topics = unique
    write_jsonl(DATA / "chemistry_topics.jsonl", topics)
    stats = {
        "source_id": SOURCE_ID,
        "topics": len(topics),
        "chapters": len({t["chapter"] for t in topics}),
        "pages_with_topics": len({t["pdf_page"] for t in topics}),
        "note": "Structural heading index only. Numerical conditions and mechanisms require page-level quotation.",
    }
    save_json(DATA / "chemistry_topics_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
