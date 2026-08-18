"""Embed each law chunk with Gemini and upsert it into Supabase's law_chunks table.

Safe to re-run: upserts on article_number, so a corrected fetch_law.py output can be
reloaded without duplicating rows.
"""

import asyncio
import json
import sys
from pathlib import Path

import asyncpg
from pgvector.asyncpg import register_vector

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.gemini_client import embed

CHUNKS_PATH = Path(__file__).parent / "lei_8245_chunks.json"


async def main() -> None:
    settings = get_settings()
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    conn = await asyncpg.connect(settings.supabase_db_url)
    await register_vector(conn)

    try:
        for i, chunk in enumerate(chunks, 1):
            vector = await embed(chunk["text"], task_type="RETRIEVAL_DOCUMENT")
            await conn.execute(
                """
                insert into law_chunks (article_number, chapter, text, embedding)
                values ($1, $2, $3, $4)
                on conflict (article_number) do update
                set chapter = excluded.chapter,
                    text = excluded.text,
                    embedding = excluded.embedding
                """,
                chunk["article_number"],
                chunk["chapter"],
                chunk["text"],
                vector,
            )
            print(f"[{i}/{len(chunks)}] loaded Art. {chunk['article_number']}", file=sys.stderr)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
