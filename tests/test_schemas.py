from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


SCHEMAS = [
    "ingredient.schema.json",
    "knowledge-record.schema.json",
    "recipe.schema.json",
    "research-report.schema.json",
    "source.schema.json",
]


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_draft_2020_12(skill_root: Path, name: str) -> None:
    schema = json.loads((skill_root / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"].endswith("2020-12/schema")


def test_all_ingredient_cards_validate(skill_root: Path) -> None:
    schema = json.loads((skill_root / "schemas" / "ingredient.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    cards = sorted((skill_root / "data" / "ingredients").glob("*.json"))
    cards = [p for p in cards if not p.name.startswith("_")]
    assert len(cards) == 12
    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(card), key=lambda e: list(e.path))
        assert not errors, f"{path.name}: {errors[0].message if errors else ''}"


def test_ingredient_cards_have_required_knowledge_domains(skill_root: Path) -> None:
    required = {
        "basic", "names", "category", "origin_variety", "seasonality",
        "appearance_quality", "aroma", "taste", "texture", "tcm_attributes",
        "tcm_applications", "culinary_uses", "flavor_pairings", "substitutes",
        "processing_storage", "safety", "sources",
    }
    for path in (skill_root / "data" / "ingredients").glob("*.json"):
        if path.name.startswith("_"):
            continue
        card = json.loads(path.read_text(encoding="utf-8"))
        assert required <= set(card), path.name
        assert card["sources"], path.name
