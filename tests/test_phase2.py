from __future__ import annotations

import json
import sqlite3

from common import CHUNKS_DIR, PAGES_DIR, load_books, load_json


PHASE2 = {
    "MCG-V1-2013": (326, 396),
    "MCG-V2-2013": (363, 408),
    "MCG-V3-2013": (367, 415),
    "FC-BELITZ-2009": (1114, 1112),
    "FB-PAGE-2008": (391, 1289),
    "CR-WXY-2003": (244, 447),
}

PAGE_FILE = {
    "MCG-V1-2013": "MCG-V1-2013.ocr.jsonl",
    "MCG-V2-2013": "MCG-V2-2013.ocr.jsonl",
    "MCG-V3-2013": "MCG-V3-2013.ocr.jsonl",
    "FC-BELITZ-2009": "FC-BELITZ-2009.jsonl",
    "FB-PAGE-2008": "FB-PAGE-2008.jsonl",
    "CR-WXY-2003": "CR-WXY-2003.ocr.jsonl",
}


def test_phase2_is_registered_as_six_independent_sources(skill_root) -> None:
    books = load_books()
    assert len(books) == 10
    by_id = {b["source_id"]: b for b in books}
    assert set(PHASE2) <= set(by_id)
    assert len({b["source_id"] for b in books}) == 10
    assert all(by_id[sid]["phase"] == 2 for sid in PHASE2)

    for sid in ("MCG-V1-2013", "MCG-V2-2013", "MCG-V3-2013"):
        assert by_id[sid]["series"] == "食物与厨艺"
        assert by_id[sid]["volume"] in {"1", "2", "3"}

    hashes = load_json(skill_root / "config" / "book_hashes.json", {})
    assert set(PHASE2) <= set(hashes)
    for sid, (pages, chunks) in PHASE2.items():
        assert hashes[sid]["pages"] == pages
        assert hashes[sid]["bytes"] > 0
        assert len(hashes[sid]["sha256"]) == 64


def test_phase2_pages_and_chunks_are_complete() -> None:
    for sid, (pages, chunks) in PHASE2.items():
        page_rows = [
            json.loads(line)
            for line in (PAGES_DIR / PAGE_FILE[sid]).open(encoding="utf-8")
        ]
        assert len(page_rows) == pages
        assert [r["pdf_page"] for r in page_rows] == list(range(1, pages + 1))

        chunk_rows = [
            json.loads(line)
            for line in (CHUNKS_DIR / f"{sid}.jsonl").open(encoding="utf-8")
        ]
        assert len(chunk_rows) == chunks
        assert all(r["content"].strip() for r in chunk_rows)
        assert all(1 <= r["pdf_page"] <= pages for r in chunk_rows)
        assert all(r["source_id"] == sid for r in chunk_rows)


def test_phase2_sqlite_rows_are_synchronised(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        for sid, (pages, chunks) in PHASE2.items():
            assert con.execute(
                "SELECT COUNT(*) FROM pages WHERE source_id=?", (sid,)
            ).fetchone()[0] == pages
            assert con.execute(
                "SELECT COUNT(*) FROM chunks WHERE source_id=?", (sid,)
            ).fetchone()[0] == chunks
            assert con.execute(
                "SELECT pages_extracted, chunks FROM sources WHERE source_id=?", (sid,)
            ).fetchone() == (pages, chunks)
    finally:
        con.close()


def test_chapter_maps_cover_observed_phase2_structure(skill_root) -> None:
    maps = load_json(skill_root / "config" / "chapter_maps.json", {})
    for sid in PHASE2:
        assert sid in maps
        assert maps[sid]["chapters"]

    assert [c["chapter"] for c in maps["MCG-V1-2013"]["chapters"]][:2] == [
        "第一章 面包、蛋糕、酥皮和面食",
        "第二章 调味酱料",
    ]
    assert len(maps["CR-WXY-2003"]["chapters"]) == 16
    assert len(maps["FC-BELITZ-2009"]["chapters"]) == 24
    assert maps["FB-PAGE-2008"]["chapters"][0]["chapter"] == "字母序食材条目"
    assert maps["MCG-V2-2013"]["note"].startswith("第三章的章首页")


def test_conflict_candidates_are_review_only_and_traceable(skill_root, db_path) -> None:
    rows = [
        json.loads(line)
        for line in (skill_root / "data" / "conflict_candidates.jsonl").open(encoding="utf-8")
        if line.strip()
    ]
    assert rows
    assert all(r["status"] == "review" for r in rows)
    assert all(r["source_a"] != r["source_b"] for r in rows)
    assert all(r["value_a"] != r["value_b"] for r in rows)

    con = sqlite3.connect(db_path)
    try:
        assert con.execute("SELECT COUNT(*) FROM conflict_candidates").fetchone()[0] == len(rows)
        for row in rows:
            assert con.execute(
                "SELECT COUNT(*) FROM pages WHERE source_id=? AND pdf_page=?",
                (row["source_a"], row["page_a"]),
            ).fetchone()[0] == 1
            assert con.execute(
                "SELECT COUNT(*) FROM pages WHERE source_id=? AND pdf_page=?",
                (row["source_b"], row["page_b"]),
            ).fetchone()[0] == 1
    finally:
        con.close()


def test_rd_cases_use_verified_tarragon_not_rosemary(skill_root) -> None:
    """E26/E27 once claimed CHICKEN + ROSEMARY without page evidence.

    Keep the corrected, page-verifiable TARRAGON -> CHICKEN relationship and
    prevent the generator from reintroducing the unverified claim.
    """
    for cid in ("E26", "E27"):
        case = load_json(skill_root / "evals" / "cases" / f"{cid}.json", {})
        if cid == "E26":
            assert "龙蒿" in case["required_keywords"]
        assert "迷迭香" not in case["reference_answer"]
        assert "TARRAGON" in case["reference_answer"].upper()
        assert {"source_id": "FB-PAGE-2008", "pdf_page": 358} in case["expected_pages"]

    chicken = load_json(skill_root / "data" / "ingredients-phase2" / "chicken.json", {})
    assert chicken["flavor_pairings"] == []
    assert any("搭配候选" in gap and "复核" in gap for gap in chicken["gaps"])

