from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))


PAGE_FILES = {
    "MM-ZYX-2016": "MM-ZYX-2016.jsonl",
    "CN-DIDAO-2011": "CN-DIDAO-2011.ocr.jsonl",
    "FS-SFAH-2023": "FS-SFAH-2023.jsonl",
    "DK-INGREDIENTS": "DK-INGREDIENTS.ocr.jsonl",
    "MCG-V1-2013": "MCG-V1-2013.ocr.jsonl",
    "MCG-V2-2013": "MCG-V2-2013.ocr.jsonl",
    "MCG-V3-2013": "MCG-V3-2013.ocr.jsonl",
    "FC-BELITZ-2009": "FC-BELITZ-2009.jsonl",
    "FB-PAGE-2008": "FB-PAGE-2008.jsonl",
    "CR-WXY-2003": "CR-WXY-2003.ocr.jsonl",
}


def page_text(skill_root: Path, sid: str, pdf_page: int) -> str | None:
    path = skill_root / "data" / "pages" / PAGE_FILES[sid]
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        if row["pdf_page"] == pdf_page:
            return row.get("text") or ""
    return None


def card_paths(skill_root: Path) -> list[Path]:
    old = sorted((skill_root / "data" / "ingredients").glob("*.json"))
    new = sorted((skill_root / "data" / "ingredients-phase2").glob("*.json"))
    return [p for p in old + new if not p.name.startswith("_")]


def test_all_card_quotes_exist_on_their_pages(skill_root: Path) -> None:
    checked = 0
    for path in card_paths(skill_root):
        card = json.loads(path.read_text(encoding="utf-8"))
        for ev in card["sources"]:
            body = page_text(skill_root, ev["source_id"], ev["pdf_page"])
            assert body is not None, f"{path.name}: missing page {ev['source_id']} {ev['pdf_page']}"
            assert norm(ev["quote"]) in norm(body), f"{path.name}: quote not found: {ev['quote'][:40]}"
            checked += 1
    assert checked >= 100


def test_chunk_citations_match_page_fields(skill_root: Path) -> None:
    checked = 0
    for path in (skill_root / "data" / "chunks").glob("*.jsonl"):
        for line in path.open(encoding="utf-8"):
            rec = json.loads(line)
            printed = rec.get("printed_page")
            pdf = rec["pdf_page"]
            expected = (
                f"《{rec['short_title']}》p.{printed}（PDF {pdf}）"
                if printed
                else f"《{rec['short_title']}》PDF {pdf}（电子版无印刷页码）"
            )
            assert rec["citation"] == expected, rec["chunk_id"]
            assert rec["char_len"] == len(rec["content"])
            assert rec["content"].strip()
            checked += 1
    assert checked == 6656


def test_phase2_chunks_keep_source_and_series(skill_root: Path) -> None:
    phase2 = {
        "MCG-V1-2013": ("1", 396),
        "MCG-V2-2013": ("2", 408),
        "MCG-V3-2013": ("3", 415),
        "FC-BELITZ-2009": (None, 1112),
        "FB-PAGE-2008": (None, 1289),
        "CR-WXY-2003": (None, 447),
    }
    for sid, (volume, count) in phase2.items():
        rows = [
            json.loads(line)
            for line in (skill_root / "data" / "chunks" / f"{sid}.jsonl").open(encoding="utf-8")
        ]
        assert len(rows) == count
        assert all(r["source_id"] == sid for r in rows)
        assert all(r["volume"] == volume for r in rows)
        assert all(r["series"] == ("食物与厨艺" if sid.startswith("MCG-") else None) for r in rows)


def test_validator_rejects_a_fake_page(skill_root: Path, tmp_path: Path) -> None:
    answer = tmp_path / "fake.md"
    answer.write_text(
        "《中药学》PDF 99999：“这是一段不存在于书中的引文，用来验证校验器会报错。”\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "validate_output.py"), str(answer), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert not data["ok"]
    assert any("page does not exist" in e for e in data["errors"])


def test_validator_rejects_a_filtered_quote(skill_root: Path, tmp_path: Path) -> None:
    answer = tmp_path / "fake_quote.md"
    answer.write_text(
        "《中药学》PDF 396：“花椒一定是治疗所有胃病的特效药，绝无副作用。”\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "validate_output.py"), str(answer), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert any("quote not found" in e or "banned claim" in e for e in data["errors"])


def test_validator_accepts_phase2_citation(skill_root: Path, tmp_path: Path) -> None:
    answer = tmp_path / "phase2.md"
    answer.write_text(
        "《食物与厨艺：奶·蛋·肉·鱼》p.346（PDF 348）：肉类蛋白质与加热行为。\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "validate_output.py"), str(answer), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(proc.stdout)
    assert proc.returncode == 0, data
    assert data["citations"] == 1

