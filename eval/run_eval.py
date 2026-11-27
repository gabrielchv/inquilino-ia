"""Runs eval/questions.yaml against the live chat pipeline and reports a pass rate.

Costs real Gemini calls -- not run in CI. `make eval` or `python eval/run_eval.py`.
"""

import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chat import (
    ANSWER_SYSTEM_PROMPT,
    CITATION_SYSTEM_PROMPT,
    CITATIONS_SCHEMA,
    _articles_block,
    is_refusal,
)
from app.gemini_client import generate_json
from app.retrieval import retrieve
from app.verify import _normalize_article_number, verify_citations

QUESTIONS_PATH = Path(__file__).parent / "questions.yaml"


async def _run_one(case: dict) -> tuple[bool, str]:
    question = case["question"]
    expected = {_normalize_article_number(a) for a in case["expected_articles"]}

    chunks = await retrieve(question)
    articles_block = _articles_block(chunks)

    answer_parts = []
    from app.gemini_client import generate_stream

    async for delta in generate_stream(
        ANSWER_SYSTEM_PROMPT.format(articles_block=articles_block), question
    ):
        answer_parts.append(delta)
    answer = "".join(answer_parts).strip()

    if not expected:
        passed = is_refusal(answer)
        detail = "refused correctly" if passed else f"expected refusal, got: {answer[:80]}"
        return passed, detail

    if is_refusal(answer):
        return False, "refused, but a grounded answer was expected"

    extraction = await generate_json(
        CITATION_SYSTEM_PROMPT,
        f"Pergunta: {question}\n\nResposta: {answer}\n\nArtigos:\n{articles_block}",
        CITATIONS_SCHEMA,
    )
    raw_citations = extraction.get("citacoes", [])

    # Normalize before comparing sets. A model that writes "Art. 4º" is citing
    # article 4, and the old comparison against a bare "4" scored that correct
    # citation as a miss.
    cited = {_normalize_article_number(c.get("artigo", "")) for c in raw_citations}

    # The product's claim is that a citation's quote is checked against the
    # statute. This function scored only whether the article number appeared in
    # the expected set, and never called `verify_citations` -- so a response could
    # cite the right article with a completely invented quote and score a clean
    # pass. The eval then could not detect a regression in the one property the
    # project sells.
    verified = await verify_citations(raw_citations)
    unverified = [c for c in verified if not c.verified]

    hits = cited & expected
    if not hits:
        return False, f"expected {sorted(expected)}, got {sorted(cited)}"
    if unverified:
        return False, (
            f"{len(unverified)} of {len(verified)} citation(s) failed verification: "
            + "; ".join(f"art. {c.article_number} quote {c.quote[:40]!r}" for c in unverified)
        )
    return True, f"expected {sorted(expected)}, got {sorted(cited)}, all quotes verified"


async def main() -> None:
    cases = yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        passed, detail = await _run_one(case)
        results.append(passed)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case['question']} -- {detail}")

    total = len(results)
    passed_count = sum(results)
    print(f"\n{passed_count}/{total} passed ({passed_count / total:.0%})")


if __name__ == "__main__":
    asyncio.run(main())
