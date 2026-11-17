"""Extract a source-anchored pairing index from The Flavor Bible.

The scanned PDF has an OCR text layer but its page order does not follow the
book's alphabetical order.  Every record therefore carries both the PDF page
and the printed page observed in the page footer.  Parsing is deliberately
conservative:

- only bold/large all-caps lines become entry headings;
- only lines in the pairing list before ``Flavor Affinities`` become direct
  pairings;
- ``Flavor Affinities`` combinations are stored separately and pairwise
  expansion is marked as derived, never as a direct book statement;
- lines before the first heading on a page are skipped because their owner
  heading is on another scan.

Outputs:
    data/flavor_entries.jsonl
    data/flavor_pairings.jsonl
    data/flavor_affinities.jsonl
    data/flavor_pairing_stats.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PAGES_DIR, book_path, get_book, read_jsonl, save_json, write_jsonl  # noqa: E402

SOURCE_ID = "FB-PAGE-2008"

HEADING_STOP = {
    "FLAVOR AFFINITIES", "AVOID", "DISHES", "SEASON", "TASTE", "FUNCTION",
    "WEIGHT", "VOLUME", "TECHNIQUES", "TIPS", "THE FLAVOR BIBLE",
    "FLAVOR MATCHMAKING: THE CHARTS", "FLAVOR MATCHMAKING",
    "IN GENERAL", "BALANCE", "ACIDITY", "CONTRAST", "TEXTURE", "AROMA",
}
GENERIC_HEADINGS = {
    "GENERAL", "IN GENERAL", "CUISINE", "CUISINES", "OO", "FLAVOR", "FOOD",
    "COOKING", "INGREDIENTS", "THE", "AND", "OR", "A", "AN",
}
META_RE = re.compile(
    r"^(Season|Taste|Function|Weight|Volume|Techniques|Tips|Dishes|See also|"
    r"Flavor Affinities|AVOID|The Flavor Bible|Flavor Matchmaking|"
    r"Vo!uzne|VoIuzne|Tech\b|Use to add|a dish\.)\b",
    re.IGNORECASE,
)
CONTINUATION_END_RE = re.compile(r"[,:;]$")
PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
PROSE_START_RE = re.compile(
    r"^(I|we|you|it|this|that|there|the|a|an|will|would|can|could|is|are|"
    r"was|were|gives|makes|served|use|add|think|love|like|try|keep|of)\b",
    re.IGNORECASE,
)
PROSE_WORD_RE = re.compile(
    r"\b(I|we|you|it|this|that|there|is|are|was|were|has|have|will|would|"
    r"can|could|makes|gives|think|love|like|served)\b"
)
OCR_GARBAGE_RE = re.compile(
    r"(lngredi|SSlUgs|Vo!uzne|VoIuzne|Ite\b|PESTa|samon|cmnamon|onlOns|"
    r"WIt\b|d\"l|a~ halve|fnli|citntS|vemson|shriJ1lP|dre \.|"
    r"Voluzne|FlavoJ|Matohmaking|mfJoram|omlmque|请|度物|用艺|时艺|删艺|厕艺)"
)
TECHNIQUE_START_RE = re.compile(
    r"^(braise|deep-fry|grill|poach|roast|saute|steam|stir-fry|bake|broil|caramelize|"
    r"mash|puree|raw|smoke|stew|fry)\b",
    re.IGNORECASE,
)


def is_pairing_item(text: str) -> bool:
    """Conservative filter for pairing-list lines.

    The PDF text layer mixes three columns, metadata sidebars and chef quotes.
    A false positive becomes a fabricated "book pairing", so precision wins
    over recall.  Rejected lines are written to a review queue instead.
    """
    text = text.strip()
    if len(text) < 2 or len(text) > 60:
        return False
    if text[0] in "([{":
        return False
    if text.count("(") != text.count(")"):
        return False
    if text.count("*") > 2:
        return False
    if text.endswith((".", "!", "?")) and not text.endswith(("etc.)", "e.g.)")):
        return False
    if PROSE_START_RE.match(text):
        return False
    if PROSE_WORD_RE.search(text) and ":" not in text:
        return False
    if OCR_GARBAGE_RE.search(text):
        return False
    if re.search(r"\((NEW YORK|LONDON|PARIS|CHICAGO|SAN FRANCISCO)[^)]*\)", text, re.IGNORECASE):
        return False
    if re.search(r"\b(CHEF|RESTAURANT)\b", text, re.IGNORECASE):
        return False
    if re.search(r"\.\s+[a-z]", text):
        return False
    if TECHNIQUE_START_RE.match(text) and text.count(",") >= 1:
        return False
    first = text.split()[0]
    if len(first) == 1 and first.isalpha():
        return False
    if len(re.findall(r"[A-Za-z]+", text)) <= 2 and len(re.sub(r"[^A-Za-z]", "", text)) <= 4:
        # "es", "nee", "d sesame" and similar OCR debris.
        if not re.fullmatch(r"[A-Z]{2,6}", text.strip()):
            return False
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 2:
        return False
    if len(letters) / max(len(text), 1) < 0.55:
        return False
    words = text.split()
    if len(words) > 8 and not any(x in text for x in [",", ":"]):
        return False
    # Chef attributions such as "BOB IACOVONE, C UV~E (NEW ORLEANS)".
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio > 0.65 and "(" in text and "," in text:
        return False
    if text.count('"') or text.count("“") or text.count("”"):
        return False
    return True


def line_records(page) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    d = page.get_text("dict")
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if (s.get("text") or "").strip()]
            if not spans:
                continue
            parts: list[str] = []
            prev = None
            for s in spans:
                t = s.get("text", "")
                if prev is not None and t:
                    gap = s["bbox"][0] - prev["bbox"][2]
                    if gap > 0.8 and parts and not parts[-1].endswith((" ", "\n")):
                        parts.append(" ")
                parts.append(t)
                prev = s
            text = "".join(parts).strip()
            if not text:
                continue
            sizes = [s.get("size", 0) for s in spans]
            fonts = [s.get("font", "") for s in spans]
            flags = [s.get("flags", 0) for s in spans]
            out.append(
                {
                    "text": text,
                    "bbox": [round(v, 1) for v in line["bbox"]],
                    "size": round(max(sizes), 1),
                    "font": max(fonts, key=lambda f: len(f)) if fonts else "",
                    "bold": any(("bold" in f.lower()) or (fl & 16) for f, fl in zip(fonts, flags)),
                    "block_text": " ".join(
                        "".join(s.get("text", "") for s in l2.get("spans", [])).strip()
                        for l2 in block.get("lines", [])
                    ),
                }
            )
    third = float(page.rect.width) / 3.0

    def col_of(rec: dict[str, Any]) -> int:
        centre = (rec["bbox"][0] + rec["bbox"][2]) / 2
        return min(2, max(0, int(centre // third)))

    out.sort(key=lambda r: (col_of(r), r["bbox"][1], r["bbox"][0]))
    return out


def clean_heading(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.split("(")[0].strip(" :;,-")
    text = re.sub(r"^[~_'’\"“”·•\-\s]+", "", text)
    text = text.replace("’", "'")
    return text


def is_heading(rec: dict[str, Any], body_size: float) -> bool:
    text = rec["text"].strip()
    if not text or len(text) > 95:
        return False
    upper = text.upper()
    if upper in HEADING_STOP or upper in GENERIC_HEADINGS or META_RE.match(text):
        return False
    if len(re.sub(r"[^A-Za-z]", "", head_text := text.split("(")[0])) < 3:
        return False
    if PAGE_NUM_RE.match(text):
        return False
    head_text = head_text.strip()
    letters = [c for c in head_text if c.isalpha()]
    if len(letters) < 2:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.72:
        return False
    if any(x in text for x in ["+", "—", "_", "|"]):
        return False
    # Main headings are usually bold/larger, but the embedded OCR layer does
    # not carry a bold flag for every entry.  A block that also contains
    # "Season:/Taste:/..." metadata identifies its leading all-caps line as a
    # heading even when bold metadata is missing.
    meta_block = bool(
        re.search(r"\b(Season|Taste|Function|Weight|Volume|Techniques|Tips):", rec.get("block_text", ""))
    )
    if rec["bold"] and rec["size"] >= 14.5:
        return True
    return meta_block and rec["size"] >= body_size + 0.05


def is_noise(text: str) -> bool:
    if not text:
        return True
    if META_RE.match(text):
        return True
    if PAGE_NUM_RE.match(text):
        return True
    if re.match(r"^[_\-\u2014•·]+$", text):
        return True
    if text.startswith("_ ") or text.startswith("— "):
        return True
    return False


def parse_page(
    page, page_rec: dict[str, Any], carry_entry: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int]:
    lines = line_records(page)
    if not lines:
        return [], [], [], [], 0
    body_size = statistics.median([r["size"] for r in lines]) if lines else 10.0
    entries: list[dict[str, Any]] = []
    pairings: list[dict[str, Any]] = []
    affinities: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    heading_count = 0

    # A spread often continues an entry from the previous scan without
    # repeating the heading.  Carrying the last entry keeps those pages
    # searchable while still recording the page where the item actually
    # appears.
    current: str | None = carry_entry
    in_affinities = False
    in_dishes = False
    current_items: list[dict[str, Any]] = []
    affinity_lines: list[str] = []

    def flush_entry() -> None:
        nonlocal current_items
        kept = []
        for item in current_items:
            normalized = re.sub(r"^[~'’\"“”*·•\-\s]+", "", item["text"]).strip()
            if not normalized or not is_pairing_item(normalized):
                rejected.append(
                    {
                        "entry": current,
                        "text": item["text"],
                        "source_id": SOURCE_ID,
                        "pdf_page": page_rec["pdf_page"],
                        "printed_page": page_rec.get("printed_page"),
                        "reason": "failed_post_merge_filter",
                    }
                )
                continue
            item = dict(item)
            item["text"] = normalized
            kept.append(item)
        current_items = kept
        if current and current_items:
            entries.append(
                {
                    "entry_id": f"{SOURCE_ID}:p{page_rec['pdf_page']}:{re.sub(r'[^a-z0-9]+', '-', current.lower()).strip('-')}",
                    "entry": current,
                    "source_id": SOURCE_ID,
                    "pdf_page": page_rec["pdf_page"],
                    "printed_page": page_rec.get("printed_page"),
                    "pairing_items": [x["text"] for x in current_items],
                    "n_pairing_items": len(current_items),
                }
            )
        current_items = []

    for rec in lines:
        text = rec["text"].strip()
        if PAGE_NUM_RE.match(text):
            continue
        if "Flavor Matchmaking" in text or text == "The Flavor Bible":
            continue
        if text.upper() == "FLAVOR AFFINITIES":
            in_affinities = True
            in_dishes = False
            affinity_lines = []
            continue
        if re.match(r"^Dishes\b", text):
            in_dishes = True
            continue
        if is_heading(rec, body_size):
            flush_entry()
            current = clean_heading(text)
            heading_count += 1
            in_affinities = False
            in_dishes = False
            affinity_lines = []
            continue
        if current is None or is_noise(text) or in_dishes:
            continue
        if in_affinities:
            if "+" in text:
                affinity_lines.append(text)
            continue
        # Merge wrapped continuation lines such as "cheese: goat, Gruyère,"
        # followed by "mozzarella, Parmesan".
        if current_items and (
            current_items[-1]["text"].endswith((",", ":", ";"))
            or re.match(r"^(and|or)\b", text, re.IGNORECASE)
        ):
            current_items[-1]["text"] = (current_items[-1]["text"] + " " + text).strip()
            continue
        if len(text) <= 1:
            continue
        if not is_pairing_item(text):
            rejected.append(
                {
                    "entry": current,
                    "text": text,
                    "source_id": SOURCE_ID,
                    "pdf_page": page_rec["pdf_page"],
                    "printed_page": page_rec.get("printed_page"),
                    "reason": "failed_pairing_item_filter",
                }
            )
            continue
        current_items.append(rec)

    flush_entry()

    # Parse affinity combinations after the page's final heading.  Some pages
    # have multiple headings, so this pass re-walks by heading blocks.
    current = None
    in_aff = False
    lines_for_aff: list[str] = []

    def flush_aff() -> None:
        nonlocal lines_for_aff
        if current and lines_for_aff:
            for raw in lines_for_aff:
                parts = [p.strip(" .;") for p in re.split(r"\+", raw) if p.strip(" .;")]
                if len(parts) < 2:
                    continue
                affinity = {
                    "affinity_id": f"{SOURCE_ID}:p{page_rec['pdf_page']}:a{len(affinities)+1}",
                    "entry": current,
                    "ingredients": parts,
                    "source_id": SOURCE_ID,
                    "pdf_page": page_rec["pdf_page"],
                    "printed_page": page_rec.get("printed_page"),
                    "original_context": raw,
                    "confidence": "high" if page_rec.get("printed_page") else "medium",
                }
                affinities.append(affinity)
        lines_for_aff = []

    for rec in lines:
        text = rec["text"].strip()
        if "Flavor Matchmaking" in text or text == "The Flavor Bible" or PAGE_NUM_RE.match(text):
            continue
        if text.upper() == "FLAVOR AFFINITIES":
            in_aff = True
            lines_for_aff = []
            continue
        if is_heading(rec, body_size):
            flush_aff()
            current = clean_heading(text)
            in_aff = False
            continue
        if current and in_aff and "+" in text and not is_noise(text):
            lines_for_aff.append(text)
    flush_aff()

    # Direct pairings: one record per cited item.
    for entry in entries:
        for i, item in enumerate(entry["pairing_items"], 1):
            strong = "none"
            if item.startswith("*"):
                strong = "asterisk_classic_candidate"
                item = item.lstrip("* ").strip()
            if item.isupper() and len(item) > 2:
                strong = "capitalized_or_bold_candidate"
            pairings.append(
                {
                    "pairing_id": f"{SOURCE_ID}:p{page_rec['pdf_page']}:{re.sub(r'[^a-z0-9]+', '-', entry['entry'].lower()).strip('-')}:{i}",
                    "ingredient_a": entry["entry"],
                    "ingredient_b": item,
                    "relationship": "flavor_pairing",
                    "evidence_level": "explicit_pairing_listing",
                    "source_id": SOURCE_ID,
                    "pdf_page": page_rec["pdf_page"],
                    "printed_page": page_rec.get("printed_page"),
                    "original_context": f"{entry['entry']}: {item}",
                    "book_evidence": item,
                    "strong_marker": strong,
                    "confidence": "high" if page_rec.get("printed_page") else "medium",
                    "ocr_notes": "OCR text layer; heading/list boundary heuristics" if not page_rec.get("printed_page") else None,
                    "keywords": sorted(set(entry["entry"].lower().split() + item.lower().split()))[:12],
                }
            )
        for aff in [a for a in affinities if a["entry"] == entry["entry"] and a["pdf_page"] == page_rec["pdf_page"]]:
            for j, other in enumerate(aff["ingredients"]):
                if other.lower() == entry["entry"].lower():
                    continue
                pairings.append(
                    {
                        "pairing_id": f"{SOURCE_ID}:p{page_rec['pdf_page']}:{re.sub(r'[^a-z0-9]+', '-', entry['entry'].lower()).strip('-')}:aff:{j}",
                        "ingredient_a": entry["entry"],
                        "ingredient_b": other,
                        "relationship": "flavor_affinity_member",
                        "evidence_level": "derived_from_affinity_combination",
                        "source_id": SOURCE_ID,
                        "pdf_page": page_rec["pdf_page"],
                        "printed_page": page_rec.get("printed_page"),
                        "original_context": aff["original_context"],
                        "book_evidence": aff["original_context"],
                        "strong_marker": "none",
                        "confidence": aff["confidence"],
                        "ocr_notes": "Pairwise link derived from a plus-separated affinity line",
                        "keywords": sorted(set(entry["entry"].lower().split() + other.lower().split()))[:12],
                    }
                )

    return entries, pairings, affinities, rejected, heading_count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=SOURCE_ID)
    args = ap.parse_args()
    book = get_book(args.book)
    pdf = book_path(book)
    pages = {r["pdf_page"]: r for r in read_jsonl(PAGES_DIR / f"{args.book}.jsonl")}
    if not pages:
        raise SystemExit("run ingest_digital.py first")
    doc = pymupdf.open(pdf)
    all_entries: list[dict[str, Any]] = []
    all_pairings: list[dict[str, Any]] = []
    all_affinities: list[dict[str, Any]] = []
    all_rejected: list[dict[str, Any]] = []
    carry_entry: str | None = None
    carry_allowed = True
    for i in range(doc.page_count):
        rec = pages.get(i + 1)
        if not rec:
            continue
        if i + 1 < 40:
            continue
        e, p, a, rej, heading_count = parse_page(
            doc[i], rec, carry_entry=carry_entry if carry_allowed else None
        )
        if not rec.get("printed_page"):
            # Keep such pages in the general chunk index, but do not promote
            # uncertain headings to pairing entries.
            e, p, a = [], [], []
            rej = []
        all_entries.extend(e)
        all_pairings.extend(p)
        all_affinities.extend(a)
        all_rejected.extend(rej)
        # Allow a single page of continuation.  If the page produced no new
        # heading at all, stop carrying so one bad heading cannot absorb the
        # rest of the book.
        if heading_count > 0 and e and e[-1]["entry"].upper() not in GENERIC_HEADINGS:
            carry_entry = e[-1]["entry"]
            carry_allowed = True
        else:
            carry_allowed = False
    doc.close()

    # Deduplicate while preserving evidence rows.
    def dedup(rows: list[dict[str, Any]], key: tuple[str, ...]) -> list[dict[str, Any]]:
        seen = set()
        out = []
        for r in rows:
            k = tuple(str(r.get(x, "")) for x in key)
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return out

    all_entries = dedup(all_entries, ("entry", "pdf_page"))
    all_pairings = dedup(all_pairings, ("ingredient_a", "ingredient_b", "pdf_page", "evidence_level"))
    all_affinities = dedup(all_affinities, ("entry", "original_context", "pdf_page"))

    write_jsonl(DATA / "flavor_entries.jsonl", all_entries)
    write_jsonl(DATA / "flavor_pairings.jsonl", all_pairings)
    write_jsonl(DATA / "flavor_affinities.jsonl", all_affinities)
    write_jsonl(DATA / "flavor_review_queue.jsonl", all_rejected)
    stats = {
        "source_id": SOURCE_ID,
        "pages_processed": doc_page_count(pdf),
        "entries": len(all_entries),
        "pairings": len(all_pairings),
        "direct_pairings": sum(1 for r in all_pairings if r["evidence_level"] == "explicit_pairing_listing"),
        "derived_pairings": sum(1 for r in all_pairings if r["evidence_level"].startswith("derived")),
        "affinities": len(all_affinities),
        "review_queue": len(all_rejected),
        "entries_with_printed_page": sum(1 for r in all_entries if r.get("printed_page")),
        "strong_marker_candidates": sum(1 for r in all_pairings if r["strong_marker"] != "none"),
        "pages_with_entries": len({r["pdf_page"] for r in all_entries}),
        "note": "Direct listings are explicit book evidence; affinity members are derived from plus-separated combination lines.",
    }
    save_json(DATA / "flavor_pairing_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def doc_page_count(pdf: Path) -> int:
    d = pymupdf.open(pdf)
    n = d.page_count
    d.close()
    return n


if __name__ == "__main__":
    main()
