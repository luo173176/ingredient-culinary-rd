"""Build citation-preserving knowledge chunks from extracted page text.

Usage:
    python scripts/segment.py --book MM-ZYX-2016
    python scripts/segment.py --all

Each chunk stays on a single PDF page. This is a deliberate design choice:
citations can always be traced to one page, and OCR uncertainty is contained.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import jieba
import jieba.analyse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CHUNKS_DIR,
    PAGES_DIR,
    clean_ocr_text,
    format_citation,
    get_book,
    load_books,
    load_json,
    normalize_text,
    save_json,
    snippet,
    write_jsonl,
)

jieba.setLogLevel(20)

CHAPTER_MAPS = load_json(Path(__file__).resolve().parent.parent / "config" / "chapter_maps.json", {})

LABELS = (
    "材料",
    "原料",
    "调料",
    "做法",
    "步骤",
    "功效",
    "别名",
    "性味",
    "主产地",
    "成熟期",
    "品种群",
    "食用",
    "搭配",
    "加热烹调",
    "切制",
    "选购",
    "贮存",
    "保存",
)
LABEL_RE = re.compile(r"^(?:" + "|".join(LABELS) + r")[：:]?")
RECIPE_RE = re.compile(r"(材料|原料|调料)[：:]")
COOK_RE = re.compile(r"(煮|炒|蒸|烤|煎|炖|焖|炸|拌|腌|焯|煸|烧|煲|熬|烤制|加热)")
ATTR_RE = re.compile(r"(别名|性味|主产地|成熟期|品种群|选购|贮存|功效)[：:]")
HEADER_NOISE = re.compile(
    r"^(中国地道食材图录大全|食材百科全书|中药学|盐，脂，酸，热.*|第[一二三四五六七八九十]+[章节].{0,20}|"
    r"\d{1,4}|·\d{1,4}·|高清.*|www\..*)$"
)


def page_file(source_id: str) -> Path:
    ocr = PAGES_DIR / f"{source_id}.ocr.jsonl"
    if ocr.exists():
        return ocr
    return PAGES_DIR / f"{source_id}.jsonl"


def load_pages(source_id: str) -> list[dict[str, Any]]:
    path = page_file(source_id)
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    rows.sort(key=lambda r: r["pdf_page"])
    return rows


def chapter_for(book_id: str, pdf_page: int, page: dict[str, Any]) -> tuple[str | None, str | None]:
    cm = CHAPTER_MAPS.get(book_id, {})
    chapter = None
    for item in cm.get("chapters", []):
        if pdf_page >= item["start"]:
            chapter = item["chapter"]
    if chapter:
        return chapter, page.get("section")
    toc_path = page.get("toc_path") or []
    section = page.get("section")
    if not chapter and page.get("chapter"):
        chapter = page.get("chapter")
    if section and chapter and section == chapter:
        section = None
    return chapter, section


def clean_page_text(page: dict[str, Any]) -> str:
    lines = []
    for line in (page.get("text") or "").split("\n"):
        s = line.strip()
        if not s:
            continue
        if HEADER_NOISE.match(s):
            continue
        lines.append(s)
    text = "\n".join(lines)
    if page.get("method") == "ocr":
        text = clean_ocr_text(text)
    return normalize_text(text)


def merge_ocr_lines(text: str) -> str:
    """Join OCR line breaks inside paragraphs while keeping labels separate."""
    out: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if out and not LABEL_RE.match(line) and not re.search(r"[。！？；：]$", out[-1]):
            out[-1] += line
        else:
            out.append(line)
    return "\n".join(out)


def split_chunks(text: str, target: int = 760, overlap: int = 80) -> list[str]:
    text = re.sub(r"\n+", "\n", text).strip()
    if len(text) <= target * 1.25:
        return [text] if text else []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for para in paragraphs:
        if len(cur) + len(para) + 1 <= target:
            cur = (cur + "\n" + para).strip()
            continue
        if cur:
            chunks.append(cur)
        if len(para) > target * 1.4:
            # Split very long OCR paragraphs on sentence punctuation.
            sentences = re.split(r"(?<=[。！？；])", para)
            buf = ""
            for s in sentences:
                if len(buf) + len(s) <= target:
                    buf += s
                else:
                    if buf:
                        chunks.append(buf)
                    buf = s
            cur = buf
        else:
            cur = para
    if cur:
        chunks.append(cur)
    # Add a small overlap so passages crossing a chunk boundary remain findable.
    if overlap and len(chunks) > 1:
        out = [chunks[0]]
        for prev, nxt in zip(chunks, chunks[1:]):
            out.append((prev[-overlap:] + nxt).strip())
        chunks = out
    return [c for c in chunks if len(c) >= 40]


def classify(text: str, page: dict[str, Any]) -> str:
    if RECIPE_RE.search(text) and COOK_RE.search(text):
        return "recipe"
    if ATTR_RE.search(text):
        return "attribute"
    if page.get("method") == "text_layer" and len(text) < 80 and not re.search(r"[。！？]", text):
        return "heading"
    return "text"


def keywords_for(text: str, k: int = 10) -> list[str]:
    try:
        kws = jieba.analyse.extract_tags(text, topK=k, withWeight=False)
    except Exception:  # noqa: BLE001
        kws = []
    return [w for w in kws if len(w) > 1][:k]


def build(book: dict[str, Any], lexicon: dict[str, Any]) -> dict[str, Any]:
    rows = load_pages(book["source_id"])
    cm = CHAPTER_MAPS.get(book["source_id"], {})
    start = cm.get("content_start", 1)
    end = cm.get("content_end", 10**9)
    chunks: list[dict[str, Any]] = []
    for page in rows:
        text = clean_page_text(page)
        if len(text) < 25:
            continue
        text = merge_ocr_lines(text)
        chapter, section = chapter_for(book["source_id"], page["pdf_page"], page)
        if chapter is None and page.get("chapter"):
            chapter = page.get("chapter")
        if section is None and page.get("section"):
            section = page.get("section")
        kind = "content" if start <= page["pdf_page"] <= end else "front_matter_or_appendix"
        printed = page.get("printed_page")
        if printed and abs(printed - page["pdf_page"]) > 300:
            printed = None
        for i, piece in enumerate(split_chunks(text), 1):
            matched = [
                name
                for name, aliases in lexicon.items()
                if name in piece or any(a in piece for a in aliases)
            ][:12]
            conf = "high"
            if page.get("method") == "ocr":
                score = page.get("mean_score") or 0
                conf = "medium" if score >= 0.72 else "low"
                if "ocr_many_low_confidence_lines" in (page.get("warnings") or []):
                    conf = "low"
            chunks.append(
                {
                    "chunk_id": f"{book['source_id']}:p{page['pdf_page']}:c{i}",
                    "source_id": book["source_id"],
                    "book_title": book["title"],
                    "short_title": book["short_title"],
                    "chapter": chapter,
                    "section": section,
                    "printed_page": printed,
                    "pdf_page": page["pdf_page"],
                    "page_kind": kind,
                    "content_type": classify(piece, page),
                    "content": piece,
                    "keywords": keywords_for(piece),
                    "related_ingredients": matched,
                    "confidence": conf,
                    "extraction_method": page.get("method"),
                    "ocr_mean_score": page.get("mean_score"),
                    "warnings": page.get("warnings") or [],
                    "char_len": len(piece),
                    "citation": format_citation(
                        {
                            "short_title": book["short_title"],
                            "printed_page": printed,
                            "pdf_page": page["pdf_page"],
                        }
                    ),
                }
            )

    out = CHUNKS_DIR / f"{book['source_id']}.jsonl"
    write_jsonl(out, chunks)
    by_type: dict[str, int] = {}
    for c in chunks:
        by_type[c["content_type"]] = by_type.get(c["content_type"], 0) + 1
    stats = {
        "source_id": book["source_id"],
        "chunks": len(chunks),
        "chars": sum(c["char_len"] for c in chunks),
        "by_content_type": by_type,
        "pages_with_chunks": len({c["pdf_page"] for c in chunks}),
        "high_confidence": sum(1 for c in chunks if c["confidence"] == "high"),
        "medium_confidence": sum(1 for c in chunks if c["confidence"] == "medium"),
        "low_confidence": sum(1 for c in chunks if c["confidence"] == "low"),
        "output": str(out),
    }
    save_json(CHUNKS_DIR / f"{book['source_id']}.stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False))
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    lex_path = Path(__file__).resolve().parent.parent / "config" / "ingredient_lexicon.json"
    raw = load_json(lex_path, {"entries": []})
    lexicon = {}
    for e in raw.get("entries", []):
        lexicon[e["canonical"]] = e.get("aliases", [])
    books = load_books()
    if args.all:
        targets = books
    elif args.book:
        targets = [get_book(args.book)]
    else:
        raise SystemExit("--book or --all required")
    for b in targets:
        if not page_file(b["source_id"]).exists():
            print(f"skip {b['source_id']}: no page file")
            continue
        build(b, lexicon)


if __name__ == "__main__":
    main()
