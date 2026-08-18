from dataclasses import dataclass

from app.config import get_settings
from app.db import get_pool
from app.gemini_client import embed


@dataclass
class RetrievedChunk:
    article_number: str
    chapter: str | None
    text: str


async def retrieve(question: str) -> list[RetrievedChunk]:
    settings = get_settings()
    query_vector = await embed(question, task_type="RETRIEVAL_QUERY")

    pool = await get_pool()
    rows = await pool.fetch(
        """
        select article_number, chapter, text
        from law_chunks
        order by embedding <=> $1
        limit $2
        """,
        query_vector,
        settings.retrieval_top_k,
    )
    return [
        RetrievedChunk(
            article_number=row["article_number"],
            chapter=row["chapter"],
            text=row["text"],
        )
        for row in rows
    ]


async def fetch_article_text(article_number: str) -> str | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "select text from law_chunks where article_number = $1", article_number
    )
    return row["text"] if row else None
