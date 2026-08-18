import re
from dataclasses import dataclass

from app.retrieval import fetch_article_text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_article_number(raw: str) -> str:
    """The model doesn't reliably follow "digits only" formatting instructions --
    it returns "Art. 4", "4º", "artigo 4" interchangeably. Extract the digits so the
    DB lookup (which stores bare numbers) isn't silently defeated by phrasing."""
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


@dataclass
class Citation:
    article_number: str
    quote: str
    verified: bool
    article_text: str | None


async def verify_citations(citations: list[dict]) -> list[Citation]:
    results = []
    for citation in citations:
        article_number = _normalize_article_number(citation.get("artigo", ""))
        quote = citation.get("trecho", "")

        article_text = await fetch_article_text(article_number)
        verified = bool(
            article_text and _normalize(quote) and _normalize(quote) in _normalize(article_text)
        )
        results.append(
            Citation(
                article_number=article_number,
                quote=quote,
                verified=verified,
                article_text=article_text,
            )
        )
    return results
