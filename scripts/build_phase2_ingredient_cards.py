"""Build six Phase 2 structured ingredient cards.

These are deliberately partial cards: every populated statement is tied to a
page segment that actually exists in the page table.  Empty fields are marked
as gaps instead of being filled from model memory.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, INDEX_DIR, load_books, save_json  # noqa: E402

DB = INDEX_DIR / "knowledge.sqlite"
OUT = DATA / "ingredients-phase2"
BOOKS = {b["source_id"]: b for b in load_books()}


def page_text(sid: str, page: int) -> str:
    con = sqlite3.connect(DB)
    row = con.execute(
        "SELECT text FROM pages WHERE source_id=? AND pdf_page=?", (sid, page)
    ).fetchone()
    con.close()
    if not row:
        raise SystemExit(f"missing page: {sid} {page}")
    return row[0] or ""


def evidence(sid: str, page: int, needle: str | None = None, max_len: int = 240) -> dict[str, Any]:
    text = page_text(sid, page)
    flat = re.sub(r"\s+", " ", text).strip()
    if needle:
        pos = flat.lower().find(needle.lower())
        if pos < 0:
            raise SystemExit(f"needle not found: {sid} {page}: {needle}")
        start = max(0, pos - 20)
        quote = flat[start:start + max_len]
    else:
        quote = flat[:max_len]
    con = sqlite3.connect(DB)
    row = con.execute(
        "SELECT printed_page FROM pages WHERE source_id=? AND pdf_page=?", (sid, page)
    ).fetchone()
    con.close()
    book = BOOKS[sid]
    return {
        "source_id": sid,
        "book_title": book["title"],
        "pdf_page": page,
        "printed_page": row[0] if row else None,
        "chapter": None,
        "section": None,
        "quote": quote,
        "extraction_method": "ocr" if book["kind"] == "scanned" else "text_layer",
        "confidence": "medium" if book["kind"] == "scanned" else "high",
    }


def sensory(descriptors: list[str], evidence_list: list[dict[str, Any]]) -> dict[str, Any]:
    return {"descriptors": descriptors, "intensity": "unknown", "evidence": evidence_list}


def card(
    cid: str,
    zh: str,
    en: str,
    category: list[str],
    evidence_list: list[dict[str, Any]],
    pairings: list[dict[str, Any]] | None = None,
    allergens: list[str] | None = None,
    gaps: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cid,
        "basic": {
            "canonical_name_zh": zh,
            "scientific_name": None,
            "english_name": en,
            "one_line_definition": notes or f"{zh}的第二阶段结构化食材卡；仅收录本书知识库可追溯内容。",
            "research_status": "partial",
        },
        "names": {"aliases": [], "alias_evidence": []},
        "category": {"taxonomy": category, "culinary_role": []},
        "origin_variety": {"origins": [], "varieties": [], "notes": None},
        "seasonality": {"peak_season": None, "availability": None, "notes": None},
        "appearance_quality": {"traits": [], "grading": [], "notes": None},
        "aroma": sensory([], []),
        "taste": sensory([], []),
        "texture": sensory([], []),
        "tcm_attributes": {
            "applicable": False,
            "nature": None,
            "flavor": None,
            "meridians": None,
            "notes": "本卡不建立传统本草属性；传统理论必须与现代食品科学证据分开。",
        },
        "tcm_applications": {
            "functions": [],
            "traditional_uses": [],
            "theory_basis": None,
            "evidence": [],
        },
        "culinary_uses": {"methods": [], "preparation": [], "heat_notes": None},
        "flavor_pairings": pairings or [],
        "substitutes": [],
        "processing_storage": {"processing": [], "storage": [], "shelf_life": None},
        "safety": {
            "allergens": allergens or [],
            "contraindications": [],
            "toxicity": None,
            "food_safety": [],
            "at_risk_groups": ["过敏人群"] if allergens else [],
        },
        "sources": evidence_list,
        "scientific_name": None,
        "ingredient_category": category,
        "botanical_or_animal_origin": None,
        "physical_properties": None,
        "chemical_composition": None,
        "protein_profile": None,
        "lipid_profile": None,
        "carbohydrate_profile": None,
        "aroma_compounds": None,
        "flavor_characteristics": None,
        "texture_properties": None,
        "thermal_behavior": None,
        "processing_behavior": None,
        "storage_properties": None,
        "culinary_applications": [],
        "food_science_evidence": [
            {
                "claim": "该食材在本书知识库中有可追溯的页面记录；具体机制与数值需回到引用页核对。",
                "claim_type": "original",
                "conditions": None,
                "evidence": evidence_list[:1],
            }
        ],
        "traditional_materia_medica": {
            "applicable": False,
            "nature_flavor_meridians": None,
            "functions": [],
            "theory_basis": None,
            "evidence": [],
        },
        "safety_information": {
            "allergens": allergens or [],
            "hazards": [],
            "at_risk_groups": ["过敏人群"] if allergens else [],
            "evidence": [],
        },
        "source_references": evidence_list,
        "gaps": gaps or ["品种、产地、季节、定量成分、感官阈值等字段尚未从本书知识库充分提取。"],
    }


def build() -> list[dict[str, Any]]:
    basil_ev = [evidence("FB-PAGE-2008", 73, "BASIL"), evidence("MCG-V2-2013", 195, "香草")]
    chicken_ev = [evidence("FB-PAGE-2008", 130, "CHICKEN"), evidence("MCG-V3-2013", 348, "蛋白质")]
    flour_ev = [evidence("FC-BELITZ-2009", 717, "wheat"), evidence("MCG-V1-2013", 129, "面粉")]
    egg_ev = [evidence("MCG-V3-2013", 99, "蛋"), evidence("FC-BELITZ-2009", 593, "egg")]
    milk_ev = [evidence("MCG-V3-2013", 25, "乳"), evidence("FC-BELITZ-2009", 547, "milk")]
    salmon_ev = [evidence("MCG-V3-2013", 233, "海鲜"), evidence("FC-BELITZ-2009", 661, "fish")]

    return [
        card(
            "basil", "罗勒", "basil", ["香草", "唇形科（待核）"], basil_ev,
            pairings=[
                {"with": "TOMATOES", "reason": "The Flavor Bible 的 BASIL 条目把番茄列为搭配词。", "evidence": [basil_ev[0]]},
                {"with": "GARLIC", "reason": "The Flavor Bible 的 BASIL 条目把大蒜列为搭配词。", "evidence": [basil_ev[0]]},
            ],
            gaps=["科学名称、品种、产地、香气化合物定量、传统本草属性均未在本卡建立。"],
        ),
        card(
            "chicken", "鸡", "chicken", ["禽肉"], chicken_ev,
            pairings=[],
            gaps=[
                "品种、饲养方式、部位差异、中心温度与持水性定量未在本卡建立。",
                "The Flavor Bible 三栏文本层中的 CHICKEN 搭配候选需回页人工复核；未把版面邻近词写成确定搭配。",
            ],
        ),
        card(
            "wheat-flour", "小麦面粉", "wheat flour", ["谷物", "面粉"], flour_ev,
            allergens=["麸质"],
            gaps=["蛋白质含量分档、灰分、吸水率、面团流变学数据未在本卡建立。"],
        ),
        card(
            "egg", "蛋", "egg", ["蛋类"], egg_ev,
            allergens=["蛋"],
            gaps=["蛋清与蛋黄蛋白定量、凝固温度曲线、起泡性数据未在本卡建立。"],
        ),
        card(
            "milk", "乳", "milk", ["乳与乳制品"], milk_ev,
            allergens=["乳"],
            gaps=["乳蛋白分型、脂肪球结构、热处理对风味的影响未在本卡建立。"],
        ),
        card(
            "salmon", "鲑鱼", "salmon", ["鱼类", "水产品"], salmon_ev,
            allergens=["鱼"],
            gaps=["品种、养殖与野生差异、脂质组成、寄生虫风险控制参数未在本卡建立。"],
        ),
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = build()
    for row in rows:
        save_json(OUT / f"{row['id']}.json", row)
    save_json(
        OUT / "_index.json",
        {
            "phase": 2,
            "cards": [{"id": r["id"], "name": r["basic"]["canonical_name_zh"], "status": "partial"} for r in rows],
            "note": "六张第二阶段结构化食材卡，均为 partial；空字段代表知识库缺口，不是已研究结论。",
        },
    )
    print(json.dumps({"cards": len(rows), "ids": [r["id"] for r in rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
