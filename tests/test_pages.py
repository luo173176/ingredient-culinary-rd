from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from common import PAGES_DIR, format_citation, load_json


EXPECTED = {
    "MM-ZYX-2016": ("MM-ZYX-2016.jsonl", 841),
    "CN-DIDAO-2011": ("CN-DIDAO-2011.ocr.jsonl", 239),
    "FS-SFAH-2023": ("FS-SFAH-2023.jsonl", 364),
    "DK-INGREDIENTS": ("DK-INGREDIENTS.ocr.jsonl", 531),
}


def test_four_page_files_and_continuity(skill_root: Path) -> None:
    for sid, (filename, expected_pages) in EXPECTED.items():
        rows = [json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8")]
        assert len(rows) == expected_pages, sid
        assert [r["pdf_page"] for r in rows] == list(range(1, expected_pages + 1)), sid
        assert all("text" in r for r in rows), sid
    assert sum(
        1
        for filename, _ in EXPECTED.values()
        for r in (json.loads(line) for line in (PAGES_DIR / filename).open(encoding="utf-8"))
        if len((r.get("text") or "").strip()) >= 20
    ) >= 1901


def test_printed_and_pdf_pages_are_distinct_fields(skill_root: Path) -> None:
    hashes = load_json(skill_root / "config" / "book_hashes.json", {})
    assert hashes["DK-INGREDIENTS"]["pages"] == 531
    assert hashes["CN-DIDAO-2011"]["pages"] == 239

    cn = [
        json.loads(line)
        for line in (PAGES_DIR / "CN-DIDAO-2011.ocr.jsonl").open(encoding="utf-8")
    ]
    observed = [r for r in cn if r.get("printed_page")]
    assert observed, "no printed page numbers observed in the scanned Chinese book"
    assert all(isinstance(r["printed_page"], int) and r["printed_page"] != r["pdf_page"] for r in observed)

    # Digital books have no reliable printed page in the text layer.
    fs = [
        json.loads(line)
        for line in (PAGES_DIR / "FS-SFAH-2023.jsonl").open(encoding="utf-8")
    ]
    assert all(r.get("printed_page") is None for r in fs)


def test_no_outlier_printed_pages(skill_root: Path) -> None:
    for sid, (filename, _) in EXPECTED.items():
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
    assert format_citation(scanned) == "《中国地道食材图录大全》p.36（PDF 40）"
    assert format_citation(digital) == "《中药学》PDF 396（电子版无印刷页码）"


def test_database_page_and_chunk_counts(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 1975
        assert con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 2589
        assert con.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 2589
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 4
    finally:
        con.close()
