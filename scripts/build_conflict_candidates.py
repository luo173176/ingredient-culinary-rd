"""Build a conservative cross-source conflict review queue.

This script does not decide which source is right.  It only finds claim-bearing
fields where two different source pages contribute different statements for the
same ingredient and topic.  Humans must read both pages and classify the pair as
complementary, context-dependent, different-variety, version-related or a real
contradiction.

Usage:
    python scripts/build_conflict_candidates.py
"""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

from common import DATA

CARD_DIRS = (DATA / "ingredients", DATA / "ingredients-phase2")
OUTPUT = DATA / "conflict_candidates.jsonl"

CLAIM_FIELDS = (
    ("origin_variety", "origins"),
    ("origin_variety", "varieties"),
    ("appearance_quality", "traits"),
    ("appearance_quality", "grading"),
    ("processing_storage", "processing"),
    ("processing_storage", "storage"),
)


def normalise(value: str | None) -> str:
    return "".join((value or "").split()).lower()


def claim_rows(card: dict, domain: str, field: str) -> list[dict]:
    rows: list[dict] = []
    block = card.get(domain) or {}
    for claim in block.get(field) or []:
        statement = str(claim.get("statement") or "").strip()
        if not statement:
            continue
        for evidence in claim.get("evidence") or []:
            source_id = evidence.get("source_id")
            pdf_page = evidence.get("pdf_page")
            if not source_id or not pdf_page:
                continue
            rows.append(
                {
                    "value": statement,
                    "source_id": source_id,
                    "pdf_page": int(pdf_page),
                    "quote": evidence.get("quote"),
                    "confidence": evidence.get("confidence"),
                }
            )
    return rows


def main() -> None:
    candidates: dict[str, dict] = {}
    for folder in CARD_DIRS:
        for path in sorted(folder.glob("*.json")):
            if path.name.startswith("_"):
                continue
            card = json.loads(path.read_text(encoding="utf-8"))
            ingredient = card.get("basic", {}).get("canonical_name_zh") or card.get("id")
            for domain, field in CLAIM_FIELDS:
                rows = claim_rows(card, domain, field)
                for a, b in combinations(rows, 2):
                    if a["source_id"] == b["source_id"]:
                        continue
                    if normalise(a["value"]) == normalise(b["value"]):
                        continue
                    key = "|".join(
                        [
                            str(card.get("id")),
                            domain,
                            field,
                            a["source_id"],
                            str(a["pdf_page"]),
                            b["source_id"],
                            str(b["pdf_page"]),
                        ]
                    )
                    cid = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
                    candidates[cid] = {
                        "id": f"conflict-{cid}",
                        "ingredient": ingredient,
                        "topic": f"{domain}.{field}",
                        "source_a": a["source_id"],
                        "page_a": a["pdf_page"],
                        "value_a": a["value"][:600],
                        "source_b": b["source_id"],
                        "page_b": b["pdf_page"],
                        "value_b": b["value"][:600],
                        "status": "review",
                        "note": (
                            "自动候选，不是冲突结论：同一知识域存在来自不同来源的并列表述；"
                            "请回页判断是互补、不同品种/条件、版本差异还是真矛盾。"
                        ),
                    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as fh:
        for record in sorted(candidates.values(), key=lambda x: x["id"]):
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"conflict_candidates: {len(candidates)} -> {OUTPUT}")


if __name__ == "__main__":
    main()
