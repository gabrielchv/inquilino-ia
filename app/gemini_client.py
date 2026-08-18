from collections.abc import AsyncIterator
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import get_settings


@lru_cache
def get_client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


async def embed(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    settings = get_settings()
    client = get_client()
    response = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimensions,
            task_type=task_type,
        ),
    )
    return response.embeddings[0].values


async def generate_stream(
    system_prompt: str, user_prompt: str
) -> AsyncIterator[str]:
    settings = get_settings()
    client = get_client()
    stream = await client.aio.models.generate_content_stream(
        model=settings.generation_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text


async def generate_json(system_prompt: str, user_prompt: str, schema: dict) -> dict:
    settings = get_settings()
    client = get_client()
    response = await client.aio.models.generate_content(
        model=settings.generation_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return response.parsed if response.parsed is not None else {}
