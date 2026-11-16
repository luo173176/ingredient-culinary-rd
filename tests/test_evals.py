from __future__ import annotations

import json
from pathlib import Path


def test_there_are_ten_eval_cases_covering_the_required_types(skill_root: Path) -> None:
    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((skill_root / "evals" / "cases").glob("E*.json"))]
    assert len(cases) == 10
    types = {c["type"] for c in cases}
    assert {
        "single_ingredient", "comparison", "pairing", "flavor_science",
        "herb_culinary_cross", "multi_book_cross", "gap", "page_accuracy",
        "medical_boundary", "alias",
    } <= types
    for c in cases:
        assert c["question"]
        assert c["expected_points"]
        assert c["manual_checks"]
        assert c["search_queries"]


def test_latest_eval_results_are_all_passing_on_automated_checks(skill_root: Path) -> None:
    latest = json.loads((skill_root / "evals" / "results" / "latest.json").read_text(encoding="utf-8"))
    assert latest["summary"]["cases"] == 10
    assert latest["summary"]["auto_passed"] == 10
    assert latest["summary"]["citation_hard_errors"] == 0
    assert not latest["summary"]["hard_failures"]
    assert all(c["auto_passed"] for c in latest["cases"])
    assert all(c["professional_correctness"]["status"] == "manual_pending" for c in latest["cases"])
