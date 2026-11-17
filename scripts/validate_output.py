"""Validate citations, quotes, gaps and safety language in an answer.

Usage:
    python scripts/validate_output.py answer.md
    python scripts/validate_output.py answer.md --json

This is a guardrail, not a substitute for reading the cited page.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INDEX_DIR, load_books  # noqa: E402

DB = INDEX_DIR / "knowledge.sqlite"

BANNED = [
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
]

SAFETY_HINTS = [
    "传统", "不是现代医学", "非现代医学", "传统理论",
    "食品安全", "不是医疗建议", "高风险人群", "致病菌", "彻底加热",
]
GAP_HINT = "暂无充分依据"


def normalize(s: str) -> str:
    return re.sub(r"[\s\u3000，。；：、！？“”‘’\"'（）()《》·,.;:!?\-—]", "", s)


def title_map() -> dict[str, str]:
    out = {}
    for b in load_books():
        out[b["short_title"]] = b["source_id"]
        out[b["title"]] = b["source_id"]
        out[b.get("citation_label", "")] = b["source_id"]
    return out


def page_text(con, source_id: str, pdf_page: int) -> str | None:
    r = con.execute(
        "SELECT text FROM pages WHERE source_id=? AND pdf_page=?", (source_id, pdf_page)
    ).fetchone()
    return r[0] if r else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-gap", action="store_true")
    ap.add_argument("--require-safety", action="store_true")
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")
    titles = title_map()
    con = sqlite3.connect(DB)
    errors: list[str] = []
    warnings: list[str] = []
    citations: list[dict[str, Any]] = []

    # 《书名》 PDF 396 / 《书名》p.37（PDF 40）
    pat = re.compile(
        r"《([^》]{2,40})》\s*(?:p\.\s*(\d+)\s*[（(]\s*PDF\s*(\d+)\s*[）)])|《([^》]{2,40})》\s*PDF\s*(\d+)"
    )
    for m in pat.finditer(text):
        if m.group(1):
            title, printed, pdf = m.group(1), int(m.group(2)), int(m.group(3))
        else:
            title, printed, pdf = m.group(4), None, int(m.group(5))
        sid = titles.get(title)
        if not sid:
            # Try contains matching
            for t, s in titles.items():
                if t and (t in title or title in t):
                    sid = s
                    break
        if not sid:
            errors.append(f"unknown book title: {title}")
            continue
        body = page_text(con, sid, pdf)
        rec = {"title": title, "source_id": sid, "pdf_page": pdf, "printed_page": printed, "exists": body is not None}
        citations.append(rec)
        if body is None:
            errors.append(f"page does not exist: {title} PDF {pdf}")
            continue
        if printed is not None:
            row = con.execute(
                "SELECT printed_page FROM pages WHERE source_id=? AND pdf_page=?", (sid, pdf)
            ).fetchone()
            actual = row[0] if row else None
            if actual is None:
                warnings.append(f"{title} PDF {pdf}: printed page cited but no printed page detected")
            elif actual != printed:
                errors.append(f"printed page mismatch: {title} p.{printed} (PDF {pdf}), DB p.{actual}")

    # Quoted text verification (only quotes >= 6 chars)
    for q in re.findall(r"[“「]([^”」]{6,120})[”」]", text):
        nq = normalize(q)
        if len(nq) < 6:
            continue
        found = False
        for c in citations:
            body = page_text(con, c["source_id"], c["pdf_page"])
            if body and nq in normalize(body):
                found = True
                break
        if not found:
            errors.append(f"quote not found on cited pages: {q[:40]}…")

    lower = text
    for bad in BANNED:
        if bad in lower:
            errors.append(f"banned claim: {bad}")
    if args.require_safety or "中药" in text or "本草" in text:
        if not any(h in text for h in SAFETY_HINTS):
            errors.append("missing traditional-theory / non-modern-medicine disclaimer")
    if args.require_gap and GAP_HINT not in text:
        errors.append("missing explicit knowledge-gap statement")
    if not citations:
        warnings.append("no citations found")

    con.close()
    result = {
        "file": args.file,
        "citations": len(citations),
        "unique_pages": len({(c["source_id"], c["pdf_page"]) for c in citations}),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"citations={result['citations']} unique_pages={result['unique_pages']} ok={result['ok']}")
        for e in errors:
            print(f"  ERROR: {e}")
        for w in warnings:
            print(f"  WARN:  {w}")
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
