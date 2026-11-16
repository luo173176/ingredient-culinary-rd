"""Search the four-book knowledge base with citations.

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
) -> list[dict[str, Any]]:
    """Recover chunks when jieba emits a different token boundary than the index.

    FTS5 matches whole tokens; e.g. indexed ``期是`` does not match a query
    token ``期``.  A literal substring pass over the 2.5k chunks is cheap and
    keeps recall stable for Chinese compounds and OCR artifacts.
    """
    where = []
    params: list[Any] = []
    if source:
        where.append("source_id = ?")
        params.append(source)
    if content_type:
        where.append("content_type = ?")
        params.append(content_type)
    if page_kind:
        where.append("page_kind = ?")
        params.append(page_kind)
    sql = "SELECT * FROM chunks" + (" WHERE " + " AND ".join(where) if where else "")
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
    sql = f"""
        SELECT c.*, bm25(chunks_fts, 1.0, 0.35, 0.55) AS bm
        FROM chunks_fts f JOIN chunks c ON c.rowid = f.rowid
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
        for r in _substring_fallback(con, groups, terms, source, content_type, page_kind):
            if r.get("chunk_id") not in seen:
                rows.append(r)
                seen.add(r.get("chunk_id"))
        rows.sort(key=lambda x: x["score"], reverse=True)
    con.close()
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--source")
    ap.add_argument("--mode", choices=["keyword", "semantic"], default="keyword")
    ap.add_argument("--content-type")
    ap.add_argument("--page-kind")
    ap.add_argument("--page", help="SOURCE_ID:PDF_PAGE")
    ap.add_argument("--herb")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

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
