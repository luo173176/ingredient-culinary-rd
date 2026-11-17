from __future__ import annotations

import json
import sqlite3


def test_chemistry_stats_match_raw_index(skill_root) -> None:
    stats = json.loads((skill_root / "data" / "chemistry_topics_stats.json").read_text(encoding="utf-8"))
    assert stats["source_id"] == "FC-BELITZ-2009"
    assert stats["topics"] == 2319
    assert stats["chapters"] == 24
    assert stats["pages_with_topics"] == 863
    n = sum(1 for _ in (skill_root / "data" / "chemistry_topics.jsonl").open(encoding="utf-8"))
    assert n == stats["topics"]


def test_key_chemistry_topics_are_present(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        checks = {
            "%Water Activity%": 47,
            "Gelatinization": 361,
            "%Maillard%": 315,
            "%Peroxidation%": 235,
            "5 Aroma Compounds": 384,
        }
        for pattern, expected_page in checks.items():
            sql = "SELECT COUNT(*) FROM chemistry_topics WHERE topic LIKE ? AND pdf_page=?"
            assert con.execute(sql, (pattern, expected_page)).fetchone()[0] >= 1, pattern
    finally:
        con.close()


def test_chemistry_pages_exist_and_chapters_are_complete(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        assert con.execute("SELECT COUNT(DISTINCT chapter) FROM chemistry_topics").fetchone()[0] == 24
        assert con.execute(
            "SELECT COUNT(*) FROM chemistry_topics t LEFT JOIN pages p "
            "ON p.source_id=t.source_id AND p.pdf_page=t.pdf_page WHERE p.pdf_page IS NULL"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM chemistry_topics WHERE source_id!='FC-BELITZ-2009'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM chemistry_topics WHERE topic IS NULL OR trim(topic)=''"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_printed_page_offset_is_preserved(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT printed_page, pdf_page FROM chemistry_topics "
            "WHERE topic='4.2.4.4.1 Initial Phase of the Maillard Reaction'"
        ).fetchone()
        assert row == (271, 315)
        row = con.execute(
            "SELECT printed_page, pdf_page FROM chemistry_topics WHERE topic='Gelatinization' "
            "ORDER BY pdf_page LIMIT 1"
        ).fetchone()
        assert row == (317, 361)
    finally:
        con.close()

