"""Search the ten-book knowledge base with citations.

Examples:
    python scripts/search.py "花椒 温中止痛" --top 5
    python scripts/search.py "西红柿" --source DK-INGREDIENTS
    python scripts/search.py "盐 渗透" --mode semantic --json
    python scripts/search.py --page FS-SFAH-2023:31
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jieba

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, INDEX_DIR, load_json, snippet  # noqa: E402

jieba.setLogLevel(20)
DB = INDEX_DIR / "knowledge.sqlite"


def load_alias_data() -> tuple[dict[str, str], dict[str, list[str]]]:
    lex = load_json(CONFIG / "ingredient_lexicon.json", {"entries": []})
    out = {}
    groups = {}
    for e in lex.get("entries", []):
        canonical = e["canonical"]
        out[canonical] = canonical
        groups[canonical] = list(dict.fromkeys([canonical] + list(e.get("aliases", []))))
        for a in e.get("aliases", []):
            out[a] = canonical
    return out, groups


ALIASES, ALIAS_GROUPS = load_alias_data()
TERM_CONFIG = load_json(CONFIG / "professional_terms.json", {"terms": []})
PRO_TERM_REWRITES = [
    (str(item.get("zh", "")).strip(), str(en).strip())
    for item in TERM_CONFIG.get("terms", [])
    for en in item.get("en", [])
    if str(item.get("zh", "")).strip() and str(en).strip()
]


def tokenize(q: str) -> list[str]:
    toks = [t.strip() for t in jieba.cut_for_search(q) if t.strip()]
    toks = [t for t in toks if not re.fullmatch(r"[\W_]+", t)]
    return list(dict.fromkeys(toks))


def query_groups(q: str) -> list[list[str]]:
    """Return AND-groups; alternatives inside a group are OR-ed.

    ``西红柿`` expands to ``(西红柿 OR 番茄 …)`` so an alias query does not
    require both spellings to occur in the same chunk.
    """
    groups: list[list[str]] = []
    for tok in tokenize(q):
        canonical = ALIASES.get(tok)
        group = ALIAS_GROUPS.get(canonical, [tok]) if canonical else [tok]
        group = [x for x in dict.fromkeys(group) if x]
        if group and group not in groups:
            groups.append(group)
    return groups


def expand_query(q: str) -> tuple[list[str], list[str]]:
    groups = query_groups(q)
    toks = [t for group in groups for t in group]
    canon = []
    for t in toks:
        c = ALIASES.get(t)
        if c and c not in canon:
            canon.append(c)
    return list(dict.fromkeys(toks)), canon


def professional_query_rewrites(q: str) -> list[str]:
    """Translate selected Chinese professional terms into English search hints.

    The glossary is a retrieval aid only.  It does not add facts to an answer;
    every retrieved passage still has to be checked against its source page.
    """
    hits: list[str] = []
    for zh, en in PRO_TERM_REWRITES:
        if zh in q and en not in hits:
            hits.append(en)
    return hits


def fts_query(groups: list[str] | list[list[str]], mode: str) -> str:
    if not groups:
        return ""
    normalized = [[g] if isinstance(g, str) else g for g in groups]
    clauses = []
    for group in normalized:
        quoted = [f'"{t}"' for t in group if t]
        if quoted:
            clauses.append("(" + " OR ".join(quoted) + ")" if len(quoted) > 1 else quoted[0])
    if not clauses:
        return ""
    joiner = " AND " if mode == "keyword" else " OR "
    return joiner.join(clauses)


def bigrams(text: str) -> Counter:
    flat = re.sub(r"\s+", "", text)
    return Counter(flat[i : i + 2] for i in range(max(0, len(flat) - 1)))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _prepare_row(row: dict[str, Any], terms: list[str], score: float) -> dict[str, Any]:
    row = dict(row)
    content = row.pop("content", "") or ""
    row["score"] = round(score, 4)
    row["exact_hits"] = sum(1 for t in terms if t and t in content)
    row["semantic"] = 0.0
    row["quote"] = snippet(content, terms, width=260)
    row["keywords"] = json.loads(row.get("keywords") or "[]")
    row["related_ingredients"] = json.loads(row.get("related_ingredients") or "[]")
    row["warnings"] = json.loads(row.get("warnings") or "[]")
    row.pop("bm", None)
    return row


def _substring_fallback(
    con: sqlite3.Connection,
    groups: list[list[str]],
    terms: list[str],
    source: str | None,
    content_type: str | None,
    page_kind: str | None,
    series: str | None = None,
    volume: str | None = None,
    domain: str | None = None,
    chapter: str | None = None,
    phase: int | None = None,
) -> list[dict[str, Any]]:
    """Recover chunks when jieba emits a different token boundary than the index.

    FTS5 matches whole tokens; e.g. indexed ``期是`` does not match a query
    token ``期``.  A literal substring pass over the 2.5k chunks is cheap and
    keeps recall stable for Chinese compounds and OCR artifacts.
    """
    where = []
    params: list[Any] = []
    if source:
        where.append("c.source_id = ?")
        params.append(source)
    if content_type:
        where.append("c.content_type = ?")
        params.append(content_type)
    if page_kind:
        where.append("c.page_kind = ?")
        params.append(page_kind)
    if series:
        where.append("c.series = ?")
        params.append(series)
    if volume:
        where.append("c.volume = ?")
        params.append(volume)
    if domain:
        where.append("c.domain = ?")
        params.append(domain)
    if chapter:
        where.append("c.chapter LIKE ?")
        params.append(f"%{chapter}%")
    if phase is not None:
        where.append("s.phase = ?")
        params.append(phase)
    sql = "SELECT c.* FROM chunks c LEFT JOIN sources s ON s.source_id=c.source_id" + (
        " WHERE " + " AND ".join(where) if where else ""
    )
    out: list[dict[str, Any]] = []
    for raw in con.execute(sql, params):
        row = dict(raw)
        content = row.get("content") or ""
        if not all(any(alt in content for alt in group) for group in groups):
            continue
        hits = sum(content.count(alt) for group in groups for alt in group)
        score = len(groups) * 2.0 + min(hits, 30) * 0.08
        if row.get("page_kind") != "content":
            score -= 4.0
        out.append(_prepare_row(row, terms, score))
    return out


def search(
    query: str,
    top: int = 8,
    source: str | None = None,
    mode: str = "keyword",
    content_type: str | None = None,
    page_kind: str | None = None,
    series: str | None = None,
    volume: str | None = None,
    domain: str | None = None,
    chapter: str | None = None,
    phase: int | None = None,
    _expand_terms: bool = True,
) -> list[dict[str, Any]]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    groups = query_groups(query)
    tokens, canon = expand_query(query)
    fq = fts_query(groups, mode)
    if not fq:
        return []
    where = ["chunks_fts MATCH ?"]
    params: list[Any] = [fq]
    if source:
        where.append("c.source_id = ?")
        params.append(source)
    if content_type:
        where.append("c.content_type = ?")
        params.append(content_type)
    if page_kind:
        where.append("c.page_kind = ?")
        params.append(page_kind)
    if series:
        where.append("c.series = ?")
        params.append(series)
    if volume:
        where.append("c.volume = ?")
        params.append(volume)
    if domain:
        where.append("c.domain = ?")
        params.append(domain)
    if chapter:
        where.append("c.chapter LIKE ?")
        params.append(f"%{chapter}%")
    if phase is not None:
        where.append("s.phase = ?")
        params.append(phase)
    sql = f"""
        SELECT c.*, bm25(chunks_fts, 1.0, 0.35, 0.55) AS bm
        FROM chunks_fts f JOIN chunks c ON c.rowid = f.rowid
        LEFT JOIN sources s ON s.source_id = c.source_id
        WHERE {' AND '.join(where)}
        ORDER BY bm
        LIMIT 1000
    """
    rows = [dict(r) for r in con.execute(sql, params)]

    q_bi = bigrams(query)
    terms = tokens + canon + [query]
    for r in rows:
        content = r["content"]
        exact = sum(1 for t in terms if t and t in content)
        coverage = exact / max(1, len(terms))
        sem = cosine(q_bi, bigrams(content)) if mode == "semantic" else 0.0
        # BM25 is negative (lower is better); convert to a positive score.
        r["score"] = round(-float(r["bm"]) + coverage * 2.0 + sem * 2.0, 4)
        if r.get("page_kind") != "content":
            r["score"] = round(r["score"] - 4.0, 4)
        r["exact_hits"] = exact
        r["semantic"] = round(sem, 4)
        r["quote"] = snippet(content, list(dict.fromkeys(terms)), width=260)
        r["keywords"] = json.loads(r["keywords"] or "[]")
        r["related_ingredients"] = json.loads(r["related_ingredients"] or "[]")
        r["warnings"] = json.loads(r["warnings"] or "[]")
        r.pop("bm", None)
        r.pop("content", None)
    rows.sort(key=lambda x: x["score"], reverse=True)

    # Token-boundary fallback.  Keep the FTS results and add literal matches.
    if len(rows) < 20 and groups:
        seen = {r.get("chunk_id") for r in rows}
        for r in _substring_fallback(
            con, groups, terms, source, content_type, page_kind,
            series, volume, domain, chapter, phase,
        ):
            if r.get("chunk_id") not in seen:
                rows.append(r)
                seen.add(r.get("chunk_id"))
        rows.sort(key=lambda x: x["score"], reverse=True)
    con.close()

    # English-language sources such as Food Chemistry need a small, explicit
    # Chinese-to-English retrieval bridge.  Run those rewrites as additional
    # queries and merge them instead of weakening the original Chinese query.
    if _expand_terms:
        rewrites = professional_query_rewrites(query)
        if rewrites:
            merged = {
                (r.get("source_id"), int(r.get("pdf_page") or 0), r.get("chunk_id")): r
                for r in rows
            }
            for rewrite in rewrites:
                for extra in search(
                    rewrite,
                    top=max(top, 12),
                    source=source,
                    mode="keyword",
                    content_type=content_type,
                    page_kind=page_kind,
                    series=series,
                    volume=volume,
                    domain=domain,
                    chapter=chapter,
                    phase=phase,
                    _expand_terms=False,
                ):
                    extra = dict(extra)
                    extra["score"] = round(float(extra.get("score", 0.0)) * 0.9, 4)
                    key = (extra.get("source_id"), int(extra.get("pdf_page") or 0), extra.get("chunk_id"))
                    if key not in merged or extra["score"] > merged[key]["score"]:
                        merged[key] = extra
            rows = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
    return rows[:top]


def get_page(source_id: str, pdf_page: int) -> dict[str, Any] | None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    r = con.execute(
        "SELECT p.*, s.short_title FROM pages p JOIN sources s USING(source_id) WHERE source_id=? AND pdf_page=?",
        (source_id, pdf_page),
    ).fetchone()
    con.close()
    return dict(r) if r else None


def herb(name: str) -> dict[str, Any] | None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM herbs WHERE name=?", (name,)).fetchone()
    con.close()
    return dict(r) if r else None


def pairings_for(name: str, top: int = 50) -> list[dict[str, Any]]:
    """Return Flavor Bible evidence rows that mention an ingredient."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = f"%{name.strip()}%"
    rows = con.execute(
        "SELECT * FROM flavor_pairings "
        "WHERE ingredient_a LIKE ? OR ingredient_b LIKE ? "
        "ORDER BY (ingredient_a LIKE ?) DESC, confidence DESC, pdf_page LIMIT ?",
        (q, q, q, top),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def pairing_between(a: str, b: str) -> list[dict[str, Any]]:
    """Return direct or affinity evidence for a pair, in either order."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    qa, qb = f"%{a.strip()}%", f"%{b.strip()}%"
    rows = con.execute(
        "SELECT * FROM flavor_pairings WHERE "
        "(ingredient_a LIKE ? AND ingredient_b LIKE ?) OR "
        "(ingredient_a LIKE ? AND ingredient_b LIKE ?) "
        "ORDER BY confidence DESC, pdf_page",
        (qa, qb, qb, qa),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def chemistry_topics(query: str, top: int = 20) -> list[dict[str, Any]]:
    """Search the Food Chemistry topic index by topic/chapter/section text."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = f"%{query.strip()}%"
    rows = con.execute(
        "SELECT * FROM chemistry_topics WHERE topic LIKE ? OR chapter LIKE ? OR section LIKE ? "
        "OR evidence_quote LIKE ? ORDER BY pdf_page LIMIT ?",
        (q, q, q, q, top),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def list_sources() -> list[dict[str, Any]]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT source_id,short_title,title,domain,series,volume,phase,page_count,pages_extracted,chunks "
        "FROM sources ORDER BY phase, source_id"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--source")
    ap.add_argument("--mode", choices=["keyword", "semantic"], default="keyword")
    ap.add_argument("--content-type")
    ap.add_argument("--page-kind")
    ap.add_argument("--series")
    ap.add_argument("--volume")
    ap.add_argument("--domain")
    ap.add_argument("--chapter")
    ap.add_argument("--phase", type=int)
    ap.add_argument("--page", help="SOURCE_ID:PDF_PAGE")
    ap.add_argument("--herb")
    ap.add_argument("--pairing", help="list Flavor Bible evidence for one ingredient")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"), help="look up a specific pair")
    ap.add_argument("--chemistry", help="search Food Chemistry topic index")
    ap.add_argument("--sources", action="store_true", help="list all sources")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.sources:
        rows = list_sources()
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else "\n".join(
            f"{r['source_id']:16} p{r['phase']} {r['short_title']} [{r['domain']}] "
            f"pages={r['pages_extracted']} chunks={r['chunks']}" for r in rows
        ))
        return
    if args.pairing:
        rows = pairings_for(args.pairing, top=args.top)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                print(f"{r['ingredient_a']} + {r['ingredient_b']} · {r['evidence_level']} · "
                      f"《The Flavor Bible》PDF {r['pdf_page']} · {r['confidence']}")
                print("    " + (r.get("original_context") or "")[:220])
        return
    if args.pair:
        rows = pairing_between(args.pair[0], args.pair[1])
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                print(f"{r['ingredient_a']} + {r['ingredient_b']} · {r['evidence_level']} · "
                      f"PDF {r['pdf_page']}")
                print("    " + (r.get("original_context") or "")[:260])
            if not rows:
                print("NO_DIRECT_PAIRING_EVIDENCE")
        return
    if args.chemistry:
        rows = chemistry_topics(args.chemistry, top=args.top)
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else "\n".join(
            f"[{r['topic_id']}] {r['chapter']} / {r['section']} · PDF {r['pdf_page']}" for r in rows
        ))
        return
    if args.page:
        sid, page = args.page.split(":")
        rec = get_page(sid, int(page))
        if not rec:
            raise SystemExit("page not found")
        print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else rec["text"])
        return
    if args.herb:
        rec = herb(args.herb)
        if not rec:
            raise SystemExit("herb not found")
        print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in rec.items()))
        return
    if not args.query:
        raise SystemExit("query required")

    rows = search(
        args.query,
        top=args.top,
        source=args.source,
        mode=args.mode,
        content_type=args.content_type,
        page_kind=args.page_kind,
        series=args.series,
        volume=args.volume,
        domain=args.domain,
        chapter=args.chapter,
        phase=args.phase,
    )
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for i, r in enumerate(rows, 1):
        print(f"[{i}] {r['citation']} · {r['chapter'] or ''} {r['section'] or ''} · {r['content_type']} · conf={r['confidence']}")
        print("    " + r["quote"])
        print(f"    score={r['score']} exact={r['exact_hits']} sem={r['semantic']}")
    if not rows:
        print("NO_RESULTS")


if __name__ == "__main__":
    main()
