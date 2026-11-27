import re
from dataclasses import dataclass

from app.retrieval import fetch_article_text

MIN_QUOTE_WORDS = 4
"""Words a quote needs before its presence in the article means anything.

`verified` used to be `bool(_normalize(quote) and _normalize(quote) in
text)` — pure substring containment with no lower bound, so the quote "o" was
"verified" against Article 4. Every citation the UI shows with a green check
went through that test, and a one-character quote carries no claim at all.

Four words is deliberately low. The check is a containment test, not
entailment: it can only say "this wording appears in the cited article", and a
longer floor would start rejecting short legitimate fragments of the statute.
Raising it narrows the false-positive surface; it does not make the badge mean
more than it does.
"""

_WORD = re.compile(r"\w+", re.UNICODE)


def _word_count(text: str) -> int:
    return len(_WORD.findall(text))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_article_number(raw: str) -> str:
    r"""The bare article reference, keeping a lettered suffix.

The model doesn't reliably follow "digits only" formatting instructions -- it
returns "Art. 4", "4º", "artigo 4" interchangeably. Extract the digits so the DB
lookup (which stores bare numbers) isn't silently defeated by phrasing.

A lettered article must keep its letter. `re.search(r"\d+")` turned "Art. 54-A"
into "54", so a citation to 54-A was looked up against Article 54 and certified
against the wrong text — a cross-article false positive in the one check that is
supposed to be exact.
"""
    match = re.search(r"(\d+)\s*(?:[-–]\s*([A-Za-z]))?", raw)
    if not match:
        return raw
    number, letter = match.group(1), match.group(2)
    return f"{number}-{letter.upper()}" if letter else number


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
        normalized_quote = _normalize(quote)
        # A quote has to be a quote before its presence is evidence. Containment
        # alone accepts "o", "Art. 4" and ". ", all of which are substrings of
        # every article and none of which assert anything.
        verified = bool(
            article_text
            and normalized_quote
            and _word_count(normalized_quote) >= MIN_QUOTE_WORDS
            and normalized_quote in _normalize(article_text)
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
