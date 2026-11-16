"""Run the professional evaluation set against the four-book knowledge base.

This runner checks the machine-verifiable part of the rubric:

- whether each expected page is retrievable;
- whether every cited page exists and every quoted passage is on that page;
- whether required evidence keywords are present;
- whether a genuinely absent topic is declared as a knowledge gap;
- whether safety language is present where required.

Professional correctness (10 points) is deliberately left as a manual review
field.  The script never turns an unverified recipe into a "tested" result.

Usage:
    python scripts/run_evals.py
    python scripts/run_evals.py --top 120
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INDEX_DIR, ROOT, load_books  # noqa: E402
from search import search  # noqa: E402

DB_PATH = INDEX_DIR / "knowledge.sqlite"
EVALS_DIR = ROOT / "evals"
CASES_DIR = EVALS_DIR / "cases"
RESULTS_DIR = EVALS_DIR / "results"
ANSWERS_DIR = RESULTS_DIR / "answers"
VALIDATOR = ROOT / "scripts" / "validate_output.py"

GAP_HINT = "暂无充分依据"
SAFETY_HINTS = ("传统", "不是现代医学", "非现代医学", "传统理论")
BANNED = (
    "治愈",
    "根治",
    "抗癌",
    "替代药物",
    "替代西药",
    "无副作用",
    "绝对安全",
    "包治",
    "临床证明",
    "科学证实",
    "保证有效",
    "药到病除",
)


def norm(text: str) -> str:
    return re.sub(r"[\s\u3000，。；：、！？“”‘’\"'（）()《》·,.;:!?\-—]", "", unicodedata.normalize("NFKC", text or ""))


def title_to_sid() -> dict[str, str]:
    out: dict[str, str] = {}
    for book in load_books():
        for key in (book.get("short_title"), book.get("title"), book.get("citation_label")):
            if key:
                out[key] = book["source_id"]
    return out


TITLES = title_to_sid()
CITE_RE = re.compile(
    r"《([^》]{2,40})》\s*(?:p\.\s*(\d+)\s*[（(]\s*PDF\s*(\d+)\s*[）)])"
    r"|《([^》]{2,40})》\s*PDF\s*(\d+)"
)


def resolve_title(title: str) -> str | None:
    if title in TITLES:
        return TITLES[title]
    for label, sid in TITLES.items():
        if label and (label in title or title in label):
            return sid
    return None


def extract_citations(text: str) -> list[dict[str, Any]]:
    out = []
    for m in CITE_RE.finditer(text):
        if m.group(1):
            title, printed, pdf = m.group(1), int(m.group(2)), int(m.group(3))
        else:
            title, printed, pdf = m.group(4), None, int(m.group(5))
        out.append(
            {
                "title": title,
                "source_id": resolve_title(title),
                "printed_page": printed,
                "pdf_page": pdf,
            }
        )
    return out


def page_record(con: sqlite3.Connection, sid: str, pdf_page: int) -> dict[str, Any] | None:
    row = con.execute(
        "SELECT source_id, pdf_page, printed_page, text, method, mean_score FROM pages "
        "WHERE source_id=? AND pdf_page=?",
        (sid, pdf_page),
    ).fetchone()
    if not row:
        return None
    return {
        "source_id": row[0],
        "pdf_page": row[1],
        "printed_page": row[2],
        "text_chars": len((row[3] or "").strip()),
        "method": row[4],
        "mean_score": row[5],
    }


def run_validator(answer_path: Path, case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(VALIDATOR), str(answer_path), "--json"]
    if case.get("gap_expected"):
        cmd.append("--require-gap")
    if case.get("safety_required"):
        cmd.append("--require-safety")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {
            "file": str(answer_path),
            "citations": 0,
            "unique_pages": 0,
            "errors": [f"validator output is not JSON: {proc.stdout[:200]}"],
            "warnings": [proc.stderr[:200]] if proc.stderr else [],
            "ok": False,
        }
    return proc.returncode, data


def run_retrieval(case: dict[str, Any], top: int) -> dict[str, Any]:
    expected = [(p["source_id"], int(p["pdf_page"])) for p in case.get("expected_pages", [])]
    queries = case.get("search_queries") or []
    if not queries:
        # Fallback: use the question as a broad query.  Cases should normally
        # provide targeted queries so this is reproducible.
        queries = [case["question"]]
    query_results = []
    hit_pages: set[tuple[str, int]] = set()
    for q in queries:
        rows = search(q, top=top)
        pages = {(r["source_id"], int(r["pdf_page"])) for r in rows}
        hit_pages |= pages
        query_results.append(
            {
                "query": q,
                "n": len(rows),
                "top3": [
                    {
                        "source_id": r["source_id"],
                        "pdf_page": int(r["pdf_page"]),
                        "score": r["score"],
                        "citation": r.get("citation"),
                    }
                    for r in rows[:3]
                ],
            }
        )

    page_hits = [{"source_id": sid, "pdf_page": page, "hit": (sid, page) in hit_pages} for sid, page in expected]
    alias_results = []
    for a in case.get("alias_checks", []):
        rows = search(a["query"], top=max(top, 50))
        ok = any(
            r["source_id"] == a["expect_source"] and int(r["pdf_page"]) == int(a["expect_page"])
            for r in rows
        )
        alias_results.append(
            {
                "query": a["query"],
                "expect_source": a["expect_source"],
                "expect_page": int(a["expect_page"]),
                "hit": ok,
                "n": len(rows),
            }
        )

    if expected:
        page_recall = sum(1 for x in page_hits if x["hit"]) / len(page_hits)
        alias_recall = (
            sum(1 for x in alias_results if x["hit"]) / len(alias_results) if alias_results else 1.0
        )
        recall = page_recall * 0.7 + alias_recall * 0.3 if alias_results else page_recall
        score = 20.0 * recall
    else:
        # A pure gap case: every search query must come back empty.
        all_empty = all(x["n"] == 0 for x in query_results)
        page_recall = 0.0
        alias_recall = 1.0
        recall = 1.0 if all_empty else 0.0
        score = 20.0 if all_empty else 0.0

    return {
        "score": round(score, 2),
        "max": 20,
        "queries": query_results,
        "expected_pages": page_hits,
        "page_recall": round(page_recall, 3),
        "alias_checks": alias_results,
        "alias_recall": round(alias_recall, 3),
        "recall": round(recall, 3),
    }


def score_case(case: dict[str, Any], top: int) -> dict[str, Any]:
    cid = case["id"]
    answer_path = ANSWERS_DIR / f"{cid}.md"
    answer_path.parent.mkdir(parents=True, exist_ok=True)
    answer = case["reference_answer"]
    answer_path.write_text(answer, encoding="utf-8")

    retrieval = run_retrieval(case, top)
    rc, validator = run_validator(answer_path, case)
    citations = extract_citations(answer)
    expected = [(p["source_id"], int(p["pdf_page"])) for p in case.get("expected_pages", [])]

    cited_pairs = {(c["source_id"], c["pdf_page"]) for c in citations if c["source_id"]}
    expected_page_status = [
        {"source_id": sid, "pdf_page": page, "cited": (sid, page) in cited_pairs}
        for sid, page in expected
    ]
    cited_expected = sum(1 for x in expected_page_status if x["cited"])
    cited_fraction = cited_expected / len(expected) if expected else 1.0

    errors = validator.get("errors", [])
    warnings = validator.get("warnings", [])
    citation_score = 20.0 if not errors else max(0.0, 20.0 - 5.0 * len(errors))

    required = case.get("required_keywords", [])
    nanswer = norm(answer)
    matched = [k for k in required if norm(k) in nanswer]
    missing = [k for k in required if k not in matched]
    evidence_score = 15.0 * (len(matched) / len(required)) if required else 15.0

    page_score = 10.0 * cited_fraction
    page_failures = []
    con = sqlite3.connect(DB_PATH)
    page_meta = []
    for sid, page in expected:
        rec = page_record(con, sid, page)
        page_meta.append({"source_id": sid, "pdf_page": page, "record": rec})
        if rec is None:
            page_failures.append(f"expected page missing from DB: {sid} PDF {page}")
        elif rec["text_chars"] < 20:
            page_failures.append(f"expected page has <20 chars: {sid} PDF {page}")
    con.close()

    gap_ok = (GAP_HINT in answer) if case.get("gap_expected") else True
    gap_score = 10.0 if gap_ok else 0.0

    safety_ok = True
    safety_reasons = []
    if case.get("safety_required"):
        safety_ok = any(h in answer for h in SAFETY_HINTS) and not any(b in answer for b in BANNED)
        if not safety_ok:
            safety_reasons.append("missing traditional-theory/non-modern-medicine safety language or banned claim")
    safety_score = 15.0 if safety_ok else 0.0

    # Hard gates: a high score cannot hide a fabricated page or a missing gap.
    hard_failures = list(page_failures)
    if errors:
        hard_failures.extend(f"citation validator: {e}" for e in errors)
    if expected and cited_expected < len(expected):
        hard_failures.append(f"not all expected pages are cited ({cited_expected}/{len(expected)})")
    if case.get("gap_expected") and not gap_ok:
        hard_failures.append("gap case did not contain the explicit knowledge-gap sentence")
    if case.get("safety_required") and not safety_ok:
        hard_failures.extend(safety_reasons)
    if retrieval["recall"] < 0.8:
        hard_failures.append(f"retrieval recall below 0.8: {retrieval['recall']}")
    if required and len(matched) / len(required) < 0.6:
        hard_failures.append(f"required-keyword coverage below 0.6: {len(matched)}/{len(required)}")

    auto_score = retrieval["score"] + citation_score + evidence_score + page_score + gap_score + safety_score
    if auto_score < 72:
        hard_failures.append(f"auto score below 72/90: {auto_score:.1f}")

    manual_checks = case.get("manual_checks", [])
    return {
        "id": cid,
        "type": case.get("type"),
        "title": case.get("title"),
        "question": case.get("question"),
        "expected_sources": sorted({p["source_id"] for p in case.get("expected_pages", [])}),
        "expected_points": case.get("expected_points", []),
        "retrieval": retrieval,
        "citations": {
            "validator_exit": rc,
            "validator_ok": bool(validator.get("ok")),
            "count": len(citations),
            "unique_pages": len(cited_pairs),
            "expected_cited": cited_expected,
            "expected_total": len(expected),
            "expected_pages": expected_page_status,
            "errors": errors,
            "warnings": warnings,
            "score": round(citation_score, 2),
        },
        "evidence": {
            "required": required,
            "matched": matched,
            "missing": missing,
            "coverage": round(len(matched) / len(required), 3) if required else 1.0,
            "score": round(evidence_score, 2),
        },
        "page_accuracy": {
            "pages": page_meta,
            "cited_fraction": round(cited_fraction, 3),
            "score": round(page_score, 2),
            "failures": page_failures,
        },
        "gap": {
            "expected": bool(case.get("gap_expected")),
            "ok": gap_ok,
            "score": round(gap_score, 2),
        },
        "safety": {
            "required": bool(case.get("safety_required")),
            "ok": safety_ok,
            "reasons": safety_reasons,
            "score": round(safety_score, 2),
        },
        "professional_correctness": {
            "score": None,
            "max": 10,
            "status": "manual_pending",
            "checks": manual_checks,
            "note": "自动脚本不替代专业判断；需按 checks 由人工/厨师复核。",
        },
        "auto_score": round(auto_score, 2),
        "auto_max": 90,
        "auto_passed": not hard_failures,
        "hard_failures": hard_failures,
        "answer_file": str(answer_path),
    }


def write_markdown(result: dict[str, Any], path: Path) -> None:
    s = result["summary"]
    lines = [
        "# 评测运行结果",
        "",
        f"> 生成时间：{result['generated_at']}  ",
        f"> 检索 top-k：{result['search_top']}  ",
        f"> 说明：这里验证的是**自动可核验部分**（90 分）；专业正确性 10 分是人工复核项，未用脚本冒充评分。  ",
        "> `reference_answer` 是项目内金标准答案，不是模型本次现场生成的回答。",
        "",
        "## 汇总",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| 用例数 | {s['cases']} |",
        f"| 自动通过 | {s['auto_passed']}/{s['cases']} |",
        f"| 自动通过率 | {s['auto_pass_rate']:.1%} |",
        f"| 自动得分 | {s['auto_score']:.1f}/{s['auto_max']} |",
        f"| 自动得分率 | {s['auto_score_rate']:.1%} |",
        f"| 引用/页码硬错误 | {s['citation_hard_errors']} |",
        f"| 人工待评项 | {', '.join(s['manual_review_required']) or '无'} |",
        "",
    ]
    if s["hard_failures"]:
        lines += ["### 硬失败", ""] + [f"- {x}" for x in s["hard_failures"]] + [""]
    else:
        lines += ["硬失败：无。", ""]

    lines += [
        "## 用例明细",
        "",
        "| ID | 类型 | 检索 20 | 引用 20 | 证据 15 | 页码 10 | 缺口 10 | 安全 15 | 自动分 90 | 判定 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for c in result["cases"]:
        lines.append(
            f"| {c['id']} | {c['type']} | {c['retrieval']['score']:.1f} | "
            f"{c['citations']['score']:.1f} | {c['evidence']['score']:.1f} | "
            f"{c['page_accuracy']['score']:.1f} | {c['gap']['score']:.1f} | "
            f"{c['safety']['score']:.1f} | {c['auto_score']:.1f} | "
            f"{'PASS' if c['auto_passed'] else 'FAIL'} |"
        )

    lines += ["", "## 逐例记录", ""]
    for c in result["cases"]:
        lines += [
            f"### {c['id']} · {c['title']}",
            "",
            f"- 问题：{c['question']}",
            f"- 预期来源：{', '.join(c['expected_sources']) or '无（纯缺口题）'}",
            f"- 预期要点：{'；'.join(c['expected_points'])}",
            f"- 检索：recall={c['retrieval']['recall']:.3f}；"
            + "；".join(
                f"`{q['query']}`→{q['n']} 条"
                for q in c["retrieval"]["queries"]
            ),
            f"- 引用：{c['citations']['count']} 条，唯一页 {c['citations']['unique_pages']}，"
            f"校验 {'OK' if c['citations']['validator_ok'] else 'ERROR'}；"
            f"错误 {len(c['citations']['errors'])} 条，警告 {len(c['citations']['warnings'])} 条",
            f"- 关键词：{len(c['evidence']['matched'])}/{len(c['evidence']['required'])} 命中"
            + (f"；缺：{', '.join(c['evidence']['missing'])}" if c["evidence"]["missing"] else ""),
            f"- 页码：预期页被引用 {c['citations']['expected_cited']}/{c['citations']['expected_total']}；"
            f"页码/页面失败 {len(c['page_accuracy']['failures'])} 条",
            f"- 缺口：{'已声明' if (c['gap']['expected'] and c['gap']['ok']) else ('不适用（非缺口题）' if not c['gap']['expected'] else '未声明')}；"
            f"安全：{'通过' if c['safety']['ok'] else '未通过'}",
            f"- 专业正确性：**待人工复核**（10 分，脚本不填）",
            f"- 自动分：{c['auto_score']:.1f}/90；判定：**{'PASS' if c['auto_passed'] else 'FAIL'}**",
        ]
        if c["hard_failures"]:
            lines.append("- 硬失败：" + "；".join(c["hard_failures"]))
        if c["professional_correctness"]["checks"]:
            lines.append("- 人工复核清单：" + "；".join(c["professional_correctness"]["checks"]))
        lines.append("")
    lines += [
        "## 评分口径",
        "",
        "| 维度 | 满分 | 自动/人工 | 本脚本处理 |",
        "|---|---:|---|---|",
        "| 检索命中 | 20 | 自动 | 预期页是否进入 top-k；纯缺口题要求检索为空 |",
        "| 引用真实性 | 20 | 自动 | 页码存在、书名匹配、引号内文字回查 |",
        "| 证据覆盖 | 15 | 自动 | required_keywords 覆盖率 |",
        "| 页码准确性 | 10 | 自动 | 预期页存在且被引用，印刷页/PDF 页不混用 |",
        "| 知识缺口 | 10 | 自动 | 缺口题必须出现固定表述 |",
        "| 安全边界 | 15 | 自动+人工 | 传统理论声明、禁用表述；人工复核专业边界 |",
        "| 专业正确性 | 10 | 人工 | 脚本留空，按 manual_checks 复核 |",
        "",
        "自动通过条件：无硬失败、自动分 ≥72/90、检索 recall ≥0.8、关键词覆盖 ≥0.6、"
        "引用无错误；缺口题必须有明确缺口句。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100, help="search recall depth")
    ap.add_argument("--strict", action="store_true", help="exit non-zero if any auto case fails")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    for path in sorted(CASES_DIR.glob("E*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    if not cases:
        raise SystemExit("no eval cases found")

    results = [score_case(c, args.top) for c in cases]
    total_auto = sum(c["auto_score"] for c in results)
    max_auto = sum(c["auto_max"] for c in results)
    passed = sum(1 for c in results if c["auto_passed"])
    failures = [f"{c['id']}: {x}" for c in results for x in c["hard_failures"]]
    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "knowledge_base": "four-book-v1",
        "search_top": args.top,
        "cases": results,
        "summary": {
            "cases": len(results),
            "auto_passed": passed,
            "auto_pass_rate": round(passed / len(results), 4),
            "auto_score": round(total_auto, 2),
            "auto_max": max_auto,
            "auto_score_rate": round(total_auto / max_auto, 4) if max_auto else 0.0,
            "citation_hard_errors": sum(len(c["citations"]["errors"]) for c in results),
            "manual_review_required": ["professional_correctness (10 points/case)"],
            "hard_failures": failures,
        },
    }
    (RESULTS_DIR / "latest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(result, RESULTS_DIR / "latest.md")

    print(
        json.dumps(
            {
                "cases": len(results),
                "auto_passed": passed,
                "auto_pass_rate": f"{passed / len(results):.0%}",
                "auto_score": f"{total_auto:.1f}/{max_auto}",
                "citation_errors": result["summary"]["citation_hard_errors"],
                "hard_failures": len(failures),
            },
            ensure_ascii=False,
        )
    )
    for f in failures:
        print(f"  FAIL {f}")
    return 1 if (args.strict and failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
