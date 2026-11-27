"""Line-break hyphens must not become dashes in the statute text.

Planalto marks a hyphenated word with markup around the hyphen itself:
`transmite<b>-</b>se`. `get_text(separator="\\n")` puts a newline between every
text node, so the hyphen arrives alone on its line and whitespace collapsing
turns `transmite-se` into `transmite - se`.

The consequences both run the wrong way: a model quoting the real statute fails
verification (the quote is not in the corrupted text), and the UI presents the
corrupted string as the authoritative article. The committed corpus carried 45 of
these across 27 of its 90 articles.
"""

from __future__ import annotations

from ingest.fetch_law import extract_text, join_broken_hyphens


def test_a_hyphen_split_by_markup_is_rejoined():
    html = "<p>Art. 10. Morrendo o locador, a locação transmite<b>-</b>se aos herdeiros.</p>"
    assert "transmite-se" in extract_text(html)


def test_every_shape_of_split_hyphen_is_rejoined():
    for markup in ("<b>-</b>", "<i>-</i>", "<span>-</span>", "<u>-</u>"):
        with_sub = f"<p>O imóvel habite{markup}se agora.</p>"
        assert "habite-se" in extract_text(with_sub), markup


def test_a_spaced_dash_between_words_is_left_alone():
    # A paragraph dash is one text node, so the pattern never fires on it.
    html = "<p>Art. 1º - Texto com travessão espaçado.</p>"
    text = extract_text(html)
    assert " - Texto" in text
    assert "1º-Texto" not in text


def test_a_normal_sentence_is_unchanged():
    assert extract_text("<p>Art. 2º Texto normal, sem hífen.</p>").strip() == (
        "Art. 2º Texto normal, sem hífen."
    )


def test_a_line_leading_dash_outside_a_word_is_left_alone():
    # No word character before it, so it is not a broken compound.
    assert join_broken_hyphens("texto\n- item") == "texto\n- item"


def test_an_already_correct_compound_is_untouched():
    assert join_broken_hyphens("transmite-se") == "transmite-se"
