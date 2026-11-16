"""Normalize page-level artifacts.

- Sort page records by PDF page.
- Remove clearly impossible printed page numbers (OCR misreads such as 1348
  on PDF page 353) while preserving the raw OCR string in a warning.

This script never invents a printed page number.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PAGES_DIR, write_jsonl  # noqa: E402

FILES = {
    "MM-ZYX-2016": PAGES_DIR / "MM-ZYX-2016.jsonl",
    "CN-DIDAO-2011": PAGES_DIR / "CN-DIDAO-2011.ocr.jsonl",
    "FS-SFAH-2023": PAGES_DIR / "FS-SFAH-2023.jsonl",
    "DK-INGREDIENTS": PAGES_DIR / "DK-INGREDIENTS.ocr.jsonl",
}


def main() -> None:
    report = {}
    for sid, path in FILES.items():
        rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
        removed = []
        for r in rows:
            pp = r.get("printed_page")
            if pp is not None and (not isinstance(pp, int) or pp < 1 or abs(pp - r["pdf_page"]) > 400):
                removed.append((r["pdf_page"], pp, r.get("printed_page_raw")))
                r["printed_page"] = None
                warnings = r.setdefault("warnings", [])
                if "printed_page_outlier_removed" not in warnings:
                    warnings.append("printed_page_outlier_removed")
        rows.sort(key=lambda r: r["pdf_page"])
        write_jsonl(path, rows)
        report[sid] = {"pages": len(rows), "outliers_removed": removed}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
