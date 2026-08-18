.PHONY: install test lint eval ingest dev-backend dev-frontend

install:
	python3 -m venv .venv
	./.venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

test:
	./.venv/bin/pytest

lint:
	./.venv/bin/ruff check app ingest tests
	cd frontend && npm run lint

eval:
	./.venv/bin/python eval/run_eval.py

ingest:
	./.venv/bin/python ingest/fetch_law.py
	./.venv/bin/python ingest/embed_and_load.py

dev-backend:
	./.venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
