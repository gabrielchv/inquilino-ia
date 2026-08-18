"""Runs eval/questions.yaml against the live chat pipeline and reports a pass rate.

Costs real Gemini calls -- not run in CI. `make eval` or `python eval/run_eval.py`.
"""

import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chat import ANSWER_SYSTEM_PROMPT, CITATIONS_SCHEMA, CITATION_SYSTEM_PROMPT  # noqa: E402
from app.chat import REFUSAL_SENTENCE, _articles_block  # noqa: E402
from app.gemini_client import generate_json  # noqa: E402
from app.retrieval import retrieve  # noqa: E402

QUESTIONS_PATH = Path(__file__).parent / "questions.yaml"


async def _run_one(case: dict) -> tuple[bool, str]:
    question = case["question"]
    expected = set(case["expected_articles"])

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
        passed = answer == REFUSAL_SENTENCE
        detail = "refused correctly" if passed else f"expected refusal, got: {answer[:80]}"
        return passed, detail

    if answer == REFUSAL_SENTENCE:
        return False, "refused, but a grounded answer was expected"

    extraction = await generate_json(
        CITATION_SYSTEM_PROMPT,
        f"Pergunta: {question}\n\nResposta: {answer}\n\nArtigos:\n{articles_block}",
        CITATIONS_SCHEMA,
    )
    cited = {c["artigo"] for c in extraction.get("citacoes", [])}
    passed = bool(cited & expected)
    detail = f"expected {expected}, got {cited}"
    return passed, detail


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
