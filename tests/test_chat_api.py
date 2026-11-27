import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import chat as chat_module
from app.chat import REFUSAL_SENTENCE
from app.chat import router as chat_router
from app.retrieval import RetrievedChunk


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router)
    return app


@pytest.fixture
def client(monkeypatch):
    async def fake_retrieve(question):
        return [RetrievedChunk(article_number="4", chapter="SEÇÃO I", text="texto do artigo 4")]

    async def fake_generate_stream(system_prompt, user_prompt):
        for token in ["Você ", "pode ", "sim."]:
            yield token

    async def fake_generate_json(system_prompt, user_prompt, schema):
        return {"citacoes": [{"artigo": "4", "trecho": "texto do artigo"}]}

    monkeypatch.setattr(chat_module, "retrieve", fake_retrieve)
    monkeypatch.setattr(chat_module, "generate_stream", fake_generate_stream)
    monkeypatch.setattr(chat_module, "generate_json", fake_generate_json)

    async def fake_verify_citations(citations):
        from app.verify import Citation

        return [
            Citation(article_number=c["artigo"], quote=c["trecho"], verified=True, article_text="x")
            for c in citations
        ]

    monkeypatch.setattr(chat_module, "verify_citations", fake_verify_citations)

    app = build_test_app()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_chat_streams_deltas_then_verified_citations(client):
    async with (
        client as c,
        c.stream("POST", "/api/chat", json={"question": "posso sair do contrato?"}) as resp,
    ):
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk

    assert "Você " in body
    assert "pode " in body
    assert '"verified": true' in body
    assert '"refused": false' in body


async def test_chat_refuses_out_of_scope_question(client, monkeypatch):
    async def fake_generate_stream(system_prompt, user_prompt):
        yield REFUSAL_SENTENCE

    monkeypatch.setattr(chat_module, "generate_stream", fake_generate_stream)

    async with (
        client as c,
        c.stream("POST", "/api/chat", json={"question": "qual a capital do Brasil?"}) as resp,
    ):
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk

    assert '"refused": true' in body
    assert '"citations": []' in body


# --- a refusal is how the answer opens, not the whole of it -----------------


async def test_a_dressed_up_refusal_is_still_a_refusal(client, monkeypatch):
    """The model usually adds a polite sentence after refusing.

    Exact equality read that as a grounded answer: the UI showed a non-refusal and
    the route made a third Gemini call to extract citations from text that cited
    nothing.
    """

    async def fake_generate_stream(system_prompt, user_prompt):
        yield REFUSAL_SENTENCE
        yield " Se tiver outra dúvida, é só perguntar."

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("citation extraction must not run on a refusal")

    monkeypatch.setattr(chat_module, "generate_stream", fake_generate_stream)
    monkeypatch.setattr(chat_module, "generate_json", fail_if_called)

    async with (
        client as c,
        c.stream("POST", "/api/chat", json={"question": "qual a capital do Brasil?"}) as resp,
    ):
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk

    assert '"refused": true' in body
    assert '"citations": []' in body


async def test_a_grounded_answer_is_not_read_as_a_refusal(client):
    async with (
        client as c,
        c.stream("POST", "/api/chat", json={"question": "Posso sair antes do prazo?"}) as resp,
    ):
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk

    assert '"refused": false' in body
