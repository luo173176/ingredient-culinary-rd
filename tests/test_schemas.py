from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator


SCHEMAS = [
    "ingredient.schema.json",
    "knowledge-record.schema.json",
    "recipe.schema.json",
    "research-report.schema.json",
    "source.schema.json",
    "flavor-pairing.schema.json",
]

PHASE2_FIELDS = {
    "scientific_name",
    "ingredient_category",
    "botanical_or_animal_origin",
    "physical_properties",
    "chemical_composition",
    "protein_profile",
    "lipid_profile",
    "carbohydrate_profile",
    "aroma_compounds",
    "flavor_characteristics",
    "texture_properties",
    "thermal_behavior",
    "processing_behavior",
    "storage_properties",
    "culinary_applications",
    "flavor_pairings",
    "food_science_evidence",
    "traditional_materia_medica",
    "safety_information",
    "source_references",
}


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_draft_2020_12(skill_root: Path, name: str) -> None:
    schema = json.loads((skill_root / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"].endswith("2020-12/schema")


def test_ingredient_schema_exposes_phase2_optional_fields(skill_root: Path) -> None:
    schema = json.loads((skill_root / "schemas" / "ingredient.schema.json").read_text(encoding="utf-8"))
    assert PHASE2_FIELDS <= set(schema["properties"])


def test_all_ingredient_cards_validate(skill_root: Path) -> None:
    schema = json.loads((skill_root / "schemas" / "ingredient.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    old_cards = [p for p in sorted((skill_root / "data" / "ingredients").glob("*.json")) if not p.name.startswith("_")]
    new_cards = [
        p
        for p in sorted((skill_root / "data" / "ingredients-phase2").glob("*.json"))
        if not p.name.startswith("_")
    ]
    cards = old_cards + new_cards
    assert len(old_cards) == 12
    assert len(new_cards) == 6
    assert len(cards) == 18
    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(card), key=lambda e: list(e.path))
        assert not errors, f"{path.name}: {errors[0].message if errors else ''}"


def test_ingredient_cards_have_required_knowledge_domains(skill_root: Path) -> None:
    required = {
        "basic",
        "names",
        "category",
        "origin_variety",
        "seasonality",
        "appearance_quality",
        "aroma",
        "taste",
        "texture",
        "tcm_attributes",
        "tcm_applications",
        "culinary_uses",
        "flavor_pairings",
        "substitutes",
        "processing_storage",
        "safety",
        "sources",
    }
    for folder in ("ingredients", "ingredients-phase2"):
        for path in (skill_root / "data" / folder).glob("*.json"):
            if path.name.startswith("_"):
                continue
            card = json.loads(path.read_text(encoding="utf-8"))
            assert required <= set(card), path.name
            assert card["sources"], path.name


def test_phase2_cards_keep_tcm_and_food_science_separate(skill_root: Path) -> None:
    for path in (skill_root / "data" / "ingredients-phase2").glob("*.json"):
        if path.name.startswith("_"):
            continue
        card = json.loads(path.read_text(encoding="utf-8"))
        assert card["basic"]["research_status"] == "partial"
        assert card["tcm_attributes"]["applicable"] is False
        assert "传统理论" in card["tcm_attributes"]["notes"]
        assert card["traditional_materia_medica"]["applicable"] is False
        assert card["gaps"]


def test_flavor_pairing_schema_accepts_sample_and_rejects_unknown_level(skill_root: Path) -> None:
    schema = json.loads((skill_root / "schemas" / "flavor-pairing.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    with (skill_root / "data" / "flavor_pairings.jsonl").open(encoding="utf-8") as fh:
        first = json.loads(fh.readline())
    assert validator.is_valid(first)
    bad = dict(first)
    bad["evidence_level"] = "made_up"
    assert not validator.is_valid(bad)

