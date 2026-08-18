# InquilinoIA

A citation-grounded RAG assistant that answers Brazilian tenancy-law questions
against the full text of **Lei do Inquilinato (Lei 8.245/1991)**. Every claim in an
answer must be backed by a verbatim quote from the actual article -- checked in code
before it's shown, not taken on the model's word.

Ask something like *"posso sair do contrato antes do prazo?"* and get an answer with
per-claim citations you can click to read the source article, or an explicit refusal
if the law provided doesn't answer the question -- never a plausible-sounding guess.

## Why this exists

A portfolio project built to demonstrate RAG engineering, not just prompt a model
over a PDF: the interesting part is the verification pipeline, not the chat UI.

## Architecture

```
                       ┌─────────────────────────────┐
   Browser  ───────►   │   Cloud Run (single service) │
   (Vue 3 SPA)         │   FastAPI serves:            │
                       │   - static Vue build          │
                       │   - /api/chat (SSE)           │
                       │   - /api/health                │
                       └──────────┬────────────────────┘
                                  │
                    ┌─────────────┼──────────────┐
                    ▼                            ▼
           Supabase Postgres              Gemini API
           + pgvector                     (embeddings + generation,
           (law_chunks table)              streaming)
```

**Two Gemini calls per question, by design.** The first streams a plain-language
answer for a responsive UI. The second (non-streaming, structured JSON output) asks
the model to extract `{article, verbatim_quote}` pairs backing that answer. Each quote
is then checked in Python against the actual stored article text -- a normalized
substring match, not a second LLM call and not trust in the model's citation. This
avoids the fragile alternative of parsing citation tags out of a live token stream,
where a tag split across two chunks would corrupt the parse.

Streaming shows the answer before verification finishes, so verification can only
*annotate* (citation badges: verified/unverified, or a banner if nothing verified),
never *suppress* -- unlike a form-fill where a bad value can be dropped before it's
ever written. See `app/chat.py` for the full flow.

## Stack

- **Frontend**: Vue 3 + Vite (Composition API, no meta-framework), Tailwind CSS
- **Backend**: FastAPI (Python), single Cloud Run service serving the built frontend
- **Vector store**: Supabase (Postgres + pgvector), free tier
- **LLM**: Gemini only, both embeddings (`gemini-embedding-001`, truncated to 768
  dimensions) and generation (`gemini-2.5-flash`)
- **IaC**: Terraform (GCP resources only -- see `infra/README.md`)
- **CI/CD**: GitHub Actions, deploys on merge to `main` via Workload Identity
  Federation (no long-lived service account keys)

## Data pipeline

`ingest/fetch_law.py` scrapes the law from planalto.gov.br and chunks it per article.
The tricky part: planalto keeps every historical amendment inline as redlined text --
some struck through with a `<strike>` tag, some via CSS
`text-decoration:line-through` instead -- and naively splitting on "Art. N" headers
would capture revoked wording as if it were current law. The parser strips both
strikethrough forms before extracting text. See the module docstring and
`tests/test_fetch_law.py` for the specific case (Article 4 has three historical
versions layered this way) that would otherwise silently ship wrong law.

Output is committed as `ingest/lei_8245_chunks.json` -- a versioned, reproducible seed
so re-running the pipeline doesn't require re-scraping. `ingest/embed_and_load.py`
embeds each chunk and upserts it into Supabase.

## Running locally

```bash
make install
cp .env.example .env   # fill in GEMINI_API_KEY and SUPABASE_DB_URL
```

Provision Supabase manually: create a project, run `infra/schema.sql` in its SQL
editor (enables pgvector, creates `law_chunks`). Then:

```bash
make ingest        # fetch + chunk + embed + load, ~90 articles
make dev-backend   # uvicorn on :8000
make dev-frontend  # vite dev server on :5173, proxies /api to :8000
```

## Testing & eval

```bash
make test   # pytest -- chunking parser, citation verification, API contract
make eval   # eval/questions.yaml against the live pipeline, costs real Gemini calls
```

Frontend testing is deliberately out of scope for v1, to protect backend/citation
quality within the project's time budget.

## Deploying

See `infra/README.md` for the one-time bootstrap (GCS state bucket, Workload Identity
Federation for GitHub Actions). After that, `git push` to `main` builds, pushes, and
`terraform apply`s automatically.
