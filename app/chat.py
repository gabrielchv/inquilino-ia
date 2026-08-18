import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.gemini_client import generate_json, generate_stream
from app.retrieval import retrieve
from app.verify import verify_citations

router = APIRouter()

REFUSAL_SENTENCE = (
    "Não encontrei fundamento na Lei do Inquilinato para responder a essa pergunta."
)

ANSWER_SYSTEM_PROMPT = f"""\
Você é um assistente que responde exclusivamente com base nos artigos da Lei do \
Inquilinato (Lei 8.245/1991) fornecidos abaixo. Nunca use conhecimento próprio sobre \
a lei além do texto fornecido.

Se os artigos fornecidos não contiverem fundamento para responder à pergunta, \
responda exatamente com esta frase, sem adicionar mais nada:
"{REFUSAL_SENTENCE}"

Caso contrário, responda em português claro e direto, em texto corrido, sem citar \
números de artigo em nenhum ponto da resposta e sem nenhum rodapé, separador ou lista \
de referências ao final -- as citações serão anexadas separadamente pela interface.

Artigos fornecidos:
{{articles_block}}
"""

CITATION_SYSTEM_PROMPT = """\
Dada uma pergunta, os artigos fornecidos e uma resposta já gerada, extraia as \
citações que fundamentam a resposta.

Para cada afirmação factual da resposta, retorne o número do artigo (APENAS o número, \
sem "Art." ou "º", ex: "4" e não "Art. 4º") e um trecho VERBATIM -- copiado exatamente, \
palavra por palavra, sem parafrasear -- do texto do artigo fornecido que sustenta essa \
afirmação.

Se a resposta for a recusa padrão ("Não encontrei fundamento..."), retorne uma lista \
vazia em "citacoes".
"""

CITATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "citacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "artigo": {"type": "string"},
                    "trecho": {"type": "string"},
                },
                "required": ["artigo", "trecho"],
            },
        }
    },
    "required": ["citacoes"],
}


class ChatRequest(BaseModel):
    question: str


def _articles_block(chunks) -> str:
    return "\n\n".join(
        f"Art. {c.article_number} ({c.chapter or 'sem seção'}):\n{c.text}" for c in chunks
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _chat_stream(question: str):
    chunks = await retrieve(question)
    articles_block = _articles_block(chunks)

    answer_parts = []
    async for delta in generate_stream(
        ANSWER_SYSTEM_PROMPT.format(articles_block=articles_block), question
    ):
        answer_parts.append(delta)
        yield _sse("delta", {"text": delta})

    answer = "".join(answer_parts).strip()
    refused = answer == REFUSAL_SENTENCE

    citations = []
    if not refused:
        extraction = await generate_json(
            CITATION_SYSTEM_PROMPT,
            f"Pergunta: {question}\n\nResposta: {answer}\n\nArtigos:\n{articles_block}",
            CITATIONS_SCHEMA,
        )
        raw_citations = extraction.get("citacoes", [])
        verified = await verify_citations(raw_citations)
        citations = [
            {
                "artigo": c.article_number,
                "trecho": c.quote,
                "verified": c.verified,
                "texto_artigo": c.article_text,
            }
            for c in verified
        ]

    yield _sse("done", {"citations": citations, "refused": refused})


@router.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(_chat_stream(request.question), media_type="text/event-stream")
