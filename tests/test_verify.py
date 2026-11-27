import pytest

from app import verify as verify_module
from app.verify import verify_citations

ARTICLE_4_TEXT = (
    "Art. 4º Durante o prazo estipulado para a duração do contrato, não poderá o "
    "locador reaver o imóvel alugado. O locatário, todavia, poderá devolvê-lo, "
    "pagando a multa pactuada, proporcional ao período de cumprimento do contrato."
)


@pytest.fixture(autouse=True)
def mock_article_lookup(monkeypatch):
    async def fake_fetch(article_number):
        return ARTICLE_4_TEXT if article_number == "4" else None

    monkeypatch.setattr(verify_module, "fetch_article_text", fake_fetch)


async def test_verbatim_quote_verifies():
    results = await verify_citations(
        [{"artigo": "4", "trecho": "não poderá o locador reaver o imóvel alugado"}]
    )
    assert results[0].verified is True


async def test_paraphrased_quote_fails_verification():
    results = await verify_citations(
        [{"artigo": "4", "trecho": "o locador não pode retomar o imóvel durante o contrato"}]
    )
    assert results[0].verified is False


async def test_quote_for_unknown_article_fails():
    results = await verify_citations([{"artigo": "999", "trecho": "qualquer coisa"}])
    assert results[0].verified is False


async def test_verification_ignores_whitespace_and_case_differences():
    results = await verify_citations(
        [{"artigo": "4", "trecho": "NÃO PODERÁ   o locador\nreaver o imóvel alugado"}]
    )
    assert results[0].verified is True


@pytest.mark.parametrize("raw", ["Art. 4", "Art. 4º", "artigo 4", "4º", "4."])
async def test_article_number_formatting_does_not_defeat_lookup(raw):
    # Live testing surfaced this: the model doesn't reliably follow "digits only"
    # formatting instructions, and the DB stores bare "4" -- a naive lookup on
    # whatever the model wrote silently marked every correct citation as unverified.
    results = await verify_citations(
        [{"artigo": raw, "trecho": "não poderá o locador reaver o imóvel alugado"}]
    )
    assert results[0].verified is True


@pytest.mark.parametrize("trivial", ["o", "a", "Art. 4", ". ", "de", "4º", "  "])
async def test_a_quote_too_short_to_carry_a_claim_is_not_verified(trivial):
    # Every one of these is a substring of Article 4, so pure containment marked
    # them "verified" and the UI showed a green check for a citation that says
    # nothing. The badge is the product's central claim; a one-word quote must
    # not earn it.
    results = await verify_citations([{"artigo": "4", "trecho": trivial}])
    assert results[0].verified is False, f"{trivial!r} should not verify"


async def test_a_short_but_real_fragment_still_verifies():
    # The floor is a word count, not a character count: four words of the actual
    # statute is a legitimate quote even though it is brief.
    results = await verify_citations(
        [{"artigo": "4", "trecho": "não poderá o locador reaver"}]
    )
    assert results[0].verified is True


async def test_a_fabricated_rule_still_fails_even_when_long():
    # Length must not be a way to buy a pass: four-plus words that the statute
    # does not contain still fail.
    results = await verify_citations(
        [{"artigo": "4", "trecho": "o locador pode reter integralmente o valor da fiança"}]
    )
    assert results[0].verified is False


def test_lettered_article_keeps_its_letter():
    r"""`Art. 54-A` is not article 54.

    `re.search(r"\d+")` took the first digit run, so 54-A became 54 and a
    citation about 54-A was looked up against Article 54 and certified against
    the wrong text.
    """
    from app.verify import _normalize_article_number

    assert _normalize_article_number("Art. 54-A") == "54-A"
    assert _normalize_article_number("54-A") == "54-A"
    assert _normalize_article_number("artigo 54-a") == "54-A"
    assert _normalize_article_number("Art. 33-A.") == "33-A"


def test_plain_article_number_still_normalizes():
    from app.verify import _normalize_article_number

    for spelling in ("Art. 4º", "4º", "4.", "artigo 4", "Art. 4"):
        assert _normalize_article_number(spelling) == "4", spelling


async def test_a_lettered_article_is_not_certified_against_its_base_article(monkeypatch):
    """The cross-article false positive, closed.

    A citation naming 54-A must not be verified using Article 54's text. When the
    corpus has no 54-A chunk — which it does not, until it is re-ingested — the
    honest answer is "source not found", not a green check against 54.
    """

    async def fake_fetch(article_number):
        return ARTICLE_4_TEXT if article_number == "4" else None

    monkeypatch.setattr(verify_module, "fetch_article_text", fake_fetch)

    results = await verify_citations(
        [{"artigo": "4-A", "trecho": "não poderá o locador reaver o imóvel alugado"}]
    )

    assert results[0].article_number == "4-A"
    assert results[0].article_text is None
    assert results[0].verified is False
