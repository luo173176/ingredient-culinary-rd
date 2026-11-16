"""Build schema-compliant ingredient cards (JSON + Markdown) from curated specs.

Every ``quote`` in the evidence list is verified as a substring of the stored
page text before a card is written.  A failed verification aborts the build:
the project never ships an invented quotation.

Only facts traceable to the four books are included.  Fields that the books do
not support stay empty and are listed under ``gaps``.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INGREDIENTS_DIR, PAGES_DIR, ROOT, load_json  # noqa: E402

REF_CN = ROOT / "references" / "chinese-ingredients" / "ingredients"
REF_DK = ROOT / "references" / "global-ingredients" / "ingredients"
REF_CN.mkdir(parents=True, exist_ok=True)
REF_DK.mkdir(parents=True, exist_ok=True)

BOOKS = {b["source_id"]: b for b in load_json(ROOT / "config" / "books.json")["books"]}

PAGE_FILES = {
    "MM-ZYX-2016": PAGES_DIR / "MM-ZYX-2016.jsonl",
    "CN-DIDAO-2011": PAGES_DIR / "CN-DIDAO-2011.ocr.jsonl",
    "FS-SFAH-2023": PAGES_DIR / "FS-SFAH-2023.jsonl",
    "DK-INGREDIENTS": PAGES_DIR / "DK-INGREDIENTS.ocr.jsonl",
}

_PAGE_CACHE: dict[str, dict[int, dict[str, Any]]] = {}


def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))


def page_record(source_id: str, pdf_page: int) -> dict[str, Any]:
    if source_id not in _PAGE_CACHE:
        path = PAGE_FILES[source_id]
        _PAGE_CACHE[source_id] = {
            r["pdf_page"]: r for r in map(json.loads, open(path, encoding="utf-8"))
        }
    rec = _PAGE_CACHE[source_id].get(pdf_page)
    if rec is None:
        raise ValueError(f"page not found: {source_id} PDF {pdf_page}")
    return rec


def evidence(
    key: str,
    source_id: str,
    pdf_page: int,
    quote: str,
    *,
    tags: tuple[str, ...] = (),
    printed: int | None = None,
    chapter: str | None = None,
    confidence: str | None = None,
) -> dict[str, Any]:
    rec = page_record(source_id, pdf_page)
    if norm(quote) not in norm(rec["text"]):
        raise ValueError(
            f"quote not found in {source_id} PDF {pdf_page}: {quote!r}\n"
            f"page starts: {rec['text'][:160]!r}"
        )
    if printed is None:
        printed = rec.get("printed_page")
    if confidence is None:
        confidence = "high" if BOOKS[source_id]["kind"] == "digital" else "medium"
    return {
        "key": key,
        "source_id": source_id,
        "pdf_page": pdf_page,
        "printed_page": printed,
        "chapter": chapter,
        "section": None,
        "quote": quote[:600],
        "tags": tags,
        "confidence": confidence,
    }


def ev_obj(ev: dict[str, Any]) -> dict[str, Any]:
    book = BOOKS[ev["source_id"]]
    return {
        "source_id": ev["source_id"],
        "book_title": book["short_title"],
        "pdf_page": ev["pdf_page"],
        "printed_page": ev["printed_page"],
        "chapter": ev["chapter"],
        "section": ev["section"],
        "quote": ev["quote"],
        "extraction_method": "ocr" if book["kind"] == "scanned" else "text_layer",
        "confidence": ev["confidence"],
    }


def resolve(spec: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    by_key = {e["key"]: e for e in spec["evidence"]}
    out = []
    for key in keys:
        if key not in by_key:
            raise KeyError(f"{spec['name']}: unknown evidence key {key}")
        out.append(ev_obj(by_key[key]))
    return out


def cite(spec: dict[str, Any], keys: list[str], short: bool = True) -> str:
    parts = []
    seen = set()
    for e in resolve(spec, keys):
        title = e["book_title"]
        if e["printed_page"]:
            page = f"p.{e['printed_page']}"
            if not short:
                page += f"（PDF {e['pdf_page']}）"
        else:
            page = f"PDF {e['pdf_page']}"
        label = f"《{title}》{page}"
        if label not in seen:
            seen.add(label)
            parts.append(label)
    return "、".join(parts)


def claim(spec: dict[str, Any], statement: str, keys: list[str], claim_type: str = "original") -> dict[str, Any]:
    return {"statement": statement, "evidence": resolve(spec, keys), "claim_type": claim_type}


def sensory(spec: dict[str, Any], descriptors: list[str], intensity: str, keys: list[str]) -> dict[str, Any]:
    return {
        "descriptors": descriptors,
        "intensity": intensity,
        "evidence": resolve(spec, keys),
    }


SPECS: list[dict[str, Any]] = [
    {
        "id": "mung-bean",
        "name": "绿豆",
        "english": "mung bean",
        "domain": "cn",
        "category": ["豆类", "谷物杂粮"],
        "role": ["煮汤", "煮粥", "制粉", "发豆芽"],
        "aliases": ["青小豆", "植豆"],
        "alias_keys": ["alias1", "alias2"],
        "one_line": "中国传统豆类；书中记其味甘性凉，可煮粥、制粉、发豆芽，并收有数个食疗小方。",
        "evidence": [
            evidence("alias1", "CN-DIDAO-2011", 40, "绿豆又名青小豆", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("alias2", "CN-DIDAO-2011", 40, "别名:豆、植豆", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("tcm", "CN-DIDAO-2011", 40, "性味:味甘性凉", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("origin", "CN-DIDAO-2011", 40, "主产地:东北三省", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("season", "CN-DIDAO-2011", 40, "成熟时期:8月", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("cook1", "CN-DIDAO-2011", 40, "作豆粥、豆饭、豆酒", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("cook2", "CN-DIDAO-2011", 40, "粉条、粉丝、糕点", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("sprout", "CN-DIDAO-2011", 40, "绿豆在发芽过程中", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("prep1", "CN-DIDAO-2011", 40, "好的绿豆洗净晾干", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("prep2", "CN-DIDAO-2011", 40, "在铁锅中干炒十分钟", printed=36, chapter="第一章 谷物和米面制品"),
            evidence("safety1", "CN-DIDAO-2011", 40, "绿豆性凉,脾胃虚弱的人不", printed=36, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("safety2", "CN-DIDAO-2011", 40, "补药时忌食绿豆食品", printed=36, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence(
                "pair1",
                "CN-DIDAO-2011",
                40,
                "绿豆金银花100g30g煎煮后加红糖饮用,可解酒",
                printed=36,
                chapter="第一章 谷物和米面制品",
                confidence="low",
            ),
            evidence("pair2", "CN-DIDAO-2011", 40, "绿豆甘草50g10g", printed=36, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("pair3", "CN-DIDAO-2011", 40, "绿豆绿茶50g10g", printed=36, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("pair4", "CN-DIDAO-2011", 40, "绿豆生甘草", printed=36, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence(
                "claim_diabetes",
                "CN-DIDAO-2011",
                40,
                "绿豆淀粉中含有相当数量的低聚糖",
                printed=36,
                chapter="第一章 谷物和米面制品",
                confidence="low",
            ),
        ],
        "origin": [("主产地：东北三省", ["origin"])],
        "varieties": [],
        "season": "成熟期：8月（原文作“成熟时期”）",
        "season_keys": ["season"],
        "quality": [],
        "aroma": ([], "unknown", []),
        "taste": ([], "unknown", []),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "凉",
            "flavor": "甘",
            "meridians": None,
            "notes": ("书中记“味甘性凉”；属传统食疗属性，不是现代医学证据。", ["tcm"]),
            "functions": ["清热解毒（书中食疗表述）", "补充营养"],
            "uses": ["夏季煮汤/煮粥", "绿豆糕", "发豆芽"],
            "keys": ["tcm"],
        },
        "cook": ["煮粥/豆饭", "制粉条/粉丝/糕点", "发豆芽"],
        "prep": [("洗净晾干", ["prep1"]), ("干炒十分钟后再煮（书中小窍门）", ["prep2"])],
        "heat": ("书中小窍门：干炒十分钟左右再煮，绿豆更易煮烂；未给温度。", ["prep2"]),
        "pairings": [
            ("金银花", "书中小食方：煎煮后加红糖饮用，书中称“可解酒”", ["pair1"]),
            ("甘草", "书中小食方组合", ["pair2"]),
            ("绿茶", "书中小食方组合", ["pair3"]),
            ("生甘草", "书中小食方组合", ["pair4"]),
        ],
        "subs": [],
        "storage": [],
        "safety": [
            ("脾胃虚弱者不宜多吃（原书食疗宜忌）", ["safety1"]),
            ("服温补药时忌食绿豆食品（原书饮食禁忌，属传统说法）", ["safety2"]),
        ],
        "gaps": [
            "香气、质地的系统描述",
            "品种与等级",
            "储存条件与保质期",
            "书中“辅助治疗糖尿病及肥胖症”“抑制癌细胞”等表述不是现代临床证据，本卡不采信为结论",
        ],
    },
    {
        "id": "kidney-bean",
        "name": "芸豆",
        "english": "kidney bean",
        "domain": "cn",
        "category": ["豆类", "蔬菜/杂粮"],
        "role": ["炖煮", "制馅", "做糕点"],
        "aliases": ["白肾豆", "架豆", "大四季豆米", "白腰豆"],
        "alias_keys": ["alias", "variety"],
        "one_line": "书中记其味甘性温，主产地山东，收有多个品种群与“话梅芸豆”等小食做法。",
        "evidence": [
            evidence("alias", "CN-DIDAO-2011", 41, "别名:白肾豆、架豆", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("tcm", "CN-DIDAO-2011", 41, "性味:味甘性温", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("origin", "CN-DIDAO-2011", 41, "主产地:山东省", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("season", "CN-DIDAO-2011", 41, "成熟期:8月上旬", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("variety", "CN-DIDAO-2011", 41, "俗称“大四季豆米”,亦称“白腰豆”", printed=37, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("quality", "CN-DIDAO-2011", 41, "颗粒硕大、色泽鲜艳", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("use", "CN-DIDAO-2011", 41, "制作糕点、豆馅、甜汤、豆沙的优质原料", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("cook", "CN-DIDAO-2011", 41, "高压锅里蒸三十分钟", printed=37, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("cook2", "CN-DIDAO-2011", 41, "芸豆煮熟后入锅蒸20分钟", printed=37, chapter="第一章 谷物和米面制品"),
            evidence("prep", "CN-DIDAO-2011", 41, "芸豆洗净后在凉水里泡一夜", printed=37, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("pair", "CN-DIDAO-2011", 41, "话梅芸豆", printed=37, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("claim_tumor", "CN-DIDAO-2011", 41, "对癌细胞的扩散有一定的抑制作用", printed=37, chapter="第一章 谷物和米面制品", confidence="low"),
        ],
        "origin": [("主产地：山东省", ["origin"])],
        "varieties": [("大白芸豆（俗称大四季豆米、白腰豆）", ["variety"])],
        "season": "成熟期：8月上旬",
        "season_keys": ["season"],
        "quality": [("红芸豆颗粒硕大、色泽鲜艳", ["quality"])],
        "aroma": ([], "unknown", []),
        "taste": ([], "unknown", []),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "温",
            "flavor": "甘",
            "meridians": None,
            "notes": ("书中记“味甘性温”；属传统食疗属性，不是现代医学证据。", ["tcm"]),
            "functions": ["温中下气（传统记载）", "利肠胃（传统记载）", "益肾补元气（传统记载）"],
            "uses": ["豆沙", "糕点", "炖煮"],
            "keys": ["tcm"],
        },
        "cook": ["蒸/高压锅蒸", "煮", "制豆沙/豆馅/糕点/甜汤"],
        "prep": [("凉水泡一夜", ["prep"]), ("先煮熟再蒸（书中芸豆卷做法）", ["cook2"])],
        "heat": ("书中“话梅芸豆”用高压锅蒸三十分钟；芸豆卷先煮熟再蒸二十分钟；未给温度。", ["cook", "cook2"]),
        "pairings": [("话梅、红枣、冰糖", "书中小食“话梅芸豆”的组合", ["pair"])],
        "subs": [],
        "storage": [],
        "safety": [
            ("生豆类含凝集素，必须彻底煮熟；四书未展开毒理，属通用食品安全提示（非四书依据）", []),
        ],
        "gaps": ["香气描述", "替代方案", "储存期限", "书中“抑制癌细胞扩散”表述不是现代临床证据"],
    },
    {
        "id": "black-bean",
        "name": "黑豆",
        "english": "black bean",
        "domain": "cn",
        "category": ["豆类", "谷物杂粮"],
        "role": ["煲汤", "炒制", "制豉"],
        "aliases": ["槽豆", "乌豆", "枝仔豆", "黑大豆"],
        "alias_keys": ["alias"],
        "one_line": "书中记其味甘性平，主产区为东北三省与河南，并收有“何首乌黑豆煲鸡脚”食疗方。",
        "evidence": [
            evidence("alias", "CN-DIDAO-2011", 43, "别名:槽豆、乌豆、枝仔豆、黑大豆", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("tcm", "CN-DIDAO-2011", 43, "性味:味甘性平", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("func", "CN-DIDAO-2011", 43, "补肾益阴、健脾利湿、除热解毒", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("origin", "CN-DIDAO-2011", 43, "主产区:东北三省,河南省", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("season", "CN-DIDAO-2011", 43, "成熟期:12月~次年3月", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("quality", "CN-DIDAO-2011", 43, "脐处有白点", printed=39, chapter="第一章 谷物和米面制品", confidence="low"),
            evidence("cook1", "CN-DIDAO-2011", 43, "黑豆洗净放锅中炒至豆壳裂开", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("cook2", "CN-DIDAO-2011", 43, "全部用料放入煲内,加适量清水煲3小时", printed=39, chapter="第一章 谷物和米面制品"),
            evidence("pair", "CN-DIDAO-2011", 43, "何首乌黑豆煲鸡脚", printed=39, chapter="第一章 谷物和米面制品"),
        ],
        "origin": [("主产区：东北三省、河南省", ["origin"])],
        "varieties": [],
        "season": "成熟期：12月~次年3月",
        "season_keys": ["season"],
        "quality": [("种脐处有白点（书中用于辨别真假黑豆）", ["quality"])],
        "aroma": ([], "unknown", []),
        "taste": ([], "unknown", []),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "平",
            "flavor": "甘",
            "meridians": None,
            "notes": ("书中记“味甘性平”，功效记载为补肾益阴、健脾利湿、除热解毒；属传统理论。", ["tcm", "func"]),
            "functions": ["补肾益阴（传统）", "健脾利湿（传统）", "除热解毒（传统）"],
            "uses": ["何首乌黑豆煲鸡脚（书中小食/食疗方）"],
            "keys": ["tcm", "func"],
        },
        "cook": ["煲汤", "炒至豆壳裂开"],
        "prep": [("洗净", []), ("炒至豆壳裂开（书中煲汤做法）", ["cook1"])],
        "heat": ("书中煲汤约三小时；未给温度。", ["cook2"]),
        "pairings": [("何首乌、红枣、鸡脚、猪瘦肉", "书中“何首乌黑豆煲鸡脚”食疗方组合", ["pair"])],
        "subs": [],
        "storage": [],
        "safety": [
            ("书中食疗方含何首乌；四书未提供何首乌肝损伤风险的系统数据，不建议自行长期服用（缺口提示）", []),
            ("豆类必须彻底煮熟；四书未展开毒理，属通用食品安全提示（非四书依据）", []),
        ],
        "gaps": ["香气、质地的系统描述", "替代方案", "储存条件", "何首乌配伍的现代安全性证据"],
    },
    {
        "id": "bitter-melon",
        "name": "苦瓜",
        "english": "bitter melon / balsam pear",
        "domain": "cn",
        "category": ["蔬菜", "瓜类"],
        "role": ["清炒", "煲汤", "凉拌", "榨汁"],
        "aliases": ["凉瓜", "癫瓜", "锦荔枝", "葡萄"],
        "alias_keys": ["alias"],
        "one_line": "书中记其味苦、性寒、无毒，果瘤与果肉颜色是品质线索；收有苦瓜汤、烧鱼、榨汁等做法。",
        "evidence": [
            evidence("alias", "CN-DIDAO-2011", 80, "别名:凉瓜、癫瓜、锦荔枝、葡萄", printed=76, chapter="第三章 蔬菜"),
            evidence("tcm", "CN-DIDAO-2011", 80, "性味:味苦,性寒,无毒", printed=76, chapter="第三章 蔬菜"),
            evidence("origin", "CN-DIDAO-2011", 80, "主产地:福建两广地区", printed=76, chapter="第三章 蔬菜"),
            evidence("season", "CN-DIDAO-2011", 80, "成熟期:4~9月", printed=76, chapter="第三章 蔬菜"),
            evidence("quality1", "CN-DIDAO-2011", 80, "颗粒大而饱", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("quality2", "CN-DIDAO-2011", 80, "好的苦瓜一般果肉洁白,若果肉发黄,则表示已过", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("func1", "CN-DIDAO-2011", 80, "清热解暑", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("func2", "CN-DIDAO-2011", 80, "补脾和胃", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("func3", "CN-DIDAO-2011", 80, "滋肝明目", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair1", "CN-DIDAO-2011", 80, "葱白生姜", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair1r", "CN-DIDAO-2011", 80, "用于暑天感冒发热、身痛口苦", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair2", "CN-DIDAO-2011", 80, "苦瓜菊花", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair2r", "CN-DIDAO-2011", 80, "用于肝热目赤或疼痛", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair3", "CN-DIDAO-2011", 235, "苦瓜辣椒共炒食,可清热、开胃", printed=231, chapter="第八章 调味品", confidence="low"),
            evidence("safety1", "CN-DIDAO-2011", 80, "可刺激子宫收缩", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("safety2", "CN-DIDAO-2011", 80, "瓜中奎宁的含量较低", printed=76, chapter="第三章 蔬菜", confidence="low"),
            evidence("cook1", "CN-DIDAO-2011", 81, "蚌肉苦瓜汤", printed=77, chapter="第三章 蔬菜", confidence="low"),
            evidence("cook2", "CN-DIDAO-2011", 81, "苦瓜烧鱼", printed=77, chapter="第三章 蔬菜", confidence="low"),
            evidence("cook3", "CN-DIDAO-2011", 81, "香蕉苦瓜汁", printed=77, chapter="第三章 蔬菜", confidence="low"),
            evidence("prep", "CN-DIDAO-2011", 81, "将苦瓜切段、蚌肉切片", printed=77, chapter="第三章 蔬菜", confidence="low"),
        ],
        "origin": [("主产地：福建、两广地区", ["origin"])],
        "varieties": [],
        "season": "成熟期：4~9月",
        "season_keys": ["season"],
        "quality": [
            ("果瘤颗粒大而饱满者瓜肉较厚", ["quality1"]),
            ("果肉洁白为佳；发黄表示已过熟、口感下降", ["quality2"]),
        ],
        "aroma": ([], "unknown", []),
        "taste": ([], "unknown", []),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "寒",
            "flavor": "苦",
            "meridians": None,
            "notes": ("书中记“味苦，性寒，无毒”，并记清热解暑、补脾和胃、滋肝明目；属传统理论。", ["tcm", "func1", "func2"]),
            "functions": ["清热解暑（传统）", "补脾和胃（传统）", "滋肝明目（传统）"],
            "uses": ["暑天清炒/煲汤", "苦瓜配辣椒/木耳（书中饮食搭配）"],
            "keys": ["tcm", "func1", "func2", "func3"],
        },
        "cook": ["煮汤", "烧", "榨汁"],
        "prep": [("切段/切块；书中有氽烫、快炒做法", ["prep", "cook2"])],
        "heat": ("书未给温度；苦瓜烧鱼为“快炒至香”后小火焖约十分钟。", ["cook2"]),
        "pairings": [
            ("葱白、生姜", "书中饮食搭配，用于暑天感冒发热、身痛口苦", ["pair1", "pair1r"]),
            ("菊花", "书中饮食搭配，用于肝热目赤或疼痛", ["pair2", "pair2r"]),
            ("辣椒", "书中记“苦瓜辣椒共炒食，可清热、开胃”", ["pair3"]),
        ],
        "subs": [],
        "storage": [],
        "safety": [
            ("书中称苦瓜可刺激子宫收缩、孕妇不要食用；同时又记瓜中奎宁含量较低。按保守原则，孕妇应咨询医生", ["safety1", "safety2"]),
            ("书中“防癌抗癌”“降糖”等表述不是现代临床证据，本卡不采信为结论", []),
        ],
        "gaps": ["香气/质地的系统描述", "替代方案", "苦味物质的定量数据", "孕妇食用的现代安全性证据"],
    },
    {
        "id": "lotus-root",
        "name": "莲藕",
        "english": "lotus root",
        "domain": "cn",
        "category": ["蔬菜", "根茎类"],
        "role": ["煲汤", "清炒", "凉拌", "榨汁"],
        "aliases": ["藕", "莲菜"],
        "alias_keys": ["alias", "alias2"],
        "one_line": "书中记其味甘性平，可除热渴、散淤血；微甜且脆，收有莲藕排骨煨汤与藕汁蜂蜜的做法。",
        "evidence": [
            evidence("alias", "CN-DIDAO-2011", 87, "又称莲藕", printed=83, chapter="第三章 蔬菜"),
            evidence("alias2", "CN-DIDAO-2011", 87, "又称莲菜", printed=83, chapter="第三章 蔬菜", confidence="low"),
            evidence("tcm", "CN-DIDAO-2011", 87, "性味:味甘,性平", printed=83, chapter="第三章 蔬菜"),
            evidence("func", "CN-DIDAO-2011", 87, "功效:除热渴,散淤血", printed=83, chapter="第三章 蔬菜"),
            evidence("origin", "CN-DIDAO-2011", 87, "主产区:江苏省、浙江省", printed=83, chapter="第三章 蔬菜"),
            evidence("season", "CN-DIDAO-2011", 87, "成熟期:9~10月", printed=83, chapter="第三章 蔬菜"),
            evidence("quality1", "CN-DIDAO-2011", 87, "藕孔小的", printed=83, chapter="第三章 蔬菜", confidence="low"),
            evidence("quality2", "CN-DIDAO-2011", 87, "如果藕孔中带红或出现茶色黏液,就表", printed=83, chapter="第三章 蔬菜", confidence="low"),
            evidence("sensory", "CN-DIDAO-2011", 87, "微甜且脆", printed=83, chapter="第三章 蔬菜"),
            evidence("cook1", "CN-DIDAO-2011", 87, "可生食也可做菜", printed=83, chapter="第三章 蔬菜"),
            evidence("cook2", "CN-DIDAO-2011", 87, "莲藕排骨煨汤", printed=83, chapter="第三章 蔬菜"),
            evidence("cook3", "CN-DIDAO-2011", 87, "藕榨汁后加入蜂蜜", printed=83, chapter="第三章 蔬菜"),
            evidence("heat", "CN-DIDAO-2011", 87, "后调成小火,炖一小时后加", printed=83, chapter="第三章 蔬菜", confidence="low"),
            evidence("pair1", "CN-DIDAO-2011", 87, "盐、葱、姜调味即可", printed=83, chapter="第三章 蔬菜"),
            evidence("pair2", "CN-DIDAO-2011", 87, "藕榨汁后加入蜂蜜", printed=83, chapter="第三章 蔬菜"),
            evidence("safety1", "CN-DIDAO-2011", 87, "泄者不要生吃藕", printed=83, chapter="第三章 蔬菜", confidence="low"),
            evidence("safety2", "CN-DIDAO-2011", 87, "产妇不宜", printed=83, chapter="第三章 蔬菜", confidence="low"),
        ],
        "origin": [("主产区：江苏省、浙江省", ["origin"])],
        "varieties": [],
        "season": "成熟期：9~10月",
        "season_keys": ["season"],
        "quality": [("选藕孔小者；藕孔带红或出现茶色黏液表示不新鲜", ["quality1", "quality2"])],
        "aroma": ([], "unknown", []),
        "taste": (["微甜"], "medium", ["sensory"]),
        "texture": (["脆"], "medium", ["sensory"]),
        "tcm": {
            "applicable": True,
            "nature": "平",
            "flavor": "甘",
            "meridians": None,
            "notes": ("书中记“味甘，性平”，功效为除热渴、散淤血；属传统理论。", ["tcm", "func"]),
            "functions": ["除热渴（传统）", "散淤血（传统）"],
            "uses": ["莲藕排骨煨汤（书中湖北做法）", "藕汁加蜂蜜（书中）"],
            "keys": ["tcm", "func"],
        },
        "cook": ["生食", "煲汤", "榨汁"],
        "prep": [("去皮切片/切块；排骨先焯去血沫（书中）", ["heat"])],
        "heat": ("书中排骨汤：大火煮开后转小火炖约一小时；未给温度。", ["heat"]),
        "pairings": [
            ("排骨", "书中“莲藕排骨煨汤”", ["cook2"]),
            ("蜂蜜", "书中“藕榨汁后加入蜂蜜”", ["pair2"]),
            ("盐、葱、姜", "书中汤品调味", ["pair1"]),
        ],
        "subs": [],
        "storage": [],
        "safety": [
            ("脾胃虚寒、大便溏泄者不要生吃藕（原书）", ["safety1"]),
            ("产妇不宜过早食用（原书）", ["safety2"]),
            ("生藕汁饮用有微生物风险，建议充分清洗或加热（通用食品安全提示，非四书依据）", []),
        ],
        "gaps": ["香气描述", "品种", "替代方案", "藕粉/藕节的独立数据"],
    },
    {
        "id": "shiitake",
        "name": "香菇",
        "english": "shiitake",
        "domain": "cn",
        "category": ["菌藻类", "食用菌"],
        "role": ["炖", "炒", "提鲜"],
        "aliases": [],
        "alias_keys": [],
        "one_line": "书中称其香气沁人、味道鲜美，记味甘性平凉，并给出热水泡发与“香菇炖杏仁”的做法。",
        "evidence": [
            evidence("tcm", "CN-DIDAO-2011", 119, "性味:味甘,性平、凉", printed=115, chapter="第三章 蔬菜"),
            evidence("func", "CN-DIDAO-2011", 119, "功效:益智安神,补肝益肾", printed=115, chapter="第三章 蔬菜"),
            evidence("origin", "CN-DIDAO-2011", 119, "主产区:山东、河南、浙江、福建、台湾、广东、广西等地", printed=115, chapter="第三章 蔬菜"),
            evidence("season", "CN-DIDAO-2011", 119, "成熟期:1~2月", printed=115, chapter="第三章 蔬菜"),
            evidence("quality1", "CN-DIDAO-2011", 119, "菌盖肥厚", printed=115, chapter="第三章 蔬菜", confidence="low"),
            evidence("quality2", "CN-DIDAO-2011", 119, "内侧为乳白色", printed=115, chapter="第三章 蔬菜", confidence="low"),
            evidence("quality3", "CN-DIDAO-2011", 119, "菇柄短", printed=115, chapter="第三章 蔬菜", confidence="low"),
            evidence("sensory1", "CN-DIDAO-2011", 119, "香气沁人", printed=115, chapter="第三章 蔬菜"),
            evidence("sensory2", "CN-DIDAO-2011", 119, "味道特别鲜美", printed=115, chapter="第三章 蔬菜"),
            evidence("sensory3", "CN-DIDAO-2011", 119, "具有独特的菇香", printed=115, chapter="第三章 蔬菜", confidence="low"),
            evidence("prep1", "CN-DIDAO-2011", 119, "不宜用冷水泡发,应用热", printed=115, chapter="第三章 蔬菜", confidence="low"),
            evidence("prep2", "CN-DIDAO-2011", 119, "六十摄氏度以上的热水中", printed=115, chapter="第三章 蔬菜"),
            evidence("cook1", "CN-DIDAO-2011", 119, "香菇炖杏仁", printed=115, chapter="第三章 蔬菜"),
            evidence("cook2", "CN-DIDAO-2011", 119, "略煸炒", printed=115, chapter="第三章 蔬菜"),
            evidence("claim_tumor", "CN-DIDAO-2011", 119, "抗肿瘤、降低血脂等", printed=115, chapter="第三章 蔬菜", confidence="low"),
        ],
        "origin": [("主产区：山东、河南、浙江、福建、台湾、广东、广西等地", ["origin"])],
        "varieties": [],
        "season": "成熟期：1~2月",
        "season_keys": ["season"],
        "quality": [("以菌盖肥厚、内侧乳白色、菇柄短者为佳", ["quality1", "quality2", "quality3"])],
        "aroma": (["香气沁人", "独特菇香"], "high", ["sensory1", "sensory3"]),
        "taste": (["鲜美"], "high", ["sensory2"]),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "平、凉",
            "flavor": "甘",
            "meridians": None,
            "notes": ("书中记“味甘，性平、凉”，功效为益智安神、补肝益肾；属传统理论。", ["tcm", "func"]),
            "functions": ["益智安神（传统）", "补肝益肾（传统）"],
            "uses": ["香菇炖杏仁（书中食疗方）", "炖/炒"],
            "keys": ["tcm", "func"],
        },
        "cook": ["炖", "炒"],
        "prep": [("不宜冷水泡发，应用 60°C 以上热水浸泡（书中窍门）", ["prep1", "prep2"])],
        "heat": ("书未给温度；泡发水温有明确提示。", ["prep2"]),
        "pairings": [("杏仁、青豆", "书中“香菇炖杏仁”配方", ["cook1"])],
        "subs": [],
        "storage": [],
        "safety": [
            ("书中“抗肿瘤、降低血脂”等表述不是现代临床证据，本卡不采信为结论", ["claim_tumor"]),
            ("干香菇泡发时间过长有微生物风险（通用食品安全提示，非四书依据）", []),
        ],
        "gaps": ["品种与等级", "替代方案", "香气成分定量", "储存条件"],
    },
    {
        "id": "sichuan-pepper",
        "name": "花椒",
        "english": "Sichuan pepper / prickly ash",
        "domain": "cn",
        "category": ["调味品", "香辛料"],
        "role": ["麻香", "去腥", "增香"],
        "aliases": ["川椒", "蜀椒"],
        "alias_keys": ["alias"],
        "one_line": "书中记其气芳香、味麻且辣，传统属性辛温、归脾胃肾经；既作香料去腥，也入传统方药。",
        "evidence": [
            evidence("alias", "MM-ZYX-2016", 396, "又名川椒、蜀椒", chapter="第十四章 温里药"),
            evidence("nature", "MM-ZYX-2016", 396, "辛,温。归脾、胃、肾经。", chapter="第十四章 温里药"),
            evidence("eff", "MM-ZYX-2016", 396, "温中止痛,杀虫止痒。", chapter="第十四章 温里药"),
            evidence("sensory", "MM-ZYX-2016", 396, "本品气芳香,味麻且辣。", chapter="第十四章 温里药"),
            evidence("origin", "MM-ZYX-2016", 396, "主产于辽宁、河北、四川,传统以四川产者为佳", chapter="第十四章 温里药"),
            evidence("season", "MM-ZYX-2016", 396, "秋季采收成熟果实", chapter="第十四章 温里药"),
            evidence("quality", "MM-ZYX-2016", 396, "花椒以色紫红、无梗、无椒目者为佳", chapter="第十四章 温里药"),
            evidence("usage", "MM-ZYX-2016", 396, "煎服,3~6g。外用适量,煎汤熏洗。", chapter="第十四章 温里药"),
            evidence("pair1", "MM-ZYX-2016", 396, "常与生姜、白豆蔻等同用", chapter="第十四章 温里药"),
            evidence("pair2", "MM-ZYX-2016", 396, "常与干姜、人参等配伍", chapter="第十四章 温里药"),
            evidence("pair3", "MM-ZYX-2016", 396, "与砂仁、肉豆蔻等同用", chapter="第十四章 温里药"),
            evidence("pair4", "MM-ZYX-2016", 396, "与乌梅、干姜、黄柏等同用", chapter="第十四章 温里药"),
            evidence("pair5", "MM-ZYX-2016", 396, "与茯苓配伍", chapter="第十四章 温里药"),
            evidence("cn_tcm", "CN-DIDAO-2011", 234, "性味:味辛,性温", printed=230, chapter="第八章 调味品"),
            evidence("cn_eff", "CN-DIDAO-2011", 234, "功效:温中止痛、杀虫止痒", printed=230, chapter="第八章 调味品"),
            evidence("cn_quality", "CN-DIDAO-2011", 234, "应选购壳色红艳油润,果实开口而不含籽粒,手感糙硬的", printed=230, chapter="第八章 调味品"),
            evidence("cook", "CN-DIDAO-2011", 234, "烹饪时加入少许花椒", printed=230, chapter="第八章 调味品"),
            evidence("deodor", "CN-DIDAO-2011", 234, "除各种肉类的腥气", printed=230, chapter="第八章 调味品"),
            evidence("storage", "CN-DIDAO-2011", 234, "可防虫", printed=230, chapter="第八章 调味品", confidence="low"),
            evidence("safety1", "CN-DIDAO-2011", 234, "花椒虽可使用但不宜多用", printed=230, chapter="第八章 调味品"),
            evidence("safety2", "CN-DIDAO-2011", 234, "可诱发恶性肿瘤", printed=230, chapter="第八章 调味品", confidence="low"),
            evidence("safety3", "CN-DIDAO-2011", 234, "都有一定的毒性", printed=230, chapter="第八章 调味品", confidence="low"),
        ],
        "origin": [
            ("《中药学》：主产于辽宁、河北、四川，传统以四川产者为佳", ["origin"]),
        ],
        "varieties": [],
        "season": "秋季采收成熟果实",
        "season_keys": ["season"],
        "quality": [
            ("《中药学》：花椒以色紫红、无梗、无椒目者为佳", ["quality"]),
            ("《中国地道食材图录大全》：壳色红艳油润、开口不含籽、手感糙硬", ["cn_quality"]),
        ],
        "aroma": (["芳香"], "high", ["sensory"]),
        "taste": (["麻", "辣", "辛"], "high", ["sensory", "cn_tcm"]),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "温",
            "flavor": "辛",
            "meridians": "脾、胃、肾",
            "notes": ("《中药学》记“辛，温。归脾、胃、肾经”，功效温中止痛、杀虫止痒；属传统理论，不是现代医学证据。", ["nature", "eff"]),
            "functions": ["温中止痛（传统）", "杀虫止痒（传统，外用）"],
            "uses": ["中寒脘腹冷痛、呕吐泄泻（传统应用）", "虫积腹痛（传统应用）", "湿疹/阴痒外用（传统应用）"],
            "keys": ["nature", "eff"],
        },
        "cook": ["烹饪调味", "去腥增香"],
        "prep": [("整粒或磨粉使用；书中未见花椒油温度", [])],
        "heat": ("书中未给花椒油温度；避免炸糊发苦（烹饪提示，非原文温度）。", []),
        "pairings": [
            ("生姜、白豆蔻", "《中药学》传统配伍（不是烹饪搭配建议）", ["pair1"]),
            ("干姜、人参", "《中药学》传统配伍（大建中汤）", ["pair2"]),
            ("砂仁、肉豆蔻", "《中药学》传统配伍", ["pair3"]),
            ("乌梅、干姜、黄柏", "《中药学》传统配伍（乌梅丸）", ["pair4"]),
            ("茯苓", "《中药学》传统配伍（椒苓丸）", ["pair5"]),
        ],
        "subs": [],
        "storage": [("纱布包花椒放入米中，可防虫（书中生活窍门）", ["storage"])],
        "safety": [
            ("原书：花椒虽可使用但不宜多用", ["safety1"]),
            ("原书称天然调味品“有一定的毒性，可诱发恶性肿瘤”；该表述缺乏现代证据，本卡仅记录为书中说法", ["safety2", "safety3"]),
            ("《中药学》用法用量为教材临床语境，不是烹饪用量；孕妇、儿童或用药者应咨询专业人士", ["usage"]),
        ],
        "gaps": ["花椒麻味物质的定量", "不同产地/品种的系统对比", "烟点/耐热性数据", "书中“可诱发恶性肿瘤”说法的现代毒理学验证"],
    },
    {
        "id": "star-anise",
        "name": "八角",
        "english": "star anise",
        "domain": "cn",
        "category": ["调味品", "香辛料"],
        "role": ["卤", "炖", "增香"],
        "aliases": ["八角茴香", "大料", "大茴香"],
        "alias_keys": ["alias1", "alias2"],
        "one_line": "书中记其又称八角茴香、气味芳香而甜，传统属性辛温，常用于炖肉、卤煮与腌渍。",
        "evidence": [
            evidence("alias1", "CN-DIDAO-2011", 236, "又称八角茴香", printed=232, chapter="第八章 调味品"),
            evidence("alias2", "CN-DIDAO-2011", 236, "大料和大茴香", printed=232, chapter="第八章 调味品"),
            evidence("tcm", "CN-DIDAO-2011", 236, "性味:味辛,性温", printed=232, chapter="第八章 调味品"),
            evidence("func", "CN-DIDAO-2011", 236, "功效:温阳散寒,理气止痛", printed=232, chapter="第八章 调味品"),
            evidence("sensory1", "CN-DIDAO-2011", 236, "气味芳香而甜", printed=232, chapter="第八章 调味品"),
            evidence("sensory2", "CN-DIDAO-2011", 236, "具强烈香味", printed=232, chapter="第八章 调味品"),
            evidence("cook", "CN-DIDAO-2011", 236, "煮、炸、卤、酱及烧等烹调加", printed=232, chapter="第八章 调味品", confidence="low"),
            evidence("prep", "CN-DIDAO-2011", 236, "或磨粉使用", printed=232, chapter="第八章 调味品"),
            evidence("pair1", "CN-DIDAO-2011", 236, "将八角与肉一同", printed=232, chapter="第八章 调味品", confidence="low"),
            evidence("pair2", "CN-DIDAO-2011", 236, "放入八角则会", printed=232, chapter="第八章 调味品", confidence="low"),
            evidence("claim", "CN-DIDAO-2011", 236, "能刺激胃肠神经血", printed=232, chapter="第八章 调味品", confidence="low"),
        ],
        "origin": [],
        "varieties": [],
        "season": "",
        "season_keys": [],
        "quality": [],
        "aroma": (["芳香", "甜", "强烈香味"], "high", ["sensory1", "sensory2"]),
        "taste": (["辛"], "unknown", ["tcm"]),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": True,
            "nature": "温",
            "flavor": "辛",
            "meridians": None,
            "notes": ("书中记“味辛，性温”，功效温阳散寒、理气止痛；属传统理论。", ["tcm", "func"]),
            "functions": ["温阳散寒（传统）", "理气止痛（传统）"],
            "uses": ["炖肉", "卤味", "腌渍", "煮蛋"],
            "keys": ["tcm", "func"],
        },
        "cook": ["煮", "炸", "卤", "酱", "烧", "磨粉"],
        "prep": [("整颗或磨粉使用", ["prep"])],
        "heat": ("书未给温度；整颗耐炖，磨粉后易失香（烹饪提示）。", ["prep"]),
        "pairings": [
            ("肉类", "书中“炖肉时，将八角与肉一同下锅”", ["pair1"]),
            ("鸡蛋、鸭蛋", "书中煮蛋时放入八角", ["pair2"]),
        ],
        "subs": [],
        "storage": [],
        "safety": [
            ("书未给明确禁忌；作为香辛料不宜大量（按原书语境提示）", []),
            ("书中“刺激胃肠神经血管”等表述属传统/通俗描述，不是现代临床结论", ["claim"]),
        ],
        "gaps": ["产地/品种", "选购标准", "替代方案", "现代安全性数据"],
    },
    {
        "id": "tomato",
        "name": "番茄",
        "english": "tomato",
        "domain": "dk",
        "category": ["蔬菜", "茄果类"],
        "role": ["生食", "烤", "炒", "制酱", "汤"],
        "aliases": [],
        "alias_keys": [],
        "one_line": "书中记番茄品种多样、夏到初秋为高产期，可生食、烤、炒、煎、炖、制酱，并列出多种香草与奶酪搭配。",
        "evidence": [
            evidence("name", "DK-INGREDIENTS", 270, "番茄(tomato)"),
            evidence("variety1", "DK-INGREDIENTS", 270, "球形番茄(globetomatoes)"),
            evidence("variety2", "DK-INGREDIENTS", 270, "樱桃番茄(cherrytomatoes)"),
            evidence("variety3", "DK-INGREDIENTS", 270, "牛排番茄(beefsteaktomato)"),
            evidence("variety4", "DK-INGREDIENTS", 270, "李子番茄(plumtomatoes)"),
            evidence("season", "DK-INGREDIENTS", 270, "番茄的高产期是在夏天到初秋时节"),
            evidence("quality1", "DK-INGREDIENTS", 270, "要寻找那些成熟的番茄,这样的番茄味道最佳"),
            evidence("quality2", "DK-INGREDIENTS", 270, "其质地应硬实"),
            evidence("storage", "DK-INGREDIENTS", 270, "番茄要在室温下存放,不要放到冰箱内储存"),
            evidence("cook1", "DK-INGREDIENTS", 270, "番茄可以整个的烤"),
            evidence("cook2", "DK-INGREDIENTS", 270, "可以铁、炒、煎,或者炖等"),
            evidence("cook3", "DK-INGREDIENTS", 270, "可以用来制作沙司或者汤菜"),
            evidence("cook4", "DK-INGREDIENTS", 270, "腌制时:烘干之后可以浸泡到橄榄油里"),
            evidence("pair", "DK-INGREDIENTS", 270, "帕玛森干酪,马祖丽娜干酪,罗勒,大蒜,洋葱,青葱,香芹,甘蓝,香脂醋,牛至,百里香,马郁兰等"),
            evidence("sensory1", "DK-INGREDIENTS", 270, "酸甜适口,质地多汁"),
            evidence("sensory2", "DK-INGREDIENTS", 270, "甘甜多汁"),
            evidence("sensory3", "DK-INGREDIENTS", 270, "肉质硬实"),
            evidence("cook5", "DK-INGREDIENTS", 271, "小火炖大约20分钟"),
        ],
        "origin": [],
        "varieties": [
            ("球形番茄", ["variety1"]),
            ("樱桃番茄", ["variety2"]),
            ("牛排番茄", ["variety3"]),
            ("李子番茄", ["variety4"]),
        ],
        "season": "高产期：夏天到初秋",
        "season_keys": ["season"],
        "quality": [
            ("成熟番茄味道最佳", ["quality1"]),
            ("非当季番茄应质地硬实、表面无瑕疵（OCR 作“瑕癌”，待复核）", ["quality2"]),
        ],
        "aroma": ([], "unknown", []),
        "taste": (["酸甜"], "high", ["sensory1", "sensory2"]),
        "texture": (["多汁", "肉质硬实"], "high", ["sensory1", "sensory3"]),
        "tcm": {
            "applicable": False,
            "nature": None,
            "flavor": None,
            "meridians": None,
            "notes": "《中药学》未收番茄；无传统四气五味依据。",
            "functions": [],
            "uses": [],
            "keys": [],
        },
        "cook": ["生食", "烤", "炒", "煎", "炖", "制沙司/汤", "腌渍/烘干"],
        "prep": [("去籽切碎（鳄梨酱）", ["cook4"]), ("去皮切碎（番茄沙司）", ["cook5"])],
        "heat": ("书中番茄沙司小火炖约 20 分钟；未给温度。", ["cook5"]),
        "pairings": [
            ("帕玛森干酪、马祖丽娜干酪、罗勒、大蒜、洋葱、青葱、香芹、甘蓝、香脂醋、牛至、百里香、马郁兰", "书中“搭配各种风味”", ["pair"]),
        ],
        "subs": [],
        "storage": [("室温存放，避免相互接触；熟透后才可冷藏", ["storage"])],
        "safety": [
            ("对番茄过敏者避免（通用提示，非四书依据）", []),
            ("未成熟绿番茄的龙葵碱风险，书未展开，标缺口", []),
        ],
        "gaps": ["具体品种的糖酸比", "产地", "番茄红素等营养数据", "绿番茄安全性"],
    },
    {
        "id": "sea-bream",
        "name": "鲷鱼",
        "english": "sea bream / snapper",
        "domain": "dk",
        "category": ["水产", "鱼类"],
        "role": ["主料"],
        "aliases": ["红鲷鱼", "真鲷（OCR 作“真纳”）"],
        "alias_keys": ["variety1", "variety4"],
        "one_line": "书中记鲷鱼鱼肉多为浅白色、加热后变白，适合蒸、煎、铁扒、烘烤、炒；并给出海鲈鱼、石斑鱼替代。",
        "evidence": [
            evidence("name", "DK-INGREDIENTS", 41, "鲷鱼(snapper)", printed=136, chapter="鱼类和海鲜类"),
            evidence("origin", "DK-INGREDIENTS", 41, "在世界各地的热带水域中均可以见到它们的身影", printed=136, chapter="鱼类和海鲜类"),
            evidence("variety1", "DK-INGREDIENTS", 41, "红鲷鱼", printed=136, chapter="鱼类和海鲜类"),
            evidence("variety2", "DK-INGREDIENTS", 41, "巴哈马笛鲷", printed=136, chapter="鱼类和海鲜类"),
            evidence("variety3", "DK-INGREDIENTS", 41, "黄尾笛鲷", printed=136, chapter="鱼类和海鲜类"),
            evidence("quality", "DK-INGREDIENTS", 41, "整条售卖的鱼在加热烹调之前,需要经过修剪、去掉鱼鳞以及内脏", printed=136, chapter="鱼类和海鲜类"),
            evidence("sensory1", "DK-INGREDIENTS", 41, "在加热烹调的过程中会变成白色", printed=136, chapter="鱼类和海鲜类"),
            evidence("sensory2", "DK-INGREDIENTS", 41, "有着甘美的美好滋味", printed=136, chapter="鱼类和海鲜类"),
            evidence("cook", "DK-INGREDIENTS", 41, "可以蒸、煎、铁扒、烘烤、炒等", printed=136, chapter="鱼类和海鲜类"),
            evidence("prep", "DK-INGREDIENTS", 41, "可以是整条、可以剔取鱼肉、切割成鱼排等", printed=136, chapter="鱼类和海鲜类"),
            evidence("sub", "DK-INGREDIENTS", 41, "下列鱼类可以用来代替它们:海鲈鱼、石斑鱼等", printed=136, chapter="鱼类和海鲜类"),
            evidence("pair", "DK-INGREDIENTS", 41, "香油、酱油、姜、大、香菜、棕榈糖、泰国鱼汁等", printed=136, chapter="鱼类和海鲜类"),
            evidence("safety", "DK-INGREDIENTS", 41, "部分地区属于濒临灭绝的鱼类", printed=136, chapter="鱼类和海鲜类"),
            evidence("variety4", "DK-INGREDIENTS", 30, "red sea bream", printed=25, chapter="鱼类和海鲜类"),
            evidence("variety5", "DK-INGREDIENTS", 30, "牙鲷(dentex)", printed=25, chapter="鱼类和海鲜类"),
            evidence("heat1", "DK-INGREDIENTS", 30, "将烤箱预热至210°C", printed=25, chapter="鱼类和海鲜类"),
            evidence("heat2", "DK-INGREDIENTS", 30, "放入烤箱烘烤12~15分钟", printed=25, chapter="鱼类和海鲜类"),
            evidence("heat3", "DK-INGREDIENTS", 30, "肉质变得硬实而不透明", printed=25, chapter="鱼类和海鲜类"),
        ],
        "origin": [("世界各地的热带水域（不同种）", ["origin"])],
        "varieties": [
            ("红鲷鱼", ["variety1"]),
            ("巴哈马笛鲷", ["variety2"]),
            ("黄尾笛鲷", ["variety3"]),
            ("真鲷（书中英文 red sea bream，OCR 作“真纳”）", ["variety4"]),
            ("牙鲷", ["variety5"]),
        ],
        "season": "",
        "season_keys": [],
        "quality": [("整条售卖需修剪、去鳞、去内脏", ["quality"])],
        "aroma": ([], "unknown", []),
        "taste": (["甘美"], "medium", ["sensory2"]),
        "texture": (["肉质洁白", "硬实"], "medium", ["sensory1", "heat3"]),
        "tcm": {
            "applicable": False,
            "nature": None,
            "flavor": None,
            "meridians": None,
            "notes": "《中药学》未收鲷鱼；无传统四气五味依据。",
            "functions": [],
            "uses": [],
            "keys": [],
        },
        "cook": ["蒸", "煎", "铁扒", "烘烤", "炒", "纸包烤"],
        "prep": [("去鳞、去内脏；整条/鱼排/鱼肉", ["quality", "prep"])],
        "heat": ("书中纸包海鲷鱼：烤箱 210°C，烤 12~15 分钟至鱼肉硬实不透明。", ["heat1", "heat2", "heat3"]),
        "pairings": [
            ("香油、酱油、姜、大蒜、香菜、棕榈糖、泰国鱼汁、柠檬/青柠", "书中“搭配各种风味”（OCR“大”应为“大蒜”）", ["pair"]),
        ],
        "subs": [
            ("海鲈鱼", "书中列为可替代鱼类", ["sub"]),
            ("石斑鱼", "书中列为可替代鱼类", ["sub"]),
        ],
        "storage": [],
        "safety": [
            ("鱼类过敏原（通用提示，非四书依据）", []),
            ("生食水产有寄生虫/微生物风险；书未给生食安全参数", []),
            ("书中提示部分鲷鱼捕捞过度/濒危，选择时关注可持续性", ["safety"]),
        ],
        "gaps": ["各品种的精确风味差异", "中心温度安全阈值", "产地季节", "储存条件"],
    },
    {
        "id": "olive-oil",
        "name": "橄榄油",
        "english": "olive oil",
        "domain": "dk",
        "category": ["油脂", "调味品"],
        "role": ["烹饪介质", "沙拉酱", "蘸酱", "增香"],
        "aliases": ["特级初榨橄榄油", "初榨橄榄油"],
        "alias_keys": ["evoo"],
        "one_line": "书中按品种与产地描述橄榄油的果香、苦涩与胡椒风味；《盐，脂，酸，热》补充了变质判断与避光储存。",
        "evidence": [
            evidence("variety1", "DK-INGREDIENTS", 516, "TondaIbleaoil"),
            evidence("variety2", "DK-INGREDIENTS", 516, "Picualvarietaloil"),
            evidence("variety3", "DK-INGREDIENTS", 516, "克拉缇娜橄榄油(Coratinavarietaloil)"),
            evidence("variety4", "DK-INGREDIENTS", 516, "莱钦橄榄油(Leccinovarietaloil)"),
            evidence("variety5", "DK-INGREDIENTS", 516, "佛良多依奥橄概油(Frantoiovarietaloil)"),
            evidence("variety6", "DK-INGREDIENTS", 516, "克罗内基混合橄榄油(Koroneikivarietalblend)"),
            evidence("evoo", "DK-INGREDIENTS", 516, "特级初榨橄榄油"),
            evidence("origin1", "DK-INGREDIENTS", 516, "这种西西里岛出产的橄榄油"),
            evidence("origin2", "DK-INGREDIENTS", 516, "原产于安达卢西亚的哈恩地区"),
            evidence("sensory1", "DK-INGREDIENTS", 516, "有着番茄的滋味,带有香草的回味和中度的苦涩感与胡椒风味"),
            evidence("sensory2", "DK-INGREDIENTS", 516, "有着浓郁的苦涩和胡椒风味"),
            evidence("cook", "DK-INGREDIENTS", 516, "可以用作菌酱或者用于沙拉、鸡肉、羊肉以及蔬菜类菜肴中"),
            evidence("defect1", "FS-SFAH-2023", 58, "苦涩、过于辛辣、混浊、陈腐,这些都是致命的缺点"),
            evidence("defect2", "FS-SFAH-2023", 58, "橄榄油的色泽与品质几乎没有关系"),
            evidence("defect3", "FS-SFAH-2023", 58, "你的橄榄油闻起来像不像蜡笔或蜡烛?"),
            evidence("defect4", "FS-SFAH-2023", 58, "那么你的橄榄油已经变质了"),
            evidence("storage", "FS-SFAH-2023", 59, "请将橄榄油贮存在温度较低的遮光处"),
            evidence("shelf", "FS-SFAH-2023", 58, "橄榄油会在压榨后12至14个月内变质"),
        ],
        "origin": [
            ("西西里岛（Tonda Iblea 示例）", ["origin1"]),
            ("西班牙安达卢西亚哈恩地区（Picual 示例）", ["origin2"]),
        ],
        "varieties": [
            ("Tonda Iblea", ["variety1"]),
            ("Picual", ["variety2"]),
            ("Coratina", ["variety3"]),
            ("Leccino", ["variety4"]),
            ("Frantoio", ["variety5"]),
            ("Koroneiki", ["variety6"]),
        ],
        "season": "",
        "season_keys": [],
        "quality": [
            ("劣质橄榄油：苦涩、过于辛辣、混浊、陈腐", ["defect1"]),
            ("色泽与品质几乎无关", ["defect2"]),
            ("闻起来像蜡笔/蜡烛或陈旧花生酱表层油脂味，说明已变质", ["defect3", "defect4"]),
        ],
        "aroma": (["果香", "香草", "胡椒"], "high", ["sensory1"]),
        "taste": (["苦涩", "辛辣"], "high", ["sensory1", "sensory2"]),
        "texture": ([], "unknown", []),
        "tcm": {
            "applicable": False,
            "nature": None,
            "flavor": None,
            "meridians": None,
            "notes": "《中药学》未收橄榄油；无传统四气五味依据。",
            "functions": [],
            "uses": [],
            "keys": [],
        },
        "cook": ["沙拉", "蘸酱", "意面", "烤/煎肉类", "蔬菜"],
        "prep": [("品尝选油；避免高温加热到冒烟（烹饪提示，书未给烟点）", [])],
        "heat": ("书未给烟点；只说不同油耐热性不同，标缺口。", []),
        "pairings": [
            ("番茄、罗勒、硬质干酪、烤蔬菜、鸡肉/羊肉", "书中搭配与用途", ["cook", "sensory1"]),
        ],
        "subs": [],
        "storage": [("低温、遮光；暗色玻璃瓶或金属瓶", ["storage"]), ("压榨后 12~14 个月内变质，不宜长期存放", ["shelf"])],
        "safety": [
            ("油脂过敏少见但存在（通用提示，非四书依据）", []),
            ("高血脂/高血压人群的用油建议需专业指导，书未给", []),
        ],
        "gaps": ["烟点/耐热温度", "酸度/过氧化值标准", "每日推荐摄入量"],
    },
    {
        "id": "butter",
        "name": "黄油",
        "english": "butter",
        "domain": "dk",
        "category": ["乳制品", "油脂"],
        "role": ["烘焙", "煎", "酱汁", "增香"],
        "aliases": [],
        "alias_keys": [],
        "one_line": "书中记法国黄油适合烘焙、风味细腻、乳脂质感浓郁；《盐，脂，酸，热》解释其融化后水油分离，澄清黄油耐热性更高。",
        "evidence": [
            evidence("dk_sensory", "DK-INGREDIENTS", 376, "法国黄油非常适合用来烘焙,在其非常细腻的风味中有着浓郁的乳脂状的质地"),
            evidence("clarify1", "DK-INGREDIENTS", 370, "澄清黄油这是一种去掉水分和杂质奶之后的黄油"),
            evidence("clarify2", "DK-INGREDIENTS", 370, "因为澄清黄油比普通黄油的燃点要高得多"),
            evidence("storage", "DK-INGREDIENTS", 370, "箱内储存几周的时间"),
            evidence("whip", "DK-INGREDIENTS", 370, "搅打奶油"),
            evidence("melt", "FS-SFAH-2023", 70, "黄油从冷冻温度(0摄氏度)一直到融化温度(32~35摄氏度)都能保持固态"),
            evidence("separate", "FS-SFAH-2023", 70, "黄油超过融化温度后,水分会随着油脂的融化而分离"),
            evidence("emulsion", "FS-SFAH-2023", 70, "融化的黄油是一种分离了的乳浊液"),
        ],
        "origin": [("法国（书中示例）", ["dk_sensory"])],
        "varieties": [("普通黄油", ["dk_sensory"]), ("澄清黄油", ["clarify1"])],
        "season": "",
        "season_keys": [],
        "quality": [],
        "aroma": (["乳香"], "unknown", ["dk_sensory"]),
        "taste": (["乳脂"], "high", ["dk_sensory"]),
        "texture": (["细腻", "浓郁", "乳脂状"], "high", ["dk_sensory"]),
        "tcm": {
            "applicable": False,
            "nature": None,
            "flavor": None,
            "meridians": None,
            "notes": "《中药学》未收黄油；无传统四气五味依据。",
            "functions": [],
            "uses": [],
            "keys": [],
        },
        "cook": ["烘焙", "澄清后作烹调用油"],
        "prep": [("软化/融化", ["melt"]), ("澄清：去水分与杂质", ["clarify1"])],
        "heat": ("书中：黄油在 32~35°C 融化；超过融化温度后水油分离；澄清黄油燃点更高。", ["melt", "separate", "clarify2"]),
        "pairings": [],
        "subs": [],
        "storage": [("冷藏；澄清黄油可在冰箱内储存数周", ["storage"])],
        "safety": [
            ("乳制品过敏/乳糖不耐受需注意（通用提示，非四书依据）", []),
            ("饱和脂肪摄入需适量；书未给营养建议", []),
        ],
        "gaps": ["烟点精确值", "不同产地黄油的系统对比", "营养数据", "风味搭配"],
    },
]


def build_json(spec: dict[str, Any]) -> dict[str, Any]:
    tcm = spec["tcm"]
    tcm_note = tcm["notes"]
    if isinstance(tcm_note, tuple):
        text, keys = tcm_note
        tcm_note = f"{text}（{cite(spec, keys)}）"
    if tcm["applicable"] and tcm_note and "非现代医学证据" not in tcm_note and "不是现代医学证据" not in tcm_note:
        tcm_note = tcm_note + "；传统理论，非现代医学证据。"

    def claim_list(items: list[tuple[str, list[str]]]) -> list[dict[str, Any]]:
        return [claim(spec, text, keys) for text, keys in items]

    season_note = None
    if spec.get("season"):
        season_note = f"书中记载：{spec['season']}"
        if spec.get("season_keys"):
            season_note += f"（{cite(spec, spec['season_keys'])}）"

    heat_text, heat_keys = spec["heat"] if isinstance(spec["heat"], tuple) else (spec["heat"], [])
    if heat_keys:
        heat_text = f"{heat_text}（{cite(spec, heat_keys)}）"

    safety = []
    for text, keys in spec["safety"]:
        if keys:
            text = f"{text}（{cite(spec, keys)}）"
        safety.append(text)

    sources = [ev_obj(e) for e in spec["evidence"]]
    # De-duplicate by (source, page, quote), preserving first appearance.
    seen = set()
    unique_sources = []
    for e in sources:
        k = (e["source_id"], e["pdf_page"], e["quote"])
        if k not in seen:
            seen.add(k)
            unique_sources.append(e)

    return {
        "id": spec["id"],
        "basic": {
            "canonical_name_zh": spec["name"],
            "scientific_name": None,
            "english_name": spec["english"],
            "one_line_definition": spec["one_line"],
            "research_status": "partial",
        },
        "names": {
            "aliases": [e for e in spec.get("aliases", [])],
            "alias_evidence": resolve(spec, spec.get("alias_keys", [])),
        },
        "category": {"taxonomy": spec["category"], "culinary_role": spec["role"]},
        "origin_variety": {
            "origins": claim_list(spec["origin"]),
            "varieties": claim_list(spec["varieties"]),
            "notes": None,
        },
        "seasonality": {"peak_season": spec["season"] or None, "availability": None, "notes": season_note},
        "appearance_quality": {
            "traits": claim_list(spec["quality"]),
            "grading": [],
            "notes": None,
        },
        "aroma": sensory(spec, *spec["aroma"]),
        "taste": sensory(spec, *spec["taste"]),
        "texture": sensory(spec, *spec["texture"]),
        "tcm_attributes": {
            "applicable": bool(tcm["applicable"]),
            "nature": tcm["nature"],
            "flavor": tcm["flavor"],
            "meridians": tcm["meridians"],
            "notes": tcm_note,
        },
        "tcm_applications": {
            "functions": tcm["functions"],
            "traditional_uses": tcm["uses"],
            "theory_basis": "《中药学》/《中国地道食材图录大全》传统记载" if tcm["functions"] else None,
            "evidence": resolve(spec, tcm["keys"]),
        },
        "culinary_uses": {
            "methods": spec["cook"],
            "preparation": [text for text, _ in spec["prep"]],
            "heat_notes": heat_text,
        },
        "flavor_pairings": [
            {"with": name, "reason": reason, "evidence": resolve(spec, keys)}
            for name, reason, keys in spec["pairings"]
        ],
        "substitutes": [
            {"name": name, "difference": difference, "evidence": resolve(spec, keys)}
            for name, difference, keys in spec["subs"]
        ],
        "processing_storage": {
            "processing": claim_list([(t, k) for t, k in spec["prep"] if k]),
            "storage": claim_list(spec["storage"]),
            "shelf_life": None,
        },
        "safety": {
            "allergens": [],
            "contraindications": safety,
            "toxicity": None,
            "food_safety": [],
            "at_risk_groups": [],
        },
        "sources": unique_sources,
        "gaps": spec["gaps"],
    }


def build_md(spec: dict[str, Any], card: dict[str, Any]) -> str:
    lines = [
        f"# {spec['name']}",
        "",
        f"> 卡片状态：partial · 证据 {len(card['sources'])} 条 · 四书知识库",
        "> 传统属性 ≠ 现代医学证据；缺依据的字段明确标为缺口。",
        "> 本卡由 `scripts/build_ingredient_cards.py` 生成；每条引文均已回查页面文本。",
        "",
        "## 一句话",
        spec["one_line"],
        "",
        "## 证据表",
        "",
        "| ID | 书名 | 页码 | 原文摘录 | 可信度 |",
        "|---|---|---|---|---|",
    ]
    for i, e in enumerate(card["sources"], 1):
        page = f"p.{e['printed_page']}（PDF {e['pdf_page']}）" if e["printed_page"] else f"PDF {e['pdf_page']}"
        quote = e["quote"].replace("|", "\\|")
        lines.append(f"| E{i} | 《{e['book_title']}》 | {page} | {quote} | {e['confidence']} |")

    lines += [
        "",
        "## 基础信息",
        f"- 英文名：{spec['english']}",
        f"- 分类：{' / '.join(spec['category'])}",
        f"- 烹饪角色：{' / '.join(spec['role'])}",
        f"- 别名：{'、'.join(spec.get('aliases', [])) or '—'}",
        "",
        "## 产地与品种",
    ]
    if spec["origin"]:
        lines += [f"- {t}" for t, _ in spec["origin"]]
    else:
        lines.append("- 当前四本书知识库暂无充分依据。")
    if spec["varieties"]:
        lines += ["- 品种：" + "；".join(t for t, _ in spec["varieties"])]
    else:
        lines.append("- 品种：当前四本书知识库暂无充分依据。")

    lines += ["", "## 季节与品质", f"- 季节：{spec['season'] or '—'}"]
    if spec["quality"]:
        lines += [f"- {t}" for t, _ in spec["quality"]]
    else:
        lines.append("- 品质分级：当前四本书知识库暂无充分依据。")

    def sensory_line(label: str, item: tuple[list[str], str, list[str]]) -> str:
        desc, intensity, _ = item
        return f"- {label}：{'、'.join(desc) or '—'}（强度 {intensity}）"

    lines += [
        "",
        "## 香气 / 味道 / 口感",
        sensory_line("香气", spec["aroma"]),
        sensory_line("味道", spec["taste"]),
        sensory_line("口感", spec["texture"]),
        "",
        "## 传统本草属性",
    ]
    tcm = spec["tcm"]
    if tcm["applicable"]:
        lines += [
            f"- 性味：{tcm['flavor'] or '—'} / {tcm['nature'] or '—'}",
            f"- 归经：{tcm['meridians'] or '—'}",
            f"- 功效：{'；'.join(tcm['functions']) or '—'}",
            "- 说明：以上为传统理论/书中食疗表述，不是现代医学疗效证据。",
        ]
    else:
        lines.append("- 不适用：四书未收该食材的本草条目，无传统四气五味依据。")

    lines += ["", "## 烹饪方式", "、".join(spec["cook"])]
    if spec["prep"]:
        lines.append("")
        lines.append("预处理：" + "；".join(t for t, _ in spec["prep"]))
    if spec["heat"]:
        lines.append("")
        lines.append(f"火候/温度：{spec['heat'][0] if isinstance(spec['heat'], tuple) else spec['heat']}")

    lines += ["", "## 风味搭配"]
    if spec["pairings"]:
        lines += [f"- {name}：{reason}" for name, reason, _ in spec["pairings"]]
    else:
        lines.append("- 当前四本书知识库暂无充分依据。")

    lines += ["", "## 替代方案"]
    if spec["subs"]:
        lines += [f"- {name}：{difference}" for name, difference, _ in spec["subs"]]
    else:
        lines.append("- 当前四本书知识库暂无充分依据。")

    lines += ["", "## 加工与保存"]
    if spec["storage"]:
        lines += [f"- {text}" for text, _ in spec["storage"]]
    else:
        lines.append("- 当前四本书知识库暂无充分依据。")

    lines += ["", "## 安全与禁忌"]
    if spec["safety"]:
        lines += [f"- {text}" for text, _ in spec["safety"]]
    else:
        lines.append("- 当前四本书知识库暂无充分依据。")

    lines += ["", "## 知识缺口"] + [f"- {x}" for x in spec["gaps"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    made = []
    index = []
    for spec in SPECS:
        card = build_json(spec)
        out_json = INGREDIENTS_DIR / f"{spec['id']}.json"
        out_json.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        out_md = (REF_CN if spec["domain"] == "cn" else REF_DK) / f"{spec['name']}.md"
        out_md.write_text(build_md(spec, card), encoding="utf-8")
        made.append(spec["name"])
        index.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "english": spec["english"],
                "domain": spec["domain"],
                "sources": sorted({e["source_id"] for e in spec["evidence"]}),
                "evidence_count": len(card["sources"]),
                "gaps": len(spec["gaps"]),
            }
        )
    (INGREDIENTS_DIR / "_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cards": len(made), "names": made, "index": str(INGREDIENTS_DIR / "_index.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
