"""Validate the ten-book knowledge base and write data/manifest.json.

Checks are deliberately concrete: file presence, page counts, citation/page
agreement, FTS/chunk parity, herb record integrity, ingredient-card schema
validity, and verbatim quote existence.  A failed check exits non-zero.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CHUNKS_DIR,
    DATA,
    INDEX_DIR,
    PAGES_DIR,
    ROOT,
    book_path,
    format_citation,
    load_books,
    load_json,
    read_jsonl,
    save_json,
)

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover
    Draft202012Validator = None  # type: ignore


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

PHASE1 = ["MM-ZYX-2016", "CN-DIDAO-2011", "FS-SFAH-2023", "DK-INGREDIENTS"]
PHASE2 = ["MCG-V1-2013", "MCG-V2-2013", "MCG-V3-2013", "FC-BELITZ-2009", "FB-PAGE-2008", "CR-WXY-2003"]

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name} :: {detail}")
        FAILURES.append(f"{name}: {detail}")


def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    books = load_books()
    by_id = {b["source_id"]: b for b in books}
    hashes = load_json(ROOT / "config" / "book_hashes.json", {})
    page_cache: dict[str, dict[int, dict[str, Any]]] = {}
    book_stats: list[dict[str, Any]] = []

    print("== 1. 原始文件与哈希 ==")
    for b in books:
        sid = b["source_id"]
        path = book_path(b)
        check(f"{sid} 文件存在", path.exists(), str(path))
        if not path.exists():
            continue
        expected = hashes.get(sid, {})
        if expected.get("bytes"):
            check(f"{sid} 文件大小", path.stat().st_size == expected["bytes"], f"{path.stat().st_size} != {expected['bytes']}")
        if expected.get("sha256"):
            actual = sha256(path)
            check(f"{sid} SHA-256", actual == expected["sha256"], actual)

    print("== 2. 页级记录 ==")
    for b in books:
        sid = b["source_id"]
        path = PAGE_FILES.get(sid)
        check(f"{sid} 页文件存在", bool(path and path.exists()), str(path))
        if not path or not path.exists():
            continue
        rows = list(read_jsonl(path))
        expected_pages = hashes.get(sid, {}).get("pages")
        check(f"{sid} 页数", expected_pages is None or len(rows) == expected_pages, f"{len(rows)} != {expected_pages}")
        pages = sorted(r.get("pdf_page") for r in rows)
        check(f"{sid} 页号连续", pages == list(range(1, len(rows) + 1)), f"first={pages[:3]} last={pages[-3:]}")
        bad_printed = []
        empty_pages = 0
        low_conf_pages = 0
        for r in rows:
            text = r.get("text") or ""
            if len(text.strip()) < 20:
                empty_pages += 1
            pp = r.get("printed_page")
            if pp is not None:
                if not isinstance(pp, int) or pp < 1 or abs(pp - r["pdf_page"]) > 400:
                    bad_printed.append((r["pdf_page"], pp))
            score = r.get("mean_score")
            if score is not None and score < 0.72:
                low_conf_pages += 1
        check(f"{sid} printed_page 合理", not bad_printed, str(bad_printed[:5]))
        page_cache[sid] = {r["pdf_page"]: r for r in rows}
        book_stats.append(
            {
                "source_id": sid,
                "title": b["title"],
                "pages": len(rows),
                "near_empty_pages": empty_pages,
                "low_confidence_pages": low_conf_pages,
                "printed_page_observed": sum(1 for r in rows if r.get("printed_page")),
            }
        )

    phase1_pages = sum(x["pages"] for x in book_stats if x["source_id"] in PHASE1)
    phase2_pages = sum(x["pages"] for x in book_stats if x["source_id"] in PHASE2)
    check("第一阶段 4 书页记录基线 1975", phase1_pages == 1975, f"{phase1_pages} != 1975")
    check("第二阶段 6 书页记录非空", phase2_pages > 0, str(phase2_pages))

    print("== 3. 知识片段与引用 ==")
    chunk_rows: list[dict[str, Any]] = []
    for b in books:
        sid = b["source_id"]
        path = CHUNKS_DIR / f"{sid}.jsonl"
        check(f"{sid} chunk 文件存在", path.exists(), str(path))
        if not path.exists():
            continue
        rows = list(read_jsonl(path))
        chunk_rows.extend(rows)
        check(f"{sid} chunk 非空", len(rows) > 0, "0 chunks")
        bad_page = [r["chunk_id"] for r in rows if not (1 <= r.get("pdf_page", 0) <= len(page_cache.get(sid, {})))]
        check(f"{sid} chunk 页码在范围内", not bad_page, str(bad_page[:5]))
        bad_citation = []
        bad_len = []
        for r in rows:
            rec = {
                "short_title": r.get("short_title"),
                "printed_page": r.get("printed_page"),
                "pdf_page": r.get("pdf_page"),
            }
            expected = format_citation(rec)
            if r.get("citation") != expected:
                bad_citation.append((r["chunk_id"], r.get("citation"), expected))
            if r.get("char_len") != len(r.get("content") or ""):
                bad_len.append(r["chunk_id"])
        check(f"{sid} citation 与页码字段一致", not bad_citation, str(bad_citation[:3]))
        check(f"{sid} char_len 一致", not bad_len, str(bad_len[:5]))
        check(f"{sid} chunk 内容非空", all((r.get("content") or "").strip() for r in rows), "empty content found")
        for r in rows:
            pp = r.get("printed_page")
            if pp is not None and abs(pp - r["pdf_page"]) > 400:
                check(f"{sid} chunk printed_page 合理", False, f"{r['chunk_id']} p{pp}")
                break

    total_chunks = len(chunk_rows)
    phase1_chunks = sum(1 for r in chunk_rows if r["source_id"] in PHASE1)
    phase2_chunks = sum(1 for r in chunk_rows if r["source_id"] in PHASE2)
    check("第一阶段 4 书 chunk 基线 2589", phase1_chunks == 2589, f"{phase1_chunks} != 2589")
    check("第二阶段 6 书 chunk 非空", phase2_chunks > 0, str(phase2_chunks))
    check("全库 chunk 总数 = 各书之和", total_chunks == phase1_chunks + phase2_chunks, str(total_chunks))

    print("== 4. SQLite 索引 ==")
    db = INDEX_DIR / "knowledge.sqlite"
    check("SQLite 存在", db.exists(), str(db))
    db_counts: dict[str, int] = {}
    if db.exists():
        con = sqlite3.connect(db)
        try:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            check("SQLite integrity_check", integrity == "ok", integrity)
            for table in (
                "pages", "chunks", "chunks_fts", "herbs", "aliases", "sources",
                "flavor_pairings", "flavor_affinities", "chemistry_topics",
                "culinary_sections", "conflict_candidates",
            ):
                n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                db_counts[table] = n
            check("pages 行数 = 页记录总数", db_counts["pages"] == sum(len(v) for v in page_cache.values()), str(db_counts))
            check("chunks 行数 = chunk 文件总数", db_counts["chunks"] == total_chunks, f"{db_counts['chunks']} != {total_chunks}")
            check("FTS 行数 = chunks", db_counts["chunks_fts"] == db_counts["chunks"], str(db_counts))
            check("sources = 10", db_counts["sources"] == 10, str(db_counts["sources"]))
            check("flavor_pairings 非空", db_counts["flavor_pairings"] > 0, str(db_counts["flavor_pairings"]))
            check("flavor_affinities 非空", db_counts["flavor_affinities"] > 0, str(db_counts["flavor_affinities"]))
            check("chemistry_topics 非空", db_counts["chemistry_topics"] > 0, str(db_counts["chemistry_topics"]))
            check("culinary_sections 非空", db_counts["culinary_sections"] > 0, str(db_counts["culinary_sections"]))
            bad_levels = con.execute(
                "SELECT COUNT(*) FROM flavor_pairings WHERE evidence_level NOT IN "
                "('explicit_pairing_listing','explicit_affinity_combination',"
                "'derived_from_affinity_combination','ai_hypothesis')"
            ).fetchone()[0]
            check("flavor_pairings evidence_level 合法", bad_levels == 0, str(bad_levels))
            bad_pair_pages = con.execute(
                "SELECT COUNT(*) FROM flavor_pairings p LEFT JOIN pages g "
                "ON g.source_id=p.source_id AND g.pdf_page=p.pdf_page WHERE g.pdf_page IS NULL"
            ).fetchone()[0]
            check("flavor_pairings 页码均存在", bad_pair_pages == 0, str(bad_pair_pages))
            bad_topic_pages = con.execute(
                "SELECT COUNT(*) FROM chemistry_topics t LEFT JOIN pages g "
                "ON g.source_id=t.source_id AND g.pdf_page=t.pdf_page WHERE g.pdf_page IS NULL"
            ).fetchone()[0]
            check("chemistry_topics 页码均存在", bad_topic_pages == 0, str(bad_topic_pages))
        finally:
            con.close()

    print("== 5. 本草结构化记录 ==")
    herbs_path = DATA / "herbs.jsonl"
    check("herbs.jsonl 存在", herbs_path.exists(), str(herbs_path))
    herbs = list(read_jsonl(herbs_path)) if herbs_path.exists() else []
    main_herbs = [h for h in herbs if not h.get("is_attached")]
    attached = [h for h in herbs if h.get("is_attached")]
    check("herbs 总数 558", len(herbs) == 558, str(len(herbs)))
    check("主条目 434", len(main_herbs) == 434, str(len(main_herbs)))
    check("附药 124", len(attached) == 124, str(len(attached)))
    bad_main = []
    for h in main_herbs:
        if not h.get("name") or not h.get("efficacy") or not h.get("applications") or not h.get("usage_dosage"):
            bad_main.append(h.get("name"))
        if not (1 <= h.get("pdf_start", 0) <= h.get("pdf_end", 0) <= 841):
            bad_main.append(h.get("name") + ":page")
    check("主条目字段完整/页码合理", not bad_main, str(bad_main[:8]))
    check("主条目功效覆盖率 100%", sum(1 for h in main_herbs if h.get("efficacy")) == len(main_herbs))

    herb_index = ROOT / "references" / "materia-medica" / "herb-index.md"
    check("herb-index.md 存在", herb_index.exists(), str(herb_index))
    if herb_index.exists():
        rows = [
            line for line in herb_index.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\| .+ \| \d+ \|$", line)
        ]
        check("herb-index 行数 = 434", len(rows) == 434, str(len(rows)))

    print("== 6. 食材卡与引文回查 ==")
    schema_path = ROOT / "schemas" / "ingredient.schema.json"
    schema = load_json(schema_path)
    check("ingredient.schema.json 存在", bool(schema), str(schema_path))
    validator = Draft202012Validator(schema) if schema and Draft202012Validator else None
    old_cards = sorted((DATA / "ingredients").glob("*.json"))
    old_cards = [p for p in old_cards if not p.name.startswith("_")]
    new_cards = sorted((DATA / "ingredients-phase2").glob("*.json"))
    new_cards = [p for p in new_cards if not p.name.startswith("_")]
    cards = old_cards + new_cards
    check("第一阶段食材卡数量 12", len(old_cards) == 12, str(len(old_cards)))
    check("第二阶段食材卡数量 6", len(new_cards) == 6, str(len(new_cards)))
    bad_schema = []
    bad_quote = []
    bad_page = []
    bad_tcm_note = []
    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        if validator is not None and not validator.is_valid(card):
            bad_schema.append(path.name)
        for e in card.get("sources", []):
            sid = e.get("source_id")
            page = e.get("pdf_page")
            rec = page_cache.get(sid, {}).get(page)
            if rec is None:
                bad_page.append(f"{path.name}:{sid}:{page}")
                continue
            if norm(e.get("quote", "")) not in norm(rec.get("text", "")):
                bad_quote.append(f"{path.name}:{sid}:{page}:{e.get('quote', '')[:30]}")
            if e.get("printed_page") != rec.get("printed_page"):
                bad_page.append(f"{path.name}:{sid}:{page}:printed")
        if card.get("tcm_attributes", {}).get("applicable"):
            note = card["tcm_attributes"].get("notes") or ""
            if "传统理论" not in note and "不是现代医学证据" not in note and "非现代医学证据" not in note:
                bad_tcm_note.append(path.name)
    check("食材卡通过 JSON Schema", not bad_schema, str(bad_schema))
    check("食材卡引文均回查命中", not bad_quote, str(bad_quote[:6]))
    check("食材卡页码/印刷页一致", not bad_page, str(bad_page[:6]))
    check("本草属性带传统理论声明", not bad_tcm_note, str(bad_tcm_note))

    print("== 7. 图像、整页扫描与表格候选 ==")
    visual_manifest = DATA / "images" / "manifest.jsonl"
    visual_stats_path = DATA / "images" / "stats.json"
    check("视觉清单存在", visual_manifest.exists(), str(visual_manifest))
    visual_rows = list(read_jsonl(visual_manifest)) if visual_manifest.exists() else []
    check("视觉清单非空", len(visual_rows) > 0, "0 visuals")
    bad_visual_page = []
    bad_visual_printed = []
    bad_visual_status = []
    allowed_status = {
        "needs_human_review",
        "no_nearby_text_needs_review",
        "page_scan_text_excerpt",
    }
    for r in visual_rows:
        rec = page_cache.get(r.get("source_id"), {}).get(r.get("pdf_page"))
        if rec is None:
            bad_visual_page.append(r.get("visual_id"))
        elif r.get("printed_page") != rec.get("printed_page"):
            bad_visual_printed.append(r.get("visual_id"))
        if r.get("caption_status") not in allowed_status:
            bad_visual_status.append(r.get("visual_id"))
    check("视觉记录页码存在", not bad_visual_page, str(bad_visual_page[:5]))
    check("视觉记录 printed_page 与页记录一致", not bad_visual_printed, str(bad_visual_printed[:5]))
    check("图注候选均标记待审/无图注", not bad_visual_status, str(bad_visual_status[:5]))
    visual_stats = load_json(visual_stats_path, {})
    check("视觉统计文件存在", bool(visual_stats), str(visual_stats_path))
    check("视觉统计 records 与清单一致", visual_stats.get("records") == len(visual_rows), f"{visual_stats.get('records')} != {len(visual_rows)}")

    print("== 8. 必需参考文件 ==")
    required = [
        "SKILL.md",
        "README.md",
        "references/knowledge-index/citation-policy.md",
        "references/knowledge-index/search-guide.md",
        "references/knowledge-index/books.md",
        "references/knowledge-index/coverage.md",
        "data/images/manifest.jsonl",
        "data/images/README.md",
        "scripts/extract_visuals.py",
        "references/materia-medica/README.md",
        "references/materia-medica/herb-index.md",
        "references/chinese-ingredients/README.md",
        "references/chinese-ingredients/index.md",
        "references/global-ingredients/README.md",
        "references/global-ingredients/index.md",
        "references/flavor-science/README.md",
        "references/flavor-science/salt.md",
        "references/flavor-science/fat.md",
        "references/flavor-science/acid.md",
        "references/flavor-science/heat.md",
        "references/flavor-science/balance.md",
        "references/food-chemistry/README.md",
        "references/food-chemistry/topics.md",
        "references/food-chemistry/limitations-2009.md",
        "references/flavor-pairing/README.md",
        "references/flavor-pairing/index.md",
        "references/flavor-pairing/evidence-policy.md",
        "references/culinary-ingredients/README.md",
        "references/food-and-cooking/README.md",
        "workflows/01-ingredient-deep-dive.md",
        "workflows/02-ingredient-comparison.md",
        "workflows/03-pairing-analysis.md",
        "workflows/04-flavor-science.md",
        "workflows/05-recipe-development.md",
        "workflows/06-recipe-optimization.md",
        "workflows/07-innovation-design.md",
        "workflows/08-topic-research.md",
        "evals/rubric.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    check("必需文件齐全", not missing, str(missing))

    print("== 9. 汇总 ==")
    totals = {
        "pages": sum(v["pages"] for v in book_stats),
        "chunks": total_chunks,
        "herbs": len(herbs),
        "main_herbs": len(main_herbs),
        "attached_herbs": len(attached),
        "ingredient_cards": len(cards),
        "phase1_ingredient_cards": len(old_cards),
        "phase2_ingredient_cards": len(new_cards),
        "phase1_pages": phase1_pages,
        "phase2_pages": phase2_pages,
        "phase1_chunks": phase1_chunks,
        "phase2_chunks": phase2_chunks,
        "sources": len(books),
        "flavor_pairings": db_counts.get("flavor_pairings", 0),
        "flavor_affinities": db_counts.get("flavor_affinities", 0),
        "chemistry_topics": db_counts.get("chemistry_topics", 0),
        "culinary_sections": db_counts.get("culinary_sections", 0),
        "visual_records": len(visual_rows),
        "content_images": visual_stats.get("images", 0),
        "page_scans": visual_stats.get("page_scans", 0),
        "table_candidates": visual_stats.get("table_candidates", 0),
    }
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "knowledge_base": "ten-book-v2",
        "books": book_stats,
        "totals": totals,
        "database": db_counts,
        "visuals": visual_stats,
        "checks": {"total": CHECKS, "failed": len(FAILURES), "failures": FAILURES},
    }
    save_json(DATA / "manifest.json", manifest)
    print(json.dumps({"totals": totals, "checks": CHECKS, "failed": len(FAILURES)}, ensure_ascii=False, indent=2))
    if FAILURES:
        print("\nFAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
