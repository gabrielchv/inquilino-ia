"""Fetch Lei 8.245/1991 from planalto.gov.br and chunk it into per-article JSON.

planalto keeps every historical amendment inline as redlined text: an old wording
struck through, sometimes several amendment layers deep, followed by the current
wording. The `<strike>` tag marks some of it; later amendments use CSS
`text-decoration:line-through` on a `<span>` instead. Both must be stripped before
extracting text, or a chunk ends up holding revoked wording as if it were current
law -- a citation-accuracy project cannot ship that mistake.
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.planalto.gov.br/ccivil_03/leis/l8245.htm"
OUTPUT_PATH = Path(__file__).parent / "lei_8245_chunks.json"

ARTICLE_HEADER = re.compile(
    r"(?:^|\n)\s*Art\.?\s*(\d+)\s*[ºo]?\s*(?:[-–]\s*([A-Za-z]))?"
)
r"""Matches `Art. 1º` and lettered articles such as `Art. 54-A`.

The previous pattern ended in `\s*[\.\-]?\s`, which required whitespace after
an optional dot or hyphen. `Art. 54-A` has a letter there, so no header matched:
the whole of 54-A was absorbed into the Article 54 chunk, no chunk keyed `54-A`
existed, and a citation to 54-A was silently certified against Article 54.

The letter is only accepted after a hyphen. A bare `\s*([A-Za-z])?` would read
the first letter of the following word as an article suffix — `Art. 4 Durante`
would become article `4-D`.
"""
CHAPTER_HEADING = re.compile(
    r"(?:^|\n)\s*(TÍTULO [IVXLC]+|CAPÍTULO [IVXLC]+|SEÇÃO [IVXLC]+)\s*\n\s*(.+)"
)
END_OF_LAW_MARKER = re.compile(r"\nBrasília,")


def fetch_html() -> str:
    resp = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"},
        timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = "latin-1"
    return resp.text


def strip_superseded_wording(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["strike", "s", "del"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"line-through")):
        tag.decompose()
    for sup in soup.find_all("sup"):
        sup.replace_with("º")


def join_broken_hyphens(text: str) -> str:
    """Reattach a hyphen that planalto splits from the word it belongs to.

    The statute writes `transmite-se` as `transmite<b>-</b>se`. `get_text` with
    `separator="\n"` puts a newline between *every* text node, so the hyphen
    arrives isolated on its own line: `transmite\n-\nse`. Collapsing whitespace
    then gives `transmite - se`, which is not the law — it fails to verify a model
    quoting the real spelling, and ships corrupted text to the UI as the
    authoritative article.

    The pattern is deliberately narrow: a hyphen alone on its line, with a word
    character on each side *across a newline*. A genuine spaced dash inside a
    paragraph is a single text node, so it never produces this shape — `Art. 1º -
    Texto` comes through as one string and is left alone.
    """
    return re.sub(r"(?<=\w)\s*\n\s*-\s*\n\s*(?=\w)", "-", text)


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    strip_superseded_wording(soup)
    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return join_broken_hyphens(text)


def chapter_at(text: str, position: int) -> str | None:
    heading = None
    for match in CHAPTER_HEADING.finditer(text, 0, position):
        heading = f"{match.group(1)} — {match.group(2).strip()}"
    return heading


def article_id(match: re.Match[str]) -> str:
    """The id a header match contributes: `4`, or `54-A` when lettered."""
    number, letter = match.group(1), match.group(2)
    return f"{number}-{letter.upper()}" if letter else number


def chunk_articles(text: str) -> list[dict]:
    headers = list(ARTICLE_HEADER.finditer(text))
    if not headers:
        raise RuntimeError("no article headers found -- source page structure changed")

    chunks = []
    for i, header in enumerate(headers):
        start = header.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[start:end].strip()

        end_marker = END_OF_LAW_MARKER.search(body)
        if end_marker:
            body = body[: end_marker.start()].strip()

        body = re.sub(r"\s+", " ", body)
        chunks.append(
            {
                "article_number": article_id(header),
                "chapter": chapter_at(text, start),
                "text": body,
            }
        )

    numbers = [c["article_number"] for c in chunks]
    if len(numbers) != len(set(numbers)):
        raise RuntimeError(f"duplicate article numbers after parsing: {numbers}")

    return chunks


def main() -> None:
    print(f"fetching {SOURCE_URL}", file=sys.stderr)
    html = fetch_html()
    text = extract_text(html)
    chunks = chunk_articles(text)
    print(f"parsed {len(chunks)} articles", file=sys.stderr)

    OUTPUT_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
