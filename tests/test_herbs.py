from __future__ import annotations

import json
import re
from pathlib import Path


def load_herbs(skill_root: Path):
    path = skill_root / "data" / "herbs.jsonl"
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def test_herb_counts_and_main_field_completeness(skill_root: Path) -> None:
    rows = load_herbs(skill_root)
    main = [h for h in rows if not h.get("is_attached")]
    attached = [h for h in rows if h.get("is_attached")]
    assert len(rows) == 558
    assert len(main) == 434
    assert len(attached) == 124
    assert sum(1 for h in rows if h.get("efficacy")) == 436
    for h in main:
        assert h["efficacy"] and h["applications"] and h["usage_dosage"], h["name"]
        assert 1 <= h["pdf_start"] <= h["pdf_end"] <= 841, h["name"]


def test_huajiao_fields(skill_root: Path) -> None:
    h = next(x for x in load_herbs(skill_root) if x["name"] == "花椒")
    assert "辛,温" in h["nature_flavor_meridians"]
    assert "温中止痛,杀虫止痒" in h["efficacy"]
    assert "生姜" in h["applications"]
    assert "3~6g" in h["usage_dosage"]
    assert h["pdf_start"] == 396
    assert h["confidence"] == "high"


def test_chenpi_has_cautions_not_empty(skill_root: Path) -> None:
    h = next(x for x in load_herbs(skill_root) if x["name"] == "陈皮")
    assert h["efficacy"].startswith("理气健脾")
    assert "内有实热" in h["cautions"]


def test_two_medium_confidence_entries_are_marked(skill_root: Path) -> None:
    rows = load_herbs(skill_root)
    medium = sorted(h["name"] for h in rows if not h.get("is_attached") and h["confidence"] == "medium")
    assert medium == ["旋覆花", "苏木"]
    assert all(not h["nature_flavor_meridians"] for h in rows if h["name"] in {"旋覆花", "苏木"})


def test_herb_index_has_one_row_per_main_entry(skill_root: Path) -> None:
    text = (skill_root / "references" / "materia-medica" / "herb-index.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if re.match(r"^\| .+ \| \d+ \|$", line)]
    assert len(rows) == 434
