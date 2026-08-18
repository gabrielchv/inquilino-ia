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
