"""Build the SQLite FTS5 knowledge index.

Usage: python scripts/build_index.py

The index stores:
- source metadata and per-page provenance
- every knowledge chunk (page-anchored)
- a jieba-tokenised FTS5 table (unicode61) with BM25 ranking
- structured herb monographs parsed from 中药学
- alias table for query normalisation
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import jieba

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CHUNKS_DIR,
    CONFIG,
    DATA,
    INDEX_DIR,
    PAGES_DIR,
    ROOT,
    book_path,
    load_books,
    load_json,
    sha256_file,
)

jieba.setLogLevel(20)
DB = INDEX_DIR / "knowledge.sqlite"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

DROP TABLE IF EXISTS chunks_fts;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS pages;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS herbs;
DROP TABLE IF EXISTS aliases;
DROP TABLE IF EXISTS meta;

CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  short_title TEXT,
  title TEXT,
  author TEXT,
  publisher TEXT,
  year TEXT,
  edition TEXT,
  isbn TEXT,
  kind TEXT,
  pdf_path TEXT,
  sha256 TEXT,
  page_count INTEGER,
  pages_extracted INTEGER,
  chunks INTEGER,
  imported_at TEXT
);

CREATE TABLE pages (
  source_id TEXT,
  pdf_page INTEGER,
  printed_page INTEGER,
  method TEXT,
  confidence TEXT,
  mean_score REAL,
  chars INTEGER,
  warnings TEXT,
  text TEXT,
  PRIMARY KEY (source_id, pdf_page)
);

CREATE TABLE chunks (
  rowid INTEGER PRIMARY KEY,
  chunk_id TEXT UNIQUE,
  source_id TEXT,
  book_title TEXT,
  short_title TEXT,
  chapter TEXT,
  section TEXT,
  printed_page INTEGER,
  pdf_page INTEGER,
  page_kind TEXT,
  content_type TEXT,
  content TEXT,
  keywords TEXT,
  related_ingredients TEXT,
  confidence TEXT,
  extraction_method TEXT,
  ocr_mean_score REAL,
  warnings TEXT,
  char_len INTEGER,
  citation TEXT
);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
  content_seg,
  keywords_seg,
  ingredients_seg,
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TABLE herbs (
  name TEXT PRIMARY KEY,
  pinyin TEXT,
  classical_source TEXT,
  nature_flavor_meridians TEXT,
  efficacy TEXT,
  applications TEXT,
  usage_dosage TEXT,
  cautions TEXT,
  modern_research TEXT,
  chemistry TEXT,
  pharmacology TEXT,
  adverse_reactions TEXT,
  pdf_start INTEGER,
  pdf_end INTEGER,
  confidence TEXT,
  is_attached INTEGER,
  raw_excerpt TEXT
);

CREATE TABLE aliases (
  alias TEXT,
  canonical TEXT,
  kind TEXT,
  source_id TEXT,
  pdf_page INTEGER
);

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""


def seg(text: str) -> str:
    if not text:
        return ""
    tokens = [t.strip() for t in jieba.cut_for_search(text) if t.strip()]
    return " ".join(dict.fromkeys(tokens))


def main() -> None:
    import time

    t0 = time.time()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    books = load_books()
    total_chunks = 0
    for b in books:
        sid = b["source_id"]
        chunk_file = CHUNKS_DIR / f"{sid}.jsonl"
        if not chunk_file.exists():
            print(f"skip {sid}: no chunks")
            continue
        chunks = [json.loads(line) for line in open(chunk_file, encoding="utf-8")]
        page_file = PAGES_DIR / f"{sid}.ocr.jsonl"
        if not page_file.exists():
            page_file = PAGES_DIR / f"{sid}.jsonl"
        pages = [json.loads(line) for line in open(page_file, encoding="utf-8")] if page_file.exists() else []
        pdf = book_path(b)
        try:
            digest = sha256_file(pdf)
        except FileNotFoundError:
            digest = ""
        con.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                b["short_title"],
                b["title"],
                b["author"],
                b.get("publisher"),
                b.get("year"),
                b.get("edition"),
                b.get("isbn"),
                b["kind"],
                b["file"],
                digest,
                len(pages),
                len(pages),
                len(chunks),
                time.strftime("%Y-%m-%dT%H:%M:%S"),
            ),
        )
        for p in pages:
            printed = p.get("printed_page")
            if printed and abs(printed - p["pdf_page"]) > 300:
                printed = None
            con.execute(
                "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    p["pdf_page"],
                    printed,
                    p.get("method"),
                    "high" if p.get("method") == "text_layer" else ("medium" if (p.get("mean_score") or 0) >= 0.72 else "low"),
                    p.get("mean_score"),
                    len(p.get("text") or ""),
                    json.dumps(p.get("warnings") or [], ensure_ascii=False),
                    p.get("text") or "",
                ),
            )
        for c in chunks:
            cur = con.execute(
                "INSERT INTO chunks (chunk_id,source_id,book_title,short_title,chapter,section,printed_page,pdf_page,"
                "page_kind,content_type,content,keywords,related_ingredients,confidence,extraction_method,"
                "ocr_mean_score,warnings,char_len,citation) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    c["chunk_id"],
                    c["source_id"],
                    c["book_title"],
                    c["short_title"],
                    c.get("chapter"),
                    c.get("section"),
                    c.get("printed_page"),
                    c["pdf_page"],
                    c.get("page_kind"),
                    c.get("content_type"),
                    c["content"],
                    json.dumps(c.get("keywords") or [], ensure_ascii=False),
                    json.dumps(c.get("related_ingredients") or [], ensure_ascii=False),
                    c.get("confidence"),
                    c.get("extraction_method"),
                    c.get("ocr_mean_score"),
                    json.dumps(c.get("warnings") or [], ensure_ascii=False),
                    c.get("char_len", len(c["content"])),
                    c.get("citation"),
                ),
            )
            rowid = cur.lastrowid
            con.execute(
                "INSERT INTO chunks_fts (rowid, content_seg, keywords_seg, ingredients_seg) VALUES (?,?,?,?)",
                (
                    rowid,
                    seg(c["content"]),
                    seg(" ".join(c.get("keywords") or [])),
                    seg(" ".join(c.get("related_ingredients") or [])),
                ),
            )
        total_chunks += len(chunks)
        print(f"{sid}: pages={len(pages)} chunks={len(chunks)}")

    herbs_file = DATA / "herbs.jsonl"
    if herbs_file.exists():
        n = 0
        for line in open(herbs_file, encoding="utf-8"):
            h = json.loads(line)
            con.execute(
                "INSERT OR REPLACE INTO herbs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    h["name"],
                    h.get("pinyin"),
                    h.get("classical_source"),
                    h.get("nature_flavor_meridians"),
                    h.get("efficacy"),
                    h.get("applications"),
                    h.get("usage_dosage"),
                    h.get("cautions"),
                    h.get("modern_research"),
                    h.get("chemistry"),
                    h.get("pharmacology"),
                    h.get("adverse_reactions"),
                    h.get("pdf_start"),
                    h.get("pdf_end"),
                    h.get("confidence"),
                    1 if h.get("is_attached") else 0,
                    h.get("raw_excerpt"),
                ),
            )
            n += 1
        print(f"herbs: {n}")

    lex = load_json(CONFIG / "ingredient_lexicon.json", {"entries": []})
    for e in lex.get("entries", []):
        for ev in e.get("evidence") or [{}]:
            con.execute(
                "INSERT INTO aliases VALUES (?,?,?,?,?)",
                (
                    e["canonical"],
                    e["canonical"],
                    e.get("alias_kind"),
                    ev.get("source_id"),
                    ev.get("pdf_page"),
                ),
            )
        for a in e.get("aliases", []):
            con.execute(
                "INSERT INTO aliases VALUES (?,?,?,?,?)",
                (a, e["canonical"], e.get("alias_kind"), None, None),
            )
    con.execute("INSERT INTO meta VALUES ('chunks', ?)", (str(total_chunks),))
    con.execute("INSERT INTO meta VALUES ('built_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%S"),))
    con.commit()
    con.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('optimize')")
    con.commit()
    con.close()
    print(f"index built: {DB} chunks={total_chunks} in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
