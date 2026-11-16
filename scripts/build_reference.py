"""Generate cite-backed reference pages from structured records.

Outputs:
- references/materia-medica/herb-index.md (all main monographs)
- references/materia-medica/herbs/*.md (selected food-adjacent herbs)

The generated cards are explicitly marked as auto-compiled excerpts, not
clinical advice and not a substitute for reading the source page.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, ROOT  # noqa: E402

REF = ROOT / "references" / "materia-medica"
HERB_DIR = REF / "herbs"
HERB_DIR.mkdir(parents=True, exist_ok=True)

SELECTED = [
    "生姜", "干姜", "葱白", "紫苏叶", "薄荷", "菊花", "山楂", "陈皮",
    "砂仁", "豆蔻", "草果", "花椒", "胡椒", "小茴香", "八角茴香", "肉桂",
    "高良姜", "丁香", "茯苓", "薏苡仁", "赤小豆", "大枣", "蜂蜜", "枸杞子",
    "桑椹", "龙眼肉", "百合", "莲子", "芡实", "山药", "甘草", "黄芪",
    "当归", "麦冬", "玉竹", "黄精", "乌梅", "五味子", "鸡内金", "莱菔子", "麦芽",
]


def clean(s: str | None, limit: int = 1200) -> str:
    if not s:
        return ""
    s = re.sub(r"\n{2,}", "\n", s.strip())
    if len(s) > limit:
        s = s[:limit].rstrip() + "……"
    return s


def cite(h: dict[str, Any]) -> str:
    return f"《中药学》PDF {h['pdf_start']}–{h['pdf_end']}，{h['chapter']}" + (
        f"·{h['section']}" if h.get("section") else ""
    ) + f"，{h['name']}条。"


def card(h: dict[str, Any]) -> str:
    name = h["name"]
    lines = [
        f"# {name}",
        "",
        f"> {cite(h)}",
        "> 本卡由结构化字段自动汇编，原文为教材节选；**不是诊疗建议，不构成个体化用药指导**。",
        "> 传统理论 ≠ 现代医学证据。",
        "",
        "## 速览",
        f"- 拼音：{h.get('pinyin') or '—'}",
        f"- 最早出处（教材标注）：{h.get('classical_source') or '—'}",
        f"- 性味归经：{clean(h.get('nature_flavor_meridians'), 200) or '—'}",
        f"- 功效：{clean(h.get('efficacy'), 300) or '—'}",
        "",
        "## 传统应用（教材原文节选）",
        clean(h.get("applications"), 1400) or "—",
        "",
        "## 用法用量（教材原文，仅作信息）",
        clean(h.get("usage_dosage"), 500) or "—",
        "",
        "## 使用注意（教材原文）",
        clean(h.get("cautions"), 700) or "—",
        "",
        "## 现代研究（教材“现代研究”栏目转述）",
        f"**化学成分**：{clean(h.get('chemistry'), 600) or '—'}",
        "",
        f"**药理作用**：{clean(h.get('pharmacology'), 900) or '—'}",
        "",
        f"**不良反应/毒性**：{clean(h.get('adverse_reactions'), 600) or '—'}",
        "",
        "## 食材/烹饪使用",
        "- 本卡只整理《中药学》条目；具体烹饪用法、风味搭配、替代方案需另查《中国地道食材图录大全》《食材百科全书》或标为缺口。",
        "- `[跨来源推理]` 若要把本药用于菜谱，必须先确认它是否属于可食用/药食同源范围，并核对用量、炮制与禁忌。",
        "- `[知识库缺口]` 本卡不提供“适合哪类人吃”“吃多少”“能否长期吃”的个体化结论。",
        "",
        "## 安全边界",
        "- 教材用法用量是临床处方语境，不是烹饪用量。",
        "- 孕妇、哺乳期、儿童、肝肾功能不全、正在服用抗凝/降糖/降压等药物者，使用前请咨询医生或药师。",
        "- 有毒/峻烈药材不得作为日常食材；如本品在教材中标“有毒”，必须特别警示。",
        "",
        "## 复核",
        f"- 结构化置信度：{h.get('confidence')}",
        f"- 缺失字段：{', '.join(h.get('missing_fields') or []) or '无'}",
        "- 复核方式：`python scripts/search.py --herb " + name + "`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = [json.loads(line) for line in open(DATA / "herbs.jsonl", encoding="utf-8")]
    main_rows = [r for r in rows if not r.get("is_attached")]
    by_name = {r["name"]: r for r in rows}

    # Full index grouped by chapter.
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in main_rows:
        groups.setdefault(r["chapter"] or "未分章", []).append(r)
    order = []
    seen = set()
    for r in main_rows:
        c = r["chapter"] or "未分章"
        if c not in seen:
            seen.add(c)
            order.append(c)

    out = [
        "# 《中药学》单味药全量索引",
        "",
        "> 来源：《中药学》（钟赣生主编，第4版，中国中医药出版社，2016）。",
        f"> 共 {len(main_rows)} 条主条目（另有附药未列入本表）。页码为 PDF 页；该电子版无可观察的印刷页码。",
        "> 表中“功效”为教材原文摘录，属传统中医药理论，不是现代医学疗效结论。",
        "",
        "## 用法",
        "",
        "```bash",
        "python scripts/search.py --herb 花椒",
        "python scripts/search.py \"花椒 温中止痛\" --source MM-ZYX-2016",
        "```",
        "",
    ]
    for c in order:
        out += [f"## {c}", "", "| 药名 | 拼音 | 性味 | 功效 | PDF页 |", "|---|---|---|---|---:|"]
        for r in groups[c]:
            eff = clean(r["efficacy"], 120).replace("|", "／").replace("\n", " ")
            nat = clean(r["nature_flavor_meridians"], 60).replace("|", "／").replace("\n", " ")
            out.append(f"| {r['name']} | {r.get('pinyin') or ''} | {nat} | {eff} | {r['pdf_start']} |")
        out.append("")
    (REF / "herb-index.md").write_text("\n".join(out), encoding="utf-8")

    made = []
    for name in SELECTED:
        h = by_name.get(name)
        if not h:
            print(f"  ! missing herb: {name}")
            continue
        (HERB_DIR / f"{name}.md").write_text(card(h), encoding="utf-8")
        made.append(name)

    readme = [
        "# 药材卡（自动汇编）",
        "",
        "这些卡片由 `scripts/build_reference.py` 从 `data/herbs.jsonl` 自动生成：",
        "",
        "- 字段来自《中药学》目录定位 + 正则解析；",
        "- 每张卡标注 PDF 页范围、章节、缺失字段与复核命令；",
        "- **不是诊疗建议**；剂量为教材原文，不是给用户的用量；",
        "- 传统功效不等于现代医学疗效。",
        "",
        f"当前生成 {len(made)} 张：" + "、".join(made),
        "",
        "全量索引见 `../herb-index.md`。",
        "",
        "## 复核",
        "",
        "```bash",
        "python scripts/search.py --herb 生姜",
        "python scripts/search.py --page MM-ZYX-2016:153",
        "```",
    ]
    (HERB_DIR / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(json.dumps({"index_rows": len(main_rows), "cards": len(made)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
