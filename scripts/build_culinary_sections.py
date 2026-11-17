"""Summarise chapter/section ranges from built chunks.

This is a navigation index, not a knowledge claim.  Each row points back to
the first PDF page and the observed printed page of a chapter so that the
search CLI can filter by book, series, volume and chapter.

Usage:
    python scripts/build_culinary_sections.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHUNKS_DIR, DATA, load_books, save_json, write_jsonl  # noqa: E402


def main() -> None:
    rows: list[dict[str, Any]] = []
    for book in load_books():
        sid = book["source_id"]
        path = CHUNKS_DIR / f"{sid}.jsonl"
        if not path.exists():
            continue
        chunks = [json.loads(line) for line in open(path, encoding="utf-8")]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            chapter = chunk.get("chapter") or "未分章"
            grouped[chapter].append(chunk)
        for n, (chapter, items) in enumerate(
            sorted(grouped.items(), key=lambda kv: min(x["pdf_page"] for x in kv[1])), 1
        ):
            items.sort(key=lambda x: (x["pdf_page"], x["chunk_id"]))
            first = items[0]
            sections = sorted({x.get("section") for x in items if x.get("section")})
            rows.append(
                {
                    "section_id": f"{sid}:chapter:{n:02d}",
                    "source_id": sid,
                    "book_title": book["title"],
                    "series": book.get("series"),
                    "volume": book.get("volume"),
                    "chapter": chapter,
                    "sections": sections[:20],
                    "first_pdf_page": first["pdf_page"],
                    "first_printed_page": first.get("printed_page"),
                    "last_pdf_page": max(x["pdf_page"] for x in items),
                    "chunk_count": len(items),
                    "evidence_quote": (first.get("content") or "")[:240],
                    "confidence": first.get("confidence") or "medium",
                }
            )
    write_jsonl(DATA / "culinary_sections.jsonl", rows)
    stats = {
        "rows": len(rows),
        "sources": len({r["source_id"] for r in rows}),
        "by_source": {
            sid: sum(1 for r in rows if r["source_id"] == sid)
            for sid in sorted({r["source_id"] for r in rows})
        },
    }
    save_json(DATA / "culinary_sections_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
