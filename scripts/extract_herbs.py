"""Parse the 中药学 (Materia Medica) monograph structure from the text layer.

Each monograph in the textbook follows a stable pattern:
    Herb name + pinyin + (source)
    【药性】...【功效】...【应用】...【用法用量】...【使用注意】...【现代研究】...

The table of contents gives every monograph's PDF page, which lets us slice
monographs without guessing. Output: data/herbs.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PAGES_DIR, book_path, get_book, save_json, write_jsonl  # noqa: E402

BOOK_ID = "MM-ZYX-2016"

HERB_TITLE_RE = re.compile(
    r"^([\u4e00-\u9fa5\s·]+?)\s*([A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňǹ′'’].*?)?\s*[（(]\s*《([^》]+)》\s*[）)]\s*$"
)
FIELD_RE = re.compile(r"【(药性|性味归经|功效|应用|用法用量|使用注意|现代研究|附注|配伍)】")


def parse_name(title: str) -> tuple[str | None, str | None, str | None]:
    t = title.replace("\u3000", " ").strip()
    m = HERB_TITLE_RE.match(t)
    if not m:
        return None, None, None
    name = re.sub(r"\s+", "", m.group(1))
    pinyin = re.sub(r"\s+", "", m.group(2) or "")
    source = m.group(3).strip()
    return name, pinyin, source


def toc_herbs(doc) -> list[dict[str, Any]]:
    out = []
    seen: set[str] = set()
    for level, title, page in doc.get_toc(simple=True):
        if level not in (3, 4, 5):
            continue
        if title.startswith("附药"):
            names = [n.strip() for n in re.split(r"[：:、,，]", title)[1:] if n.strip()]
            for n in names:
                n = re.sub(r"\s+", "", n)
                if n and n not in seen:
                    seen.add(n)
                    out.append(
                        {
                            "name": n,
                            "pinyin": None,
                            "classical_source": None,
                            "pdf_start": int(page),
                            "toc_title": title,
                            "is_attached": True,
                        }
                    )
            continue
        name, pinyin, src = parse_name(title)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(
            {
                "name": name,
                "pinyin": pinyin,
                "classical_source": src,
                "pdf_start": int(page),
                "toc_title": title,
                "is_attached": False,
            }
        )
    out.sort(key=lambda x: x["pdf_start"])
    return out


def field_sections(text: str) -> dict[str, str]:
    matches = list(FIELD_RE.finditer(text))
    fields: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[m.end() : end].strip()
        if key in fields:
            fields[key] += "\n" + value
        else:
            fields[key] = value
    return fields


def split_modern(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    pattern = re.compile(r"(?:^|\n)\s*(\d\.)?\s*(化学成分|药理作用|不良反应|毒性|临床研究)\s*")
    ms = list(pattern.finditer(text))
    if not ms:
        return out
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group(2)] = text[m.end() : end].strip()
    return out


def extract_monograph(
    name: str,
    pinyin: str | None,
    pages: list[dict[str, Any]],
    start_page: int,
    end_page: int,
    stop_herbs: list[dict[str, Any]] | None = None,
    is_attached: bool = False,
) -> tuple[str, int]:
    """Return (sliced text, actual start pdf page)."""
    name_pat = re.compile(r"[\s\u3000]*".join(map(re.escape, name)))
    selected = [p for p in pages if start_page <= p["pdf_page"] <= end_page]
    joined = ""
    offsets: list[tuple[int, int]] = []
    for p in selected:
        offsets.append((len(joined), p["pdf_page"]))
        joined += "\n" + p["text"]
    m = None
    if pinyin:
        py_pat = re.compile(r"[\s\u3000]*".join(map(re.escape, pinyin)))
        m = re.search(name_pat.pattern + r"[\s\u3000]*" + py_pat.pattern, joined)
    if not m:
        m = re.search(r"(?:^|\n)[\s\u3000]*" + name_pat.pattern + r"[\s\u3000]*(?:\n|$)", joined)
    if not m:
        m = name_pat.search(joined)
    if not m:
        return "", start_page
    start = m.start()
    actual_page = start_page
    for off, pg in offsets:
        if off <= start:
            actual_page = pg
        else:
            break
    body = joined[start:]
    if is_attached:
        relative = len(name)
        cut = len(body)
        for stop in stop_herbs or []:
            stop_pat = re.compile(r"[\s\u3000]*".join(map(re.escape, stop["name"])))
            sm = stop_pat.search(body, relative)
            if sm and sm.start() < cut:
                cut = sm.start()
        return body[:cut], actual_page

    # Cut at the *next herb title*, identified by name + pinyin + (《source》).
    # This is much stricter than matching a bare herb name, so cross
    # references such as "常与桂枝同用" do not truncate the current entry.
    cut = len(body)
    pinyin_chars = r"[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňǹ′'’]"
    for stop in stop_herbs or []:
        stop_name = re.compile(r"[\s\u3000]*".join(map(re.escape, stop["name"])))
        if stop.get("pinyin"):
            stop_pinyin = re.compile(r"[\s\u3000]*".join(map(re.escape, stop["pinyin"])))
            pat = re.compile(
                r"\n[\s\u3000]*" + stop_name.pattern + r"[\s\u3000]*"
                + stop_pinyin.pattern + r"[\s\u3000]*[（(]\s*《"
            )
        else:
            pat = re.compile(
                r"\n[\s\u3000]*" + stop_name.pattern + r"[\s\u3000]*"
                + pinyin_chars + r"+[\s\u3000]*[（(]\s*《"
            )
        sm = pat.search(body, len(name))
        if sm and sm.start() < cut:
            cut = sm.start()

    if cut == len(body):
        # Fallback: the second 【药性】 marker belongs to the next herb.
        marker = re.compile(r"【(药性|性味归经)】")
        ms = list(marker.finditer(body, len(name)))
        if len(ms) >= 2:
            cut = ms[1].start()
            # If the preceding line is a short title-like line, start there.
            line_start = body.rfind("\n", 0, cut) + 1
            if cut - line_start <= 30:
                cut = line_start
    body = body[:cut]
    return body, actual_page


def main() -> None:
    book = get_book(BOOK_ID)
    doc = pymupdf.open(book_path(book))
    herbs = toc_herbs(doc)
    chapter_map: list[tuple[int, str]] = []
    section_map: list[tuple[int, str]] = []
    for level, title, page in doc.get_toc(simple=True):
        if level == 2 and re.match(r"第[一二三四五六七八九十百]+章", title):
            chapter_map.append((int(page), title.replace("\u3000", " ").strip()))
        elif level == 3 and re.match(r"第[一二三四五六七八九十百]+节", title):
            section_map.append((int(page), title.replace("\u3000", " ").strip()))
    pages = sorted(
        (json.loads(line) for line in open(PAGES_DIR / f"{BOOK_ID}.jsonl", encoding="utf-8")),
        key=lambda r: r["pdf_page"],
    )
    total_pages = doc.page_count
    doc.close()

    records = []
    for i, h in enumerate(herbs):
        chapter = ""
        for p, t in chapter_map:
            if p <= h["pdf_start"]:
                chapter = t
        section = ""
        for p, t in section_map:
            if p <= h["pdf_start"] and p >= (chapter_map and next((cp for cp, ct in reversed(chapter_map) if ct == chapter), 0) or 0):
                section = t
        next_start = herbs[i + 1]["pdf_start"] if i + 1 < len(herbs) else h["pdf_start"] + 3
        # The next monograph may start on the same page; +1 keeps the full page.
        end_page = min(next_start + 1, total_pages)
        stops = herbs[i + 1 : i + 4]
        body, actual = extract_monograph(
            h["name"],
            h.get("pinyin"),
            pages,
            h["pdf_start"],
            end_page,
            stops,
            h.get("is_attached", False),
        )
        fields = field_sections(body)
        modern = split_modern(fields.get("现代研究", ""))
        efficacy = fields.get("功效", "").strip()
        nature = fields.get("药性") or fields.get("性味归经") or ""
        usage = fields.get("用法用量", "").strip()
        caution = fields.get("使用注意", "").strip()
        missing = [k for k, v in {
            "药性": nature,
            "功效": efficacy,
            "应用": fields.get("应用", ""),
            "用法用量": usage,
        }.items() if not v]
        confidence = "high" if not missing else ("medium" if efficacy else "low")
        records.append(
            {
                "source_id": BOOK_ID,
                "record_type": "attached_herb" if h.get("is_attached") else "herb_monograph",
                "name": h["name"],
                "pinyin": h["pinyin"],
                "classical_source": h["classical_source"],
                "chapter": chapter or "各论",
                "section": section or None,
                "pdf_start": actual,
                "pdf_end": end_page,
                "nature_flavor_meridians": nature.strip(),
                "efficacy": efficacy,
                "applications": fields.get("应用", "").strip(),
                "usage_dosage": usage,
                "cautions": caution,
                "modern_research": fields.get("现代研究", "").strip(),
                "chemistry": modern.get("化学成分", ""),
                "pharmacology": modern.get("药理作用", ""),
                "adverse_reactions": modern.get("不良反应", "") or modern.get("毒性", ""),
                "raw_excerpt": body[:6000],
                "missing_fields": missing,
                "confidence": confidence,
                "extraction_method": "toc_guided_regex@v1",
                "is_attached": h.get("is_attached", False),
            }
        )
        if not efficacy:
            print(f"  ! weak parse: {h['name']} p{h['pdf_start']}")

    out = DATA / "herbs.jsonl"
    write_jsonl(out, records)
    stats = {
        "book": BOOK_ID,
        "toc_monographs": len(herbs),
        "parsed": len(records),
        "with_efficacy": sum(1 for r in records if r["efficacy"]),
        "with_applications": sum(1 for r in records if r["applications"]),
        "with_usage": sum(1 for r in records if r["usage_dosage"]),
        "high_confidence": sum(1 for r in records if r["confidence"] == "high"),
        "output": str(out),
    }
    save_json(DATA / "herbs.stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
