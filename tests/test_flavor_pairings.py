from __future__ import annotations

import json
import sqlite3

from jsonschema import Draft202012Validator


def test_flavor_pairing_extraction_stats_match_raw_files(skill_root) -> None:
    stats = json.loads((skill_root / "data" / "flavor_pairing_stats.json").read_text(encoding="utf-8"))
    assert stats["source_id"] == "FB-PAGE-2008"
    assert stats["pages_processed"] == 391
    assert stats["entries"] == 640
    assert stats["pairings"] == 14090
    assert stats["direct_pairings"] == 13503
    assert stats["derived_pairings"] == 587
    assert stats["affinities"] == 292
    assert stats["review_queue"] == 6905
    assert stats["strong_marker_candidates"] == 493

    n = sum(1 for _ in (skill_root / "data" / "flavor_pairings.jsonl").open(encoding="utf-8"))
    assert n == stats["pairings"]
    nq = sum(1 for _ in (skill_root / "data" / "flavor_review_queue.jsonl").open(encoding="utf-8"))
    assert nq == stats["review_queue"]


def test_flavor_pairing_db_is_deduplicated_and_levels_are_valid(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        total = con.execute("SELECT COUNT(*) FROM flavor_pairings").fetchone()[0]
        assert total == 13758
        rows = dict(
            con.execute(
                "SELECT evidence_level, COUNT(*) FROM flavor_pairings GROUP BY evidence_level"
            ).fetchall()
        )
        assert rows["explicit_pairing_listing"] == 13503
        assert rows["derived_from_affinity_combination"] == 255
        assert set(rows) <= {
            "explicit_pairing_listing",
            "explicit_affinity_combination",
            "derived_from_affinity_combination",
            "ai_hypothesis",
        }
        assert con.execute(
            "SELECT COUNT(*) FROM flavor_affinities"
        ).fetchone()[0] == 292
        assert con.execute(
            "SELECT COUNT(*) FROM flavor_pairings p LEFT JOIN pages g "
            "ON g.source_id=p.source_id AND g.pdf_page=p.pdf_page WHERE g.pdf_page IS NULL"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_flavor_pairing_records_schema_and_required_fields(skill_root) -> None:
    schema = json.loads(
        (skill_root / "schemas" / "flavor-pairing.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    path = skill_root / "data" / "flavor_pairings.jsonl"
    checked = 0
    for i, line in enumerate(path.open(encoding="utf-8")):
        row = json.loads(line)
        assert row["ingredient_a"].strip()
        assert row["ingredient_b"].strip()
        assert row["source_id"] == "FB-PAGE-2008"
        assert row["printed_page"] is not None
        if i % 100 == 0:
            assert validator.is_valid(row), row["pairing_id"]
            checked += 1
    assert checked >= 100


def test_verified_flavor_pairing_examples(db_path) -> None:
    con = sqlite3.connect(db_path)
    try:
        basil = con.execute(
            "SELECT COUNT(*), MIN(pdf_page), MAX(pdf_page) FROM flavor_pairings "
            "WHERE ingredient_a='BASIL'"
        ).fetchone()
        assert basil[0] == 72
        assert basil[1:] == (73, 74)
        assert con.execute(
            "SELECT COUNT(*) FROM flavor_pairings WHERE ingredient_a='CHICKEN' AND pdf_page=130"
        ).fetchone()[0] == 61
        assert con.execute(
            "SELECT COUNT(*) FROM flavor_pairings WHERE ingredient_a='BANANAS' AND printed_page=56"
        ).fetchone()[0] >= 20
        assert con.execute(
            "SELECT COUNT(*) FROM flavor_pairings WHERE strong_marker != 'none'"
        ).fetchone()[0] == 493
    finally:
        con.close()

