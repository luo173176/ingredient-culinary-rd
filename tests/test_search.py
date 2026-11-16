from __future__ import annotations

from search import expand_query, get_page, herb, search


def _pages(rows):
    return {(r["source_id"], int(r["pdf_page"])) for r in rows}


def test_huajiao_returns_both_canonical_pages() -> None:
    rows = search("花椒 温中止痛", top=20)
    pages = _pages(rows)
    assert ("MM-ZYX-2016", 396) in pages
    assert ("CN-DIDAO-2011", 234) in pages


def test_alias_xihongshi_resolves_to_tomato() -> None:
    tokens, canon = expand_query("西红柿")
    assert "番茄" in tokens
    assert "番茄" in canon
    pages = _pages(search("西红柿", top=50))
    assert ("DK-INGREDIENTS", 270) in pages


def test_alias_tudou_resolves_to_potato() -> None:
    pages = _pages(search("土豆", top=50))
    assert ("CN-DIDAO-2011", 89) in pages


def test_absorbed_compound_query_falls_back_to_substrings() -> None:
    # jieba may index "期是" where the user typed "高产期"; the fallback exists
    # so this must still find the tomato page.
    pages = _pages(search("番茄 高产期", top=20))
    assert ("DK-INGREDIENTS", 270) in pages


def test_true_gap_returns_no_results() -> None:
    assert search("奇亚籽", top=20) == []
    assert search("奇亚籽 营养", top=20) == []


def test_truffle_is_not_falsely_declared_absent() -> None:
    rows = search("松露", top=20)
    pages = _pages(rows)
    assert any(sid == "DK-INGREDIENTS" and page == 282 for sid, page in pages)


def test_page_and_herb_lookup() -> None:
    page = get_page("FS-SFAH-2023", 31)
    assert page is not None
    assert "烤制用的整鸡应该提前" in page["text"]
    assert get_page("MM-ZYX-2016", 99999) is None

    h = herb("花椒")
    assert h is not None
    assert "温中止痛" in h["efficacy"]
    assert h["is_attached"] == 0
