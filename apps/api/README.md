# Outlay API

FastAPI service for the Outlay billing platform.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
cd apps/api
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uv run uvicorn outlay_api.main:app --reload
```

API runs at `http://localhost:8000`. OpenAPI docs at `/docs`.

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy outlay_api
uv run pytest
```
