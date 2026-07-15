"""Tests for the pure, OS-agnostic URL-building/text-parsing logic shared by
every platform's browser-reading backend.

A window-reading function has no deterministic, sandboxable behaviour to
test against (it depends on a real browser window actually being open on
screen), so those are verified manually instead (see PROJECT_PROGRESS.md) --
the one exception, ``_read_visible_text``, takes a fake window object and is
tested in ``test_browser_windows.py`` instead, since it lives in the
Windows-specific backend, not here.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.models.enums import Condition, Language
from app.pricing.cardmarket_parsing import (
    _find_breadcrumb_set_name,
    _has_bot_check,
    _has_cookie_banner,
    _parse_offer_lines,
    _parse_product_info,
    _parse_search_result_line,
    _parse_sealed_offer_lines,
    _parse_sealed_product_info,
    SELLER_COUNTRY_GERMANY_ID,
    build_filtered_url,
    build_sealed_filtered_url,
    find_alternate_version_url,
    is_unresolved_pokemontcg_shortlink,
    resolve_cardmarket_url,
    sealed_supports_language_filter,
    supports_language_filter,
    with_canonical_locale,
)
from app.pricing.models import (
    CardmarketOffer,
    CardmarketSearchResult,
    ProductInfo,
    SealedOffer,
    SealedProductInfo,
)


def test_parses_a_realistic_page_dump_into_offers() -> None:
    # Mirrors the real token sequence observed live on a Cardmarket product
    # page (seller rating, seller name, condition, [comment], price, qty),
    # with a language flag's accessible name inline as its own token, plus
    # unrelated summary-stat prices (e.g. "7-days average price") before the
    # real offer rows that must be ignored as noise.
    lines = [
        "Available items", "78", "From", "13,90 €",
        "7-days average price", "185,65 €",
        "159", "K", "CardGameCorner", "Italian", "PO", "13,90 €", "1",
        "66", "pokerina", "German", "PO", "Ask for more photos", "24,99 €", "1",
        "14", "K", "LevelUp-Wehavefun", "German", "GD", "front NM", "47,45 €", "1",
        "952", "M2workshop", "English", "NM", "59,90 €", "1",
    ]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(
            seller="CardGameCorner",
            condition=Condition.POOR,
            language=Language.ITALIAN,
            price=13.90,
        ),
        CardmarketOffer(
            seller="pokerina", condition=Condition.POOR, language=Language.GERMAN, price=24.99
        ),
        CardmarketOffer(
            seller="LevelUp-Wehavefun",
            condition=Condition.GOOD,
            language=Language.GERMAN,
            price=47.45,
        ),
        CardmarketOffer(
            seller="M2workshop",
            condition=Condition.NEAR_MINT,
            language=Language.ENGLISH,
            price=59.90,
        ),
    ]


def test_mint_condition_code_is_mt_not_m() -> None:
    lines = ["1", "Seller", "German", "MT", "100,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(
            seller="Seller", condition=Condition.MINT, language=Language.GERMAN, price=100.0
        )
    ]


def test_unrecognised_language_flag_yields_none_but_keeps_the_offer() -> None:
    lines = ["1", "Seller", "Klingon", "NM", "10,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(seller="Seller", condition=Condition.NEAR_MINT, language=None, price=10.0)
    ]


def test_row_without_a_condition_badge_is_dropped_as_noise() -> None:
    lines = ["7-days average price", "185,65 €", "1-day average price", "404,70 €"]

    assert _parse_offer_lines(lines) == []


def test_thousands_separator_price_is_parsed_correctly() -> None:
    lines = ["1", "Seller", "German", "MT", "1.049,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers[0].price == 1049.0


def test_english_locale_number_format_is_parsed_correctly() -> None:
    """Real bug: a card whose resolved Cardmarket URL happened to use the

    ``/en/`` locale prefix rendered every price as "1,550.00 €" (comma
    thousands separator, period decimal point) instead of the German
    "1.550,00 €" the original regex assumed -- silently matching zero
    prices and reporting "no offers found" despite a page full of them.
    """
    lines = ["1", "Seller", "English", "NM", "1,550.00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers[0].price == 1550.0


def test_english_locale_number_format_without_thousands_separator() -> None:
    lines = ["1", "Seller", "English", "NM", "13.90 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers[0].price == 13.90


def test_empty_input_returns_empty_list() -> None:
    assert _parse_offer_lines([]) == []


# --- build_filtered_url / supports_language_filter ------------------------ #
# Ids confirmed live by reading Cardmarket's own filter form inputs (not
# documented anywhere public) — see PROJECT_PROGRESS.md, Schritt 7 follow-up.


def test_supports_language_filter_true_for_western_languages() -> None:
    assert supports_language_filter(Language.GERMAN) is True
    assert supports_language_filter(Language.ENGLISH) is True


def test_supports_language_filter_true_for_asian_languages() -> None:
    # Live-reported (with a screenshot): ?language=7&minCondition=... on an
    # ordinary single card's own product page correctly narrowed straight to
    # its Japanese/Excellent-or-better offers -- the same filter ids the
    # sealed-product table already used. The "separate product" scenario
    # (e.g. Neo Revelation's Ho-Oh being "Awakening Legends") is real but
    # narrower than previously assumed: specific vintage/reprint sets whose
    # stored URL points at the wrong product entirely, not a general
    # property of these three languages -- see PriceService's alternate-
    # version retry and the manual-Cardmarket-link override for that case.
    assert supports_language_filter(Language.JAPANESE) is True
    assert supports_language_filter(Language.KOREAN) is True
    assert supports_language_filter(Language.CHINESE) is True


def test_build_filtered_url_with_no_filters_returns_base_url_unchanged() -> None:
    url = "https://www.cardmarket.com/de/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    assert build_filtered_url(url) == url


def test_build_filtered_url_language_only() -> None:
    url = build_filtered_url("https://cardmarket.com/x", language=Language.GERMAN)
    assert url == "https://cardmarket.com/x?language=3"


def test_build_filtered_url_condition_only() -> None:
    url = build_filtered_url("https://cardmarket.com/x", min_condition=Condition.GOOD)
    assert url == "https://cardmarket.com/x?minCondition=4"


def test_build_filtered_url_language_and_condition_combined() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", language=Language.ENGLISH, min_condition=Condition.NEAR_MINT
    )
    assert url == "https://cardmarket.com/x?language=1&minCondition=2"


def test_build_filtered_url_supports_japanese_too() -> None:
    # Every Language enum member now has a Cardmarket filter id (see
    # test_supports_language_filter_true_for_asian_languages) -- there is no
    # longer an "unsupported, silently ignored" language to test.
    url = build_filtered_url(
        "https://cardmarket.com/x", language=Language.JAPANESE, min_condition=Condition.GOOD
    )
    assert url == "https://cardmarket.com/x?language=7&minCondition=4"


def test_build_filtered_url_appends_to_an_already_queried_base_url() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x?utm_source=pokemontcgio", language=Language.GERMAN
    )
    assert url == "https://cardmarket.com/x?utm_source=pokemontcgio&language=3"


def test_build_filtered_url_seller_country_only() -> None:
    url = build_filtered_url("https://cardmarket.com/x", seller_country=SELLER_COUNTRY_GERMANY_ID)
    assert url == f"https://cardmarket.com/x?sellerCountry={SELLER_COUNTRY_GERMANY_ID}"


def test_build_filtered_url_seller_country_none_omits_the_filter() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", language=Language.GERMAN, seller_country=None
    )
    assert "sellerCountry" not in url


def test_build_filtered_url_seller_country_combined_with_language_and_condition() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x",
        language=Language.GERMAN,
        min_condition=Condition.GOOD,
        seller_country=SELLER_COUNTRY_GERMANY_ID,
    )
    assert url == (
        f"https://cardmarket.com/x?language=3&minCondition=4"
        f"&sellerCountry={SELLER_COUNTRY_GERMANY_ID}"
    )


# --- sealed_supports_language_filter / build_sealed_filtered_url ----------- #
# Unlike single cards, a sealed product's Cardmarket page genuinely does
# expose Japanese/Korean/Traditional Chinese as a language filter on the
# *same* page -- live-confirmed against a real Asian-exclusive-only set
# ("Abyss Eye Booster Box"): its own filter sidebar lists exactly these
# three languages, and clicking each checkbox produced ?language=7
# (Japanese), ?language=10 (Korean), ?language=11 (Traditional Chinese).


def test_sealed_supports_language_filter_true_for_western_and_asian_languages() -> None:
    assert sealed_supports_language_filter(Language.GERMAN) is True
    assert sealed_supports_language_filter(Language.JAPANESE) is True
    assert sealed_supports_language_filter(Language.KOREAN) is True
    assert sealed_supports_language_filter(Language.CHINESE) is True


def test_build_sealed_filtered_url_japanese_korean_and_chinese() -> None:
    base = "https://cardmarket.com/x"
    assert build_sealed_filtered_url(base, Language.JAPANESE) == f"{base}?language=7"
    assert build_sealed_filtered_url(base, Language.KOREAN) == f"{base}?language=10"
    assert build_sealed_filtered_url(base, Language.CHINESE) == f"{base}?language=11"


def test_build_sealed_filtered_url_appends_to_an_already_queried_base_url() -> None:
    url = build_sealed_filtered_url(
        "https://cardmarket.com/x?utm_source=pokemontcgio", Language.JAPANESE
    )
    assert url == "https://cardmarket.com/x?utm_source=pokemontcgio&language=7"


def test_build_sealed_filtered_url_is_idempotent_replaces_not_stacks() -> None:
    # Price lookups re-derive the filter fresh from whatever is stored (see
    # SealedPriceService), which may already carry a ?language= from a
    # previous add/edit -- calling this again must replace it, not stack a
    # second &language= onto the URL.
    already_filtered = "https://cardmarket.com/x?language=3"
    assert build_sealed_filtered_url(already_filtered, Language.GERMAN) == already_filtered
    assert (
        build_sealed_filtered_url(already_filtered, Language.JAPANESE)
        == "https://cardmarket.com/x?language=7"
    )


def test_build_sealed_filtered_url_seller_country() -> None:
    url = build_sealed_filtered_url(
        "https://cardmarket.com/x", Language.GERMAN, seller_country=SELLER_COUNTRY_GERMANY_ID
    )
    assert url == f"https://cardmarket.com/x?language=3&sellerCountry={SELLER_COUNTRY_GERMANY_ID}"


def test_build_sealed_filtered_url_seller_country_is_idempotent_replaces_not_stacks() -> None:
    already_filtered = (
        f"https://cardmarket.com/x?language=3&sellerCountry={SELLER_COUNTRY_GERMANY_ID}"
    )
    # Dropping the seller-location preference (seller_country=None) must
    # remove the existing &sellerCountry=, not just leave it stale.
    assert (
        build_sealed_filtered_url(already_filtered, Language.GERMAN, seller_country=None)
        == "https://cardmarket.com/x?language=3"
    )


# --- build_filtered_url: signed / first_edition / altered / reverse_holo ----- #
# Cardmarket's own isSigned/isFirstEd/isAltered/isReverseHolo filters -- all
# four *bare* top-level parameters, none nested under extra[...]. Live
# re-confirmed (2026-07-06) against the exact URLs Cardmarket's own filter
# sidebar produces when the checkboxes are clicked directly
# (".../Cacturne-SS2?language=1&minCondition=2&isReverseHolo=N&isSigned=N
# &isFirstEd=N&isAltered=N") -- an earlier round of research had
# isSigned/isFirstEd/isAltered wrongly wrapped as extra[isSigned] etc.,
# which most likely broke the whole filter's server-side binding rather
# than just being ignored (a real, live-reported symptom: a card explicitly
# set to *not* reverse holo still priced from a reverse-holo-only offer,
# meaning the isReverseHolo=N filter had silently had no effect at all).
# Unlike language/condition, callers pass these as a definite True/False
# almost always -- a real card either is or isn't signed.


def test_build_filtered_url_signed_true_and_false() -> None:
    assert build_filtered_url("https://cardmarket.com/x", signed=True) == (
        "https://cardmarket.com/x?isSigned=Y"
    )
    assert build_filtered_url("https://cardmarket.com/x", signed=False) == (
        "https://cardmarket.com/x?isSigned=N"
    )


def test_build_filtered_url_first_edition_and_altered() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", first_edition=True, altered=False
    )
    assert url == "https://cardmarket.com/x?isFirstEd=Y&isAltered=N"


def test_build_filtered_url_extras_unset_by_default() -> None:
    # None (unset) means "don't add this filter at all" -- distinct from
    # False ("Nein"), which does add it.
    assert build_filtered_url("https://cardmarket.com/x") == "https://cardmarket.com/x"


def test_build_filtered_url_combines_everything() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x",
        language=Language.GERMAN,
        min_condition=Condition.NEAR_MINT,
        signed=True,
        first_edition=False,
        altered=False,
        reverse_holo=True,
    )
    assert url == (
        "https://cardmarket.com/x?language=3&minCondition=2"
        "&isSigned=Y&isFirstEd=N&isAltered=N"
        "&isReverseHolo=Y"
    )


def test_build_filtered_url_reverse_holo_true_and_false() -> None:
    assert build_filtered_url("https://cardmarket.com/x", reverse_holo=True) == (
        "https://cardmarket.com/x?isReverseHolo=Y"
    )
    assert build_filtered_url("https://cardmarket.com/x", reverse_holo=False) == (
        "https://cardmarket.com/x?isReverseHolo=N"
    )


# --- _parse_product_info ---------------------------------------------------- #
# Backs "Karte manuell eintragen": Cardmarket's own product-page title,
# live-confirmed as "<Name> (<Number>) - <Set> | Cardmarket".


def test_parse_product_info_finds_title_among_page_noise() -> None:
    lines = [
        "Venusaur (18) - Legendary Collection | Cardmarket - Google Chrome",
        "Minimieren",
        "Zurück",
        "Venusaur (18) - Legendary Collection | Cardmarket",
        "Toggle navigation",
    ]

    info = _parse_product_info(lines)

    assert info == ProductInfo(name="Venusaur", set_name="Legendary Collection", card_number="18")


def test_parse_product_info_handles_blank_card_number() -> None:
    lines = ["Ho-Oh () - Awakening Legends | Cardmarket - Google Chrome"]

    info = _parse_product_info(lines)

    assert info == ProductInfo(name="Ho-Oh", set_name="Awakening Legends", card_number="")


def test_parse_product_info_returns_none_when_no_title_line_matches() -> None:
    assert _parse_product_info(["Some random page", "404 Not Found"]) is None


def test_parse_product_info_detects_the_dominant_offer_language() -> None:
    # Real, live-reported bug: the add-card dialog's language dropdown always
    # defaulted to English regardless of what was actually pasted -- the
    # product page's own offer rows (already scraped for the same read) are
    # a much better starting guess than a hardcoded constant.
    lines = [
        "Nachtara-GX (36) - SM Schwarzstern Promos | Cardmarket - Google Chrome",
        "Nachtara-GX (36) - SM Schwarzstern Promos | Cardmarket",
        "66", "pokerina", "German", "PO", "24,99 €", "1",
        "14", "K", "LevelUp-Wehavefun", "German", "GD", "47,45 €", "1",
        "952", "M2workshop", "English", "NM", "59,90 €", "1",
    ]

    info = _parse_product_info(lines)

    assert info.detected_language == Language.GERMAN


def test_parse_product_info_detected_language_is_none_without_any_offers() -> None:
    lines = [
        "Venusaur (18) - Legendary Collection | Cardmarket - Google Chrome",
        "Currently out of stock",
    ]

    info = _parse_product_info(lines)

    assert info.detected_language is None


#: A trimmed but structurally faithful slice of a real, live-captured
#: "Shining Mew" (Cardmarket's "Unnumbered Promos" category) page dump --
#: see _find_breadcrumb_set_name's own docs for the breadcrumb shape this
#: relies on.
_UNNUMBERED_PROMO_LINES = [
    "Shining Mew | Cardmarket - Google Chrome",
    "Minimieren",
    "Shining Mew | Cardmarket",
    "Toggle navigation",
    "breadcrumb",
    "Startseite",
    "/Produkte (Pokémon)",
    "/",
    "Produkte (Pokémon)",
    "/Einzelkarten",
    "/",
    "Einzelkarten",
    "/Unnumbered Promos",
    "/",
    "Unnumbered Promos",
    "/Shining Mew",
    "/",
]


def test_parse_product_info_falls_back_to_bare_title_for_unnumbered_promos() -> None:
    # Real, live-confirmed bug: an unnumbered promo ("Shining Mew" from
    # Cardmarket's own "Unnumbered Promos" category) drops the whole
    # "(Number) - Set" clause from its title instead of leaving it blank --
    # rendering as just "Shining Mew | Cardmarket", the same bare form
    # sealed products use. Without this fallback, _parse_product_info
    # returned None for every such promo, silently failing the entire
    # "Karte manuell eintragen" flow (the tab opened, but no card was ever
    # added) even though the page was a perfectly real product page.
    info = _parse_product_info(_UNNUMBERED_PROMO_LINES)

    assert info == ProductInfo(name="Shining Mew", set_name="Unnumbered Promos", card_number="")


def test_parse_product_info_translates_a_foreign_name_to_english(monkeypatch) -> None:
    # Live-reported: on a non-English Cardmarket locale (cardmarket.com/de/...)
    # the page's own title is in that language ("Despotar V"), not English
    # ("Tyranitar V") -- every other card is stored under its English name,
    # so a manually-entered one should be too.
    monkeypatch.setattr(
        "app.pricing.cardmarket_parsing.translate_name_with_suffix",
        lambda name: "Tyranitar V" if name == "Despotar V" else None,
    )
    lines = ["Despotar V (V3) - Single Strike Master | Cardmarket - Google Chrome"]

    info = _parse_product_info(lines)

    assert info == ProductInfo(name="Tyranitar V", set_name="Single Strike Master", card_number="V3")


def test_parse_product_info_translates_the_bare_title_fallback_too(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.pricing.cardmarket_parsing.translate_name_with_suffix",
        lambda name: "Ho-Oh" if name == "Homolog" else None,
    )
    lines = ["Homolog | Cardmarket - Google Chrome", "Homolog | Cardmarket"]

    info = _parse_product_info(lines)

    assert info.name == "Ho-Oh"


def test_find_breadcrumb_set_name_reads_the_label_before_the_current_page() -> None:
    assert (
        _find_breadcrumb_set_name(_UNNUMBERED_PROMO_LINES, "Shining Mew") == "Unnumbered Promos"
    )


def test_find_breadcrumb_set_name_blank_when_no_matching_breadcrumb_entry() -> None:
    assert _find_breadcrumb_set_name(["Some random page", "404 Not Found"], "Shining Mew") == ""


# --- _parse_sealed_product_info ---------------------------------------------- #
# Live-confirmed real dump (Base Set Booster Box): title is just
# "<Name> | Cardmarket" (no number/set, unlike single cards), and the
# breadcrumb's own trailing text is "<Name> <Category>" in one node.


def test_parse_sealed_product_info_finds_name_and_category() -> None:
    lines = [
        "Base Set Booster Box | Cardmarket - Google Chrome",
        "Minimieren",
        "/Products (Pokémon)",
        "Products (Pokémon)",
        "/Booster Boxes",
        "Booster Boxes",
        "/Base Set Booster Box",
        "Base Set Booster Box Booster Boxes",
        "Base Set Booster Box | Cardmarket",
    ]

    info = _parse_sealed_product_info(lines)

    # Normalised from Cardmarket's raw "Booster Boxes" breadcrumb wording to
    # the fixed SealedCategory label (see app/models/enums.py).
    assert info == SealedProductInfo(name="Base Set Booster Box", category="Booster Box")


def test_parse_sealed_product_info_blank_category_when_breadcrumb_not_found() -> None:
    lines = ["Evolutions Elite Trainer Box | Cardmarket - Google Chrome"]

    info = _parse_sealed_product_info(lines)

    assert info == SealedProductInfo(name="Evolutions Elite Trainer Box", category="")


def test_parse_sealed_product_info_returns_none_when_no_title_line_matches() -> None:
    assert _parse_sealed_product_info(["Some random page", "404 Not Found"]) is None


# --- _parse_search_result_line ------------------------------------------------ #
# Backs "Cardmarket-Link suchen": a search-result page's own hyperlinks
# flatten every descendant text node into one accessible name, live-confirmed
# as "<Name> <Set> \xa0<Name> (<Code>) From <Price>" against a real search
# for "Poke Pad" (Perfect Order, a newly released set pokemontcg.io itself
# had no Cardmarket link for at all).


def test_parse_search_result_line_matches_a_real_result() -> None:
    text = "Poké Pad Perfect Order \xa0Poké Pad (POR 113) From 9,00 €"

    result = _parse_search_result_line(text)

    assert result == CardmarketSearchResult(
        name="Poké Pad",
        set_name="Perfect Order",
        card_number="POR 113",
        price_hint="9,00 €",
        raw_text=text,
    )


def test_parse_search_result_line_handles_a_multi_word_set_name() -> None:
    text = (
        "Poké Pad MEGA Start Deck 100 Battle Collection Corociao Version "
        "\xa0Poké Pad (mP1 015) From 0,19 €"
    )

    result = _parse_search_result_line(text)

    assert result is not None
    assert result.set_name == "MEGA Start Deck 100 Battle Collection Corociao Version"
    assert result.card_number == "mP1 015"


def test_parse_search_result_line_handles_no_offers_price_hint() -> None:
    text = "Poké Pad Void Blast \xa0Poké Pad (MA4 160) From N/A"

    result = _parse_search_result_line(text)

    assert result is not None
    assert result.price_hint == "N/A"


def test_parse_search_result_line_returns_none_for_unrelated_text() -> None:
    assert _parse_search_result_line("Toggle navigation") is None
    assert _parse_search_result_line("Search Results | Cardmarket") is None


# --- _parse_sealed_offer_lines ------------------------------------------------ #
# Live-confirmed real dump (Base Set Booster Box): no condition badge at all
# per row, unlike single cards -- a language token is the signal instead.


def test_parse_sealed_offer_lines_finds_offers_without_condition() -> None:
    # Mirrors the real token sequence observed live on a Cardmarket sealed
    # product page (rating, seller, language, comment, price, quantity, a
    # trailing "you have to be logged in..." disabled-buy-button line before
    # the *next* row's own rating number starts) -- same shape as card offer
    # rows, just without a condition badge.
    lines = [
        "0",
        "Item location: Germany",
        "Loki89",
        "German",
        "Original Base Set von 1999 versiegelt",
        "5.000,00 €",
        "1",
        "You have to be logged in to be able to buy items.",
        "564",
        "Item location: Switzerland",
        "Marsi",
        "German",
        "only pick up no shipping",
        "21.000,00 €",
        "1",
        "You have to be logged in to be able to buy items.",
    ]

    offers = _parse_sealed_offer_lines(lines)

    assert len(offers) == 2
    assert offers[0] == SealedOffer(
        seller="Item location: Germany", language=Language.GERMAN, price=5000.0
    )
    # Same pre-existing, accepted quirk as the card offer parser: the
    # trailing "logged in..." line from the *previous* row isn't consumed
    # by the quantity-skip, so it leaks into this row's span as the first
    # non-digit token and wins the seller pick -- cosmetic only (not used
    # for price-matching), so this isn't something to "fix" here.
    assert offers[1].language is Language.GERMAN
    assert offers[1].price == 21000.0


def test_parse_sealed_offer_lines_finds_offers_on_a_german_locale_page() -> None:
    # Real bug, live-confirmed: a Cardmarket URL with a "/de/" path prefix
    # (what a user browsing Cardmarket in German actually copies) renders
    # the offer table's language word in German ("Deutsch"/"Englisch"/...),
    # not English ("German"/"English"/...) -- without German words in the
    # lookup table, every offer on such a page silently parsed to zero,
    # since sealed products (unlike cards) gate on the language token.
    lines = [
        "0",
        "Artikelstandort: Deutschland",
        "shadowk3",
        "Deutsch",
        "5,99 €",
        "2",
        "Du musst eingeloggt sein, um einkaufen zu können",
    ]

    offers = _parse_sealed_offer_lines(lines)

    assert len(offers) == 1
    assert offers[0].language is Language.GERMAN
    assert offers[0].price == 5.99


def test_parse_sealed_offer_lines_unrecognised_language_drops_the_row() -> None:
    # Unlike cards (where the *condition* validates a row and an
    # unrecognised language is just kept as None), sealed products have no
    # condition at all -- language is the only row-validity signal there is,
    # so a language Cardmarket sells in but this project's own enum doesn't
    # know (e.g. Dutch) means the whole row is silently dropped, not kept
    # with language=None.
    lines = [
        "6",
        "Item location: Belgium",
        "Flash-cards",
        "Professional",
        "Dutch",
        "sealed with acryl",
        "19.950,00 €",
        "1",
        "You have to be logged in to be able to buy items.",
    ]

    assert _parse_sealed_offer_lines(lines) == []


# --- with_canonical_locale --------------------------------------------------- #
# Used only when reading offers, never when reading a product's own name --
# see its docstring for why (locale-independent offer-table vocabulary,
# without needing a translated word list per locale).


def test_with_canonical_locale_rewrites_german_to_english() -> None:
    url = "https://www.cardmarket.com/de/Pokemon/Products/Boosters/Destined-Rivals-Booster"

    assert with_canonical_locale(url) == (
        "https://www.cardmarket.com/en/Pokemon/Products/Boosters/Destined-Rivals-Booster"
    )


def test_with_canonical_locale_preserves_query_string() -> None:
    url = "https://www.cardmarket.com/fr/Pokemon/Products/Boosters/Destined-Rivals-Booster?language=3"

    assert with_canonical_locale(url) == (
        "https://www.cardmarket.com/en/Pokemon/Products/Boosters/Destined-Rivals-Booster?language=3"
    )


def test_with_canonical_locale_is_a_no_op_when_already_english() -> None:
    url = "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box"

    assert with_canonical_locale(url) == url


def test_with_canonical_locale_supports_a_custom_target_locale() -> None:
    url = "https://www.cardmarket.com/de/Pokemon/Products/Boosters/Destined-Rivals-Booster"

    assert with_canonical_locale(url, locale="fr") == (
        "https://www.cardmarket.com/fr/Pokemon/Products/Boosters/Destined-Rivals-Booster"
    )


def test_with_canonical_locale_leaves_unrecognised_urls_unchanged() -> None:
    url = "https://example.com/not-a-cardmarket-url"

    assert with_canonical_locale(url) == url


# --- _has_cookie_banner ------------------------------------------------------ #
# Live-confirmed intermittent: a brand-new Chrome profile's very first
# Cardmarket visit (any user of a public build of this app, not just a
# locale-switch artifact) can show a cookie-consent banner that briefly
# delays the real page content -- this is the signal the retry loop in
# _open_and_capture_visible_text checks for.


def test_has_cookie_banner_detects_the_real_banner_text() -> None:
    lines = ["Some page content", "Cardmarket uses cookies and other related tools.", "More"]

    assert _has_cookie_banner(lines) is True


def test_has_cookie_banner_false_for_a_normal_page() -> None:
    lines = ["Available items", "78", "From", "13,90 €"]

    assert _has_cookie_banner(lines) is False


# --- _has_bot_check ---------------------------------------------------------- #
# Live-reported: Cardmarket's own Cloudflare "Checking your Browser…"
# interstitial has enough of its own chrome/branding text to clear
# _MIN_EXPECTED_LINES on its own, so it was previously accepted as a normal,
# fully-rendered page with zero offers -- see _has_bot_check's own docstring.


def test_has_bot_check_detects_the_real_interstitial_text() -> None:
    lines = [
        "Nur einen Moment… - Google Chrome",
        "Sicherheitsüberprüfung wird durchgeführt",
        "Checking your Browser…",
        "Cloudflare",
        "Ray ID: ",
        "a1a81f3b9f654860",
    ]

    assert _has_bot_check(lines) is True


def test_has_bot_check_false_for_a_normal_page() -> None:
    lines = ["Available items", "78", "From", "13,90 €"]

    assert _has_bot_check(lines) is False


def test_has_bot_check_false_when_only_one_of_the_two_markers_present() -> None:
    # Neither "Cloudflare" nor "Ray ID" alone is distinctive enough on its
    # own (e.g. a page merely mentioning Cloudflare in unrelated content).
    assert _has_bot_check(["Cloudflare is a company"]) is False
    assert _has_bot_check(["Ray ID number unrelated"]) is False


# --- resolve_cardmarket_url ------------------------------------------------ #
# pokemontcg.io's cardmarket_url is a tracking shortlink whose redirect target
# is fixed on their end -- query filters appended to the shortlink itself are
# silently dropped. Resolving to the real cardmarket.com URL first is what
# lets build_filtered_url's parameters actually take effect.


def _session_redirecting_to(final_url: str) -> MagicMock:
    response = MagicMock()
    response.url = final_url
    session = MagicMock()
    session.get.return_value = response
    return session


def test_resolve_cardmarket_url_follows_the_redirect() -> None:
    session = _session_redirecting_to(
        "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    )

    result = resolve_cardmarket_url(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", session=session
    )

    assert result == "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    session.get.assert_called_once_with(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", allow_redirects=True, timeout=10
    )


def test_is_unresolved_pokemontcg_shortlink_true_for_the_tracking_link() -> None:
    assert is_unresolved_pokemontcg_shortlink("https://prices.pokemontcg.io/cardmarket/base1-4")


def test_is_unresolved_pokemontcg_shortlink_false_for_a_real_cardmarket_url() -> None:
    assert not is_unresolved_pokemontcg_shortlink(
        "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard-V1-BS4"
    )


def test_resolve_cardmarket_url_falls_back_to_original_on_request_error() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    result = resolve_cardmarket_url(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", session=session, retry_delay=0
    )

    assert result == "https://prices.pokemontcg.io/cardmarket/skg-h32"
    assert session.get.call_count == 2  # one retry before giving up


def test_resolve_cardmarket_url_retries_once_on_timeout_and_succeeds() -> None:
    """Real incident: pokemontcg.io itself (the host behind this shortlink)

    measured live taking >30s to respond during a brief slow period, past
    this function's own timeout -- a single retry should give a second
    chance instead of silently falling back to the unresolved shortlink
    (which doesn't render as a real Cardmarket product page in Chrome).
    """
    resolved = MagicMock()
    resolved.url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    session = MagicMock()
    session.get.side_effect = [requests.Timeout("slow"), resolved]

    result = resolve_cardmarket_url(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", session=session, retry_delay=0
    )

    assert result == "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    assert session.get.call_count == 2


# --- find_alternate_version_url --------------------------------------------- #
# Real, confirmed case: Cardmarket lists Base Set's Venusaur as two entirely
# separate products -- "-V2-" (English only) and "-V1-" (multi-language).
# pokemontcg.io links the wrong one for a non-English card.


def test_prefers_the_lower_sibling_version() -> None:
    url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V2-BS15"

    result = find_alternate_version_url(url)

    assert result == "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V1-BS15"


def test_falls_back_to_the_higher_sibling_when_already_at_v1() -> None:
    url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V1-BS15"

    result = find_alternate_version_url(url)

    assert result == "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V2-BS15"


def test_returns_none_for_a_url_without_a_version_suffix() -> None:
    """Modern cards' URLs never have this problem at all -- must not

    invent a version suffix that was never there. Also proves "VMAX" alone
    (a "-V" followed by a letter, not a digit) is never mistaken for one.
    """
    url = "https://cardmarket.com/en/Pokemon/Products/Singles/Fusion-Strike/Espeon-VMAX"

    assert find_alternate_version_url(url) is None


def test_handles_a_version_suffix_with_no_trailing_dash() -> None:
    """Real, live-confirmed case: the suffix isn't always followed by

    another "-" -- some product slugs end right at the version number
    (here, right before the "?query" part), unlike "Venusaur-V2-BS15"
    above. Also proves "VMAX" earlier in the same slug is correctly
    skipped in favour of the real version marker.
    """
    url = "https://cardmarket.com/en/Pokemon/Products/Singles/Evolving-Skies/Umbreon-VMAX-V1?utm_source=pokemontcgio"

    result = find_alternate_version_url(url)

    assert result == (
        "https://cardmarket.com/en/Pokemon/Products/Singles/Evolving-Skies/Umbreon-VMAX-V2?utm_source=pokemontcgio"
    )


