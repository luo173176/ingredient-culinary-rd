from __future__ import annotations

import json
import sqlite3

from common import PAGES_DIR, format_citation, load_json


PHASE1 = {
    "MM-ZYX-2016": ("MM-ZYX-2016.jsonl", 841),
    "CN-DIDAO-2011": ("CN-DIDAO-2011.ocr.jsonl", 239),
    "FS-SFAH-2023": ("FS-SFAH-2023.jsonl", 364),
    "DK-INGREDIENTS": ("DK-INGREDIENTS.ocr.jsonl", 531),
}

PHASE2 = {
    "MCG-V1-2013": ("MCG-V1-2013.ocr.jsonl", 326),
    "MCG-V2-2013": ("MCG-V2-2013.ocr.jsonl", 363),
    "MCG-V3-2013": ("MCG-V3-2013.ocr.jsonl", 367),
    "FC-BELITZ-2009": ("FC-BELITZ-2009.jsonl", 1114),
    "FB-PAGE-2008": ("FB-PAGE-2008.jsonl", 391),
    "CR-WXY-2003": ("CR-WXY-2003.ocr.jsonl", 244),
}

ALL_BOOKS = {**PHASE1, **PHASE2}


def test_ten_page_files_and_continuity() -> None:
    for sid, (filename, expected_pages) in ALL_BOOKS.items():
        rows = [json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8")]
        assert len(rows) == expected_pages, sid
        assert [r["pdf_page"] for r in rows] == list(range(1, expected_pages + 1)), sid
        assert all("text" in r for r in rows), sid


def test_phase1_page_baseline_preserved() -> None:
    phase1_pages = 0
    phase1_text_pages = 0
    for filename, expected_pages in PHASE1.values():
        rows = [json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8")]
        phase1_pages += len(rows)
        phase1_text_pages += sum(1 for r in rows if len((r.get("text") or "").strip()) >= 20)
        assert len(rows) == expected_pages
    assert phase1_pages == 1975
    assert phase1_text_pages >= 1901


def test_phase2_pages_have_text_and_warnings_are_serialisable() -> None:
    for sid, (filename, _) in PHASE2.items():
        rows = [json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8")]
        assert any((r.get("text") or "").strip() for r in rows), sid
        assert all(isinstance(r.get("warnings") or [], list) for r in rows), sid


def test_printed_and_pdf_pages_are_distinct_fields(skill_root) -> None:
    hashes = load_json(skill_root / "config" / "book_hashes.json", {})
    assert hashes["DK-INGREDIENTS"]["pages"] == 531
    assert hashes["MCG-V3-2013"]["pages"] == 367
    assert hashes["FC-BELITZ-2009"]["pages"] == 1114

    cn = [
        json.loads(line)
        for line in (PAGES_DIR / "CN-DIDAO-2011.ocr.jsonl").open(encoding="utf-8")
    ]
    observed = [r for r in cn if r.get("printed_page")]
    assert observed
    assert all(isinstance(r["printed_page"], int) and r["printed_page"] != r["pdf_page"] for r in observed)

    fs = [
        json.loads(line)
        for line in (PAGES_DIR / "FS-SFAH-2023.jsonl").open(encoding="utf-8")
    ]
    assert all(r.get("printed_page") is None for r in fs)


def test_phase2_printed_page_examples() -> None:
    rows = {
        r["pdf_page"]: r
        for r in (
            json.loads(line)
            for line in (PAGES_DIR / "MCG-V3-2013.ocr.jsonl").open(encoding="utf-8")
        )
    }
    assert rows[348]["printed_page"] == 346
    assert rows[25]["printed_page"] == 23

    fc = {
        r["pdf_page"]: r
        for r in (
            json.loads(line)
            for line in (PAGES_DIR / "FC-BELITZ-2009.jsonl").open(encoding="utf-8")
        )
    }
    assert fc[45]["printed_page"] == 1
    assert fc[315]["printed_page"] == 271

    fb = {
        r["pdf_page"]: r
        for r in (
            json.loads(line)
            for line in (PAGES_DIR / "FB-PAGE-2008.jsonl").open(encoding="utf-8")
        )
    }
    assert fb[73]["printed_page"] == 58


def test_no_outlier_printed_pages() -> None:
    for sid, (filename, _) in ALL_BOOKS.items():
        rows = [json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8")]
        bad = [
            (r["pdf_page"], r.get("printed_page"))
            for r in rows
            if r.get("printed_page") is not None
            and (not isinstance(r["printed_page"], int) or abs(r["printed_page"] - r["pdf_page"]) > 400)
        ]
        assert not bad, f"{sid}: {bad[:5]}"


def test_citation_format_keeps_print_and_pdf_pages_separate() -> None:
    scanned = {"short_title": "中国地道食材图录大全", "printed_page": 36, "pdf_page": 40}
    digital = {"short_title": "中药学", "printed_page": None, "pdf_page": 396}
    phase2 = {"short_title": "食物与厨艺·奶蛋肉鱼", "printed_page": 346, "pdf_page": 348}
    assert format_citation(scanned) == "《中国地道食材图录大全》p.36（PDF 40）"
    assert format_citation(digital) == "《中药学》PDF 396（电子版无印刷页码）"
    assert format_citation(phase2) == "《食物与厨艺·奶蛋肉鱼》p.346（PDF 348）"


def test_database_page_and_chunk_counts(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 4780
        assert con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 6656
        assert con.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 6656
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 10
        assert con.execute(
            "SELECT SUM(chunks) FROM sources WHERE source_id IN "
            "('MM-ZYX-2016','CN-DIDAO-2011','FS-SFAH-2023','DK-INGREDIENTS')"
        ).fetchone()[0] == 2589
        assert con.execute(
            "SELECT SUM(chunks) FROM sources WHERE source_id IN "
            "('MCG-V1-2013','MCG-V2-2013','MCG-V3-2013','FC-BELITZ-2009','FB-PAGE-2008','CR-WXY-2003')"
        ).fetchone()[0] == 4067
    finally:
        con.close()

