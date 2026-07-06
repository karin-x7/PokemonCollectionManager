"""Tests for normalize_for_search's accent/punctuation folding."""

from __future__ import annotations

from app.utils.text_normalize import normalize_for_search


def test_accented_and_plain_spelling_match() -> None:
    assert normalize_for_search("Poképad") == normalize_for_search("pokepad")
    assert normalize_for_search("Poképad") == normalize_for_search("poke pad")


def test_hyphenated_and_plain_spelling_match() -> None:
    assert normalize_for_search("Ho-Oh") == normalize_for_search("hooh")
    assert normalize_for_search("Ho-Oh") == normalize_for_search("ho oh")


def test_case_is_ignored() -> None:
    assert normalize_for_search("BLASTOISE") == normalize_for_search("blastoise")


def test_apostrophes_are_stripped() -> None:
    assert normalize_for_search("Farfetch'd") == normalize_for_search("Farfetchd")


def test_unrelated_words_do_not_match() -> None:
    assert normalize_for_search("Blastoise") != normalize_for_search("Turtok")


def test_empty_string() -> None:
    assert normalize_for_search("") == ""
