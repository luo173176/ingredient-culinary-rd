"""Build the query-normalisation lexicon from book-evidenced aliases + hints.

The lexicon has two clearly separated parts:
- `aliases`: surface forms used to find the same ingredient in the books.
- `evidence`: the page where an alias was explicitly stated, when available.

Query hints are marked and are never used as factual evidence.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, DATA, PAGES_DIR, load_json, save_json  # noqa: E402

CATEGORY_RULES = [
    ("谷物", "米 面 麦 稻 谷 豆 薯 玉米 燕麦 荞麦 高粱 粟 黍 薏苡"),
    ("蔬菜", "菜 瓜 茄 椒 葱 蒜 姜 萝卜 笋 藕 芹 韭 菠菜 生菜 莴 秋葵 荸荠 山药 芋"),
    ("水果", "果 橙 柚 橘 柑 柠檬 香蕉 菠萝 芒果 葡萄 桃 梨 杏 枣 莓 瓜"),
    ("坚果种子", "仁 坚果 核桃 栗 花生 芝麻 腰果 开心果 松子 榛"),
    ("肉", "牛 猪 羊 鸡 鸭 鹅 肉 火腿 香肠"),
    ("水产", "鱼 虾 蟹 贝 蛤 蚝 牡蛎 扇贝 鱿 章鱼 海带 紫菜 海参"),
    ("乳蛋", "奶 乳 蛋 奶酪 黄油 酸奶"),
    ("调味", "盐 糖 醋 酱 油 酒 椒 茴 桂 丁香 草果 砂仁 豆蔻 陈皮 味精 蜂蜜"),
    ("本草", "药 草 根 叶 花 子 皮 苓 术 参 芪 归 芍 地 黄 天 冬 麦 斛 玉竹 黄精"),
]

ALIAS_PATTERNS = [
    re.compile(r"([\u4e00-\u9fa5]{2,6})(?:又名|又称|俗称|亦称)([^。；;\n]{2,40})"),
    re.compile(r"([\u4e00-\u9fa5]{2,6})别名[：:]\s*([^。；;\n]{2,40})"),
]
BAD_CANON = {"本品", "药材", "中药", "食物", "原料", "食材", "别名", "又名", "又称", "俗称"}
BAD_ALIAS = {"一种", "一种食品", "一种食材", "我国", "人们", "民间", "此", "其", "为", "是"}


def classify(name: str, is_herb: bool) -> str:
    if is_herb:
        return "本草"
    for cat, words in CATEGORY_RULES:
        if any(w and w in name for w in words.split()):
            return cat
    return "未分类"


def clean_alias(raw: str) -> list[str]:
    raw = re.sub(r"[“”‘’\"'（）()]", "", raw)
    parts = re.split(r"[、，,和及/]", raw)
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"^(一种|一种食品|一种食材|我国|人们|民间)", "", p)
        if 2 <= len(p) <= 8 and p not in BAD_ALIAS and not re.search(r"\d", p):
            out.append(p)
    return out


def mine_aliases(pages: list[dict[str, Any]], source_id: str) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    for page in pages:
        text = page.get("text") or ""
        for pat in ALIAS_PATTERNS:
            for m in pat.finditer(text):
                canon = m.group(1).strip()
                if canon in BAD_CANON or not (2 <= len(canon) <= 6):
                    continue
                aliases = clean_alias(m.group(2))
                if not aliases:
                    continue
                rec = {
                    "source_id": source_id,
                    "pdf_page": page["pdf_page"],
                    "printed_page": page.get("printed_page"),
                    "quote": text[max(0, m.start() - 20) : m.end() + 20].replace("\n", " ")[:160],
                }
                for a in aliases:
                    found.setdefault(canon, []).append({"alias": a, **rec})
    return found


def main() -> None:
    herbs = []
    hp = DATA / "herbs.jsonl"
    if hp.exists():
        herbs = [json.loads(line) for line in open(hp, encoding="utf-8")]
    herb_names = {h["name"] for h in herbs if not h.get("is_attached")}

    hints = load_json(CONFIG / "query_hints.json", {"aliases": {}})
    entries: dict[str, dict[str, Any]] = {}

    def add(canon: str, alias: str, evidence: dict[str, Any] | None, kind: str) -> None:
        e = entries.setdefault(
            canon,
            {
                "canonical": canon,
                "aliases": [],
                "category": classify(canon, canon in herb_names),
                "sources": [],
                "evidence": [],
                "alias_kind": "book_evidenced" if kind == "book" else "query_hint",
            },
        )
        if alias and alias != canon and alias not in e["aliases"]:
            e["aliases"].append(alias)
        if evidence:
            e["sources"].append(evidence["source_id"])
            e["evidence"].append(evidence)
            e["alias_kind"] = "book_evidenced"

    for canon, aliases in hints.get("aliases", {}).items():
        for a in aliases:
            add(canon, a, None, "hint")

    for page_file in sorted(PAGES_DIR.glob("*.jsonl")):
        source_id = page_file.stem.split(".")[0]
        pages = [json.loads(line) for line in open(page_file, encoding="utf-8")]
        for canon, recs in mine_aliases(pages, source_id).items():
            for rec in recs:
                add(canon, rec["alias"], {k: rec[k] for k in ("source_id", "pdf_page", "printed_page", "quote")}, "book")

    for h in herbs:
        if h.get("is_attached"):
            continue
        entries.setdefault(
            h["name"],
            {
                "canonical": h["name"],
                "aliases": [],
                "category": "本草",
                "sources": ["MM-ZYX-2016"],
                "evidence": [{"source_id": "MM-ZYX-2016", "pdf_page": h["pdf_start"], "printed_page": None, "quote": f"{h['name']}（{h['classical_source'] or '中药学'}）"}],
                "alias_kind": "book_evidenced",
            },
        )

    out = {
        "schema_version": "1.0",
        "role": "query_normalization",
        "note": "book_evidenced 别名有原文页码；query_hint 仅用于检索归一化，不作为事实依据。",
        "entries": sorted(entries.values(), key=lambda x: x["canonical"]),
    }
    save_json(CONFIG / "ingredient_lexicon.json", out)
    print(
        json.dumps(
            {
                "entries": len(entries),
                "book_evidenced": sum(1 for e in entries.values() if e["alias_kind"] == "book_evidenced"),
                "with_aliases": sum(1 for e in entries.values() if e["aliases"]),
                "aliases": sum(len(e["aliases"]) for e in entries.values()),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
