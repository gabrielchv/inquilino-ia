"""The eval must fail a fabricated quote, not just a wrong article number.

`_run_one` used to score `bool(cited & expected)` and never call
`verify_citations`, so a response could name the right article, invent the quote,
and pass. The project's whole claim is that the quote is checked, so the eval has
to be able to detect a regression in exactly that property.

No network and no Gemini: the model calls and the statute lookup are stubbed.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from app import verify as verify_module

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("run_eval", ROOT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(run_eval)

ARTICLE_4 = (
    "Art. 4º Durante o prazo estipulado para a duração do contrato, não poderá o "
    "locador reaver o imóvel alugado. O locatário, todavia, poderá devolvê-lo, "
    "pagando a multa pactuada, proporcional ao período de cumprimento do contrato."
)

VERBATIM = "não poderá o locador reaver o imóvel alugado"
FABRICATED = "o locador pode reter integralmente o valor da fiança do inquilino"


def _install(monkeypatch, *, answer: str, citations: list[dict]) -> None:
    async def fake_retrieve(_question):
        return []

    async def fake_generate_json(*_args, **_kwargs):
        return {"citacoes": citations}

    async def fake_fetch(article_number):
        return ARTICLE_4 if article_number == "4" else None

    def _articles_block(_chunks):
        return ARTICLE_4

    monkeypatch.setattr(run_eval, "retrieve", fake_retrieve)
    monkeypatch.setattr(run_eval, "generate_json", fake_generate_json)
    monkeypatch.setattr(run_eval, "_articles_block", _articles_block)
    monkeypatch.setattr(verify_module, "fetch_article_text", fake_fetch)

    class _Stream:
        def __aiter__(self):
            async def gen():
                yield answer

            return gen()

    from app import gemini_client

    monkeypatch.setattr(gemini_client, "generate_stream", lambda *_a, **_k: _Stream())


def _case(expected: list[str]) -> dict:
    return {"question": "Posso sair antes do prazo?", "expected_articles": expected}


def test_a_fabricated_quote_fails_even_with_the_right_article(monkeypatch):
    """The regression: right article number, invented quote, clean pass before."""
    _install(
        monkeypatch,
        answer="O locador pode reter a fiança.",
        citations=[{"artigo": "4", "trecho": FABRICATED}],
    )

    passed, detail = asyncio.run(run_eval._run_one(_case(["4"])))

    assert passed is False, detail
    assert "failed verification" in detail


def test_a_verbatim_quote_passes(monkeypatch):
    _install(
        monkeypatch,
        answer="Não poderá o locador reaver o imóvel alugado.",
        citations=[{"artigo": "4", "trecho": VERBATIM}],
    )

    passed, detail = asyncio.run(run_eval._run_one(_case(["4"])))

    assert passed is True, detail


def test_article_spelling_does_not_defeat_the_comparison(monkeypatch):
    """`Art. 4º` is article 4; comparing raw strings scored that as a miss."""
    _install(
        monkeypatch,
        answer="Não poderá o locador reaver o imóvel alugado.",
        citations=[{"artigo": "Art. 4º", "trecho": VERBATIM}],
    )

    passed, detail = asyncio.run(run_eval._run_one(_case(["4"])))

    assert passed is True, detail


def test_a_wrong_article_still_fails(monkeypatch):
    _install(
        monkeypatch,
        answer="Alguma resposta.",
        citations=[{"artigo": "22", "trecho": VERBATIM}],
    )

    passed, detail = asyncio.run(run_eval._run_one(_case(["4"])))

    assert passed is False
    assert "expected" in detail


def test_a_refusal_with_an_extra_sentence_counts_as_a_refusal(monkeypatch):
    """Exact string equality treated a correct, polite refusal as a failure."""
    from app.chat import REFUSAL_SENTENCE

    _install(
        monkeypatch,
        answer=f"{REFUSAL_SENTENCE} Se tiver outra dúvida, é só perguntar.",
        citations=[],
    )

    passed, detail = asyncio.run(run_eval._run_one(_case([])))

    assert passed is True, detail


def test_a_refusal_is_detected_for_an_in_scope_question(monkeypatch):
    from app.chat import REFUSAL_SENTENCE

    _install(monkeypatch, answer=REFUSAL_SENTENCE, citations=[])

    passed, detail = asyncio.run(run_eval._run_one(_case(["4"])))

    assert passed is False
    assert "refused, but a grounded answer was expected" in detail
