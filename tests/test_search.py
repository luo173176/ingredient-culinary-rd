from __future__ import annotations

from search import (
    chemistry_topics,
    expand_query,
    get_page,
    herb,
    list_sources,
    pairings_for,
    professional_query_rewrites,
    search,
)


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


def test_phase2_sources_are_searchable_and_filterable() -> None:
    assert len(list_sources()) == 10

    water = _pages(search("water activity", top=50, source="FC-BELITZ-2009"))
    assert ("FC-BELITZ-2009", 48) in water

    starch = _pages(search("starch gelatinization", top=50, source="FC-BELITZ-2009"))
    assert ("FC-BELITZ-2009", 363) in starch

    sauce = _pages(search("淀粉 糊化 酱汁", top=50, source="MCG-V1-2013"))
    assert ("MCG-V1-2013", 129) in sauce

    by_series = _pages(
        search("肌肉 蛋白质 加热", top=50, series="食物与厨艺", volume="3")
    )
    assert by_series
    assert all(sid == "MCG-V3-2013" for sid, _ in by_series)

    chemistry = _pages(search("maillard", top=50, domain="food-chemistry"))
    assert any(sid == "FC-BELITZ-2009" for sid, _ in chemistry)


def test_flavor_pairing_and_chemistry_special_indexes() -> None:
    rows = pairings_for("BASIL", top=100)
    assert len(rows) >= 50
    assert all(r["source_id"] == "FB-PAGE-2008" for r in rows)
    assert any(r["pdf_page"] in {73, 74} for r in rows)
    assert any(r["evidence_level"] == "explicit_pairing_listing" for r in rows)

    topics = chemistry_topics("gelatinization", top=20)
    assert topics
    assert any(r["pdf_page"] in {361, 363, 364} for r in topics)
    assert all(r["source_id"] == "FC-BELITZ-2009" for r in topics)


def test_chinese_professional_terms_bridge_to_english_sources() -> None:
    rewrites = professional_query_rewrites("蛋白质变性 持水性")
    assert "protein denaturation" in rewrites
    assert "water holding capacity" in rewrites

    protein_pages = _pages(search("蛋白质变性", top=30, source="FC-BELITZ-2009"))
    assert ("FC-BELITZ-2009", 102) in protein_pages

    starch_pages = _pages(search("淀粉糊化", top=30, source="FC-BELITZ-2009"))
    assert ("FC-BELITZ-2009", 363) in starch_pages

    water_pages = _pages(search("水分活度", top=30, source="FC-BELITZ-2009"))
    assert ("FC-BELITZ-2009", 48) in water_pages
