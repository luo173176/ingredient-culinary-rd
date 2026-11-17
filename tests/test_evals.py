from __future__ import annotations

import json


def test_there_are_thirty_eval_cases_covering_required_types(skill_root: Path) -> None:
    cases = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((skill_root / "evals" / "cases").glob("E*.json"))
    ]
    assert len(cases) == 30
    assert {c["id"] for c in cases} == {f"E{i:02d}" for i in range(1, 31)}
    types = {c["type"] for c in cases}
    assert {
        "single_ingredient",
        "comparison",
        "pairing",
        "flavor_science",
        "herb_culinary_cross",
        "multi_book_cross",
        "gap",
        "page_accuracy",
        "medical_boundary",
        "alias",
        "food_chemistry",
        "ingredient_research",
        "flavor_pairing",
        "comprehensive_rd",
    } <= types
    for c in cases:
        assert c["question"]
        assert c["expected_points"]
        assert c["manual_checks"]
        assert c["search_queries"]
        assert c.get("reference_answer")
        assert c["question"].strip() != c["reference_answer"].strip()


def test_phase1_and_phase2_case_groups_are_preserved(skill_root: Path) -> None:
    cases = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((skill_root / "evals" / "cases").glob("E*.json"))
    }
    assert {cases[f"E{i:02d}"]["type"] for i in range(1, 11)} == {
        "single_ingredient",
        "comparison",
        "pairing",
        "flavor_science",
        "herb_culinary_cross",
        "multi_book_cross",
        "gap",
        "page_accuracy",
        "medical_boundary",
        "alias",
    }
    assert {cases[f"E{i:02d}"]["type"] for i in range(11, 16)} == {"food_chemistry"}
    assert {cases[f"E{i:02d}"]["type"] for i in range(16, 21)} == {"ingredient_research"}
    assert {cases[f"E{i:02d}"]["type"] for i in range(21, 26)} == {"flavor_pairing"}
    assert {cases[f"E{i:02d}"]["type"] for i in range(26, 31)} == {"comprehensive_rd"}


def test_latest_eval_results_are_all_passing_on_automated_checks(skill_root: Path) -> None:
    latest = json.loads((skill_root / "evals" / "results" / "latest.json").read_text(encoding="utf-8"))
    assert latest["knowledge_base"] == "ten-book-v2"
    assert latest["summary"]["cases"] == 30
    assert latest["summary"]["auto_passed"] == 30
    assert latest["summary"]["citation_hard_errors"] == 0
    assert not latest["summary"]["hard_failures"]
    assert all(c["auto_passed"] for c in latest["cases"])
    assert all(c["professional_correctness"]["status"] == "manual_pending" for c in latest["cases"])
    assert latest["summary"]["auto_max"] == 2700


def test_gap_and_safety_cases_are_explicit(skill_root: Path) -> None:
    cases = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((skill_root / "evals" / "cases").glob("E*.json"))
    }
    assert cases["E07"]["gap_expected"] is True
    assert cases["E09"]["gap_expected"] is True
    assert cases["E09"]["safety_required"] is True
    assert "暂无充分依据" in cases["E07"]["reference_answer"]
    assert "不提供个体化剂量" in cases["E09"]["reference_answer"]

