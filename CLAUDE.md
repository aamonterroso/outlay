# CLAUDE.md

Persistent context for AI agents working on Outlay. Read this file fully before writing or editing code.

## Project

**Outlay**: AI-native billing infrastructure for modern B2B SaaS. Public portfolio demo.

The project demonstrates three production-shaped capabilities of a billing platform: contract ingestion with AI parsing, idempotent usage event ingestion, and an agentic assistant that queries billing data via tool use. Scope is intentionally narrow. Quality of execution and visible architectural reasoning are the goal, not feature count.

## Scope

Three features, not more.

1. **Contract upload with AI parsing**. PDF lands in object storage via presigned URL. Backend invokes Claude with tool use to extract structured line items. Result saved to Postgres with reference to the original file.
2. **Usage ingestion endpoint**. `POST /usage/ingest` accepts batch events with idempotency keys. Duplicates are absorbed silently via a UNIQUE database constraint.
3. **AI invoice assistant**. Agentic chat with read-only tool calling. Tools include get_invoice_by_id, list_overdue_invoices, get_customer_ar_aging, list_invoices_by_period.

Five Architecture Decision Records, in `docs/adr/`.

- ADR-001: Multi-tenancy via shared schema with tenant_id
- ADR-002: Idempotency via UNIQUE constraint vs Redis SETNX
- ADR-003: Agent tools, read-only scope and granularity
- ADR-004: Object storage with presigned URLs (R2 over S3)
- ADR-005: Rate limiting strategy (planned only, not implemented)

## Out of scope

These are documented non-goals. If an agent or contributor proposes adding them, decline and reference this section.

- Real authentication (JWT, OAuth, Auth0, Clerk). Auth is a stub via `X-Tenant-Id` header.
- Postgres RLS. Mentioned in ADR-001 as future hardening, not implemented.
- Dunning workflows or state machines.
- Revenue recognition (ASC 606).
- Webhook delivery with retries.
- Redis SETNX as first-line idempotency check.
- Implemented rate limiting (ADR-005 is "planned only").
- Datadog, OpenTelemetry, or any observability integration beyond JSON log format.
- Multi-currency.
- Stripe or any payment processor integration.

## Tech stack

Decided. Do not change without explicit human approval recorded in chat.

### Backend

- Python 3.11+. Do not target 3.14, Railway compatibility is uncertain.
- FastAPI for HTTP layer.
- SQLModel (Pydantic v2 + SQLAlchemy 2.x).
- **psycopg3** as the single async driver. Not asyncpg. Reasons: DBAPI 2.0 compatibility, libpq-standard SSL, better JSONB support, same driver for app and Alembic.
- Alembic for migrations.
- **Neon** managed Postgres as the primary database. Not local docker. Docker-compose may be documented as a fallback in README only, not in the default development workflow.
- Anthropic SDK with direct tool use (classic ReAct loop pattern). No MCP server.
- Cloudflare R2 via boto3 with custom `endpoint_url`.

### Frontend

- Next.js 15, App Router.
- TypeScript.
- Tailwind CSS.
- shadcn/ui.

### Deploy targets

- Frontend on Vercel.
- Backend on Railway.
- Database on Neon.
- Object storage on Cloudflare R2.

### Tooling

- uv for Python virtual environments and dependency management.
- ruff for lint and format.
- mypy in strict mode.
- pytest for tests.
- GitHub Actions running typecheck, lint, and test on every PR.
- Conventional commits from the first commit.

## Database connection strategy

Two URLs in `.env`:

- `DATABASE_URL`: pooled connection (Neon `-pooler` endpoint) used by the FastAPI app at runtime.
- `DATABASE_URL_DIRECT`: direct connection used by Alembic for migrations.

Reason: pgbouncer in transaction mode breaks some DDL statements that Alembic emits. The direct connection bypasses the pooler for migrations only. Runtime queries from the app continue to use the pooled URL.

Driver prefix: `postgresql+psycopg://`.

## Multi-tenancy approach

Shared schema with a `tenant_id UUID NOT NULL` column on every business table. Defense in depth:

1. Middleware extracts `X-Tenant-Id` from the request header, validates it as a UUID, and stores it on `request.state.tenant_id`. This is plumbing, not security.
2. A FastAPI dependency `get_current_tenant` forces every route to declare the tenant explicitly via `Depends`.
3. A base repository pattern injects `WHERE tenant_id = ?` into every query. This is the real defense against cross-tenant leakage.
4. Composite indexes always lead with `tenant_id`.
5. Postgres Row Level Security is documented in ADR-001 as future hardening. Not implemented in this demo.

## Idempotency approach

`usage_events.idempotency_key TEXT UNIQUE`. On duplicate insert, Postgres rejects with a constraint violation. The endpoint catches the violation and returns 200 with `duplicates: 1`. No Redis SETNX. Reasoning is in ADR-002: the UNIQUE constraint is durable across restarts, atomic by definition, and adds no operational dependencies.

## Object storage approach

PDFs live in R2, never in Postgres. The `contracts` table stores `r2_key TEXT` and `parsed_data JSONB`. Uploads use presigned PUT URLs with 15 minute expiry. Downloads use presigned GET URLs. The backend never proxies file bytes.

## Build phases

Each phase ends with: commit, push, verification step, then the next phase begins. Do not start a new phase without an explicit human checkpoint.

- **Phase 0**: repo init, monorepo structure, .gitignore, README placeholder, LICENSE, ADR index. **Done.**
- **Phase 1**: FastAPI scaffold, `/health` endpoint, JSON structured logging, Pydantic settings, ruff and mypy configured. **Done.**
- **Phase 2**: data layer. psycopg3 async engine, session dependency, SQLModel base, Alembic init, first migration creating `tenants` and `customers`. **Current.**
- **Phase 3**: tenancy middleware that extracts `X-Tenant-Id`, dependency injection for the current tenant, base repository pattern.
- **Phase 4**: R2 object storage configuration, presigned URL helpers, environment validation.
- **Phase 5**: Next.js 15 scaffolding, Tailwind, shadcn/ui base, typed fetch client to the API.
- **Phase 6**: early deploy. Vercel, Railway, and Neon wired in production with `/health` only. Proves the pipeline before any feature work.
- **Phase 7**: Feature 2 (usage ingestion). Backend-pure, validates the stack end to end.
- **Phase 8**: Feature 1 (contract upload and parsing). Integrates R2, Claude tool use, and the more complex frontend.
- **Phase 9**: Feature 3 (invoice assistant). Integrates everything prior.
- **Phase 10**: polish. README final with Mermaid architecture diagram, all ADRs reviewed, screenshots, deploy verification.

Triage rule: if Feature 3 fails to compile at code freeze, ship Features 1 and 2 with an honest ADR pointing at the `feat/assistant` branch. Two production-shaped features beat three broken ones.

## Branch and commit conventions

- Phases 0 through 6 (scaffold and early deploy): push directly to `main`. Conventional commits required.
- Phases 7 through 9 (feature work): each feature lives on `feat/<name>` branch with a pull request to `main`. Self-merge after CI is green. Short PR description, three to five lines.
- Phase 10 (polish): direct to `main`.

Commit prefixes used in this project: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. Scope optional: `feat(api):`, `feat(web):`.

## Working rules for AI agents

1. Read this file fully before any code change.
2. Do not advance a phase without an explicit human checkpoint. If a phase is marked Current, complete only that phase and stop.
3. Do not change tech stack decisions (driver, database target, framework choice) without explicit human approval recorded in chat.
4. Do not assume the database target. This project uses Neon. Local docker is fallback only and not the default development environment.
5. Do not introduce dependencies that are not listed in this file without justification accepted in chat.
6. When uncertain, stop and ask. A pause is cheaper than a revert.
7. Conventional commits only. Never `git commit -m "updates"` or similar non-conforming messages.
8. Run quality checks before claiming a phase done: `ruff check`, `ruff format --check`, `mypy outlay_api`, `pytest`. All must pass.
9. Never commit secrets. The file `apps/api/.env` is gitignored. Verify `git status` shows it untracked before any commit. Use `apps/api/.env.example` for shareable templates.

## ADR writing rules

ADRs live in `docs/adr/` and are part of the public signal of this repository. Format:
## ADR writing rules

ADRs live in `docs/adr/` and are part of the public signal of this repository. Format:
  
    # ADR-XXX: Title

    ## Status
    Accepted | Planned | Superseded

    ## Context
    Two to four sentences. Problem and constraints.

    ## Decision
    One to three sentences. What was decided.

    ## Alternatives considered
    Short list with reason for rejection.

    ## Trade-offs
    Honest gains and sacrifices. Not defensive.

    ## References (optional)
    External links.

Tone: human staff engineer writing an internal memo. No marketing language, no padding phrases like "in conclusion", "it's important to note", or "this approach allows us to". Avoid em-dashes when commas or parentheses work. Length 80 to 200 lines maximum per ADR.

## State at last update

- Phase 0 committed.
- Phase 1 committed. FastAPI service serves `/health` with JSON logging via `pythonjsonlogger.json.JsonFormatter`. Pydantic settings in place. ruff and mypy strict are clean.
- Neon project provisioned in us-east-1 on Postgres 17. Connection strings stored locally in `apps/api/.env` (gitignored).
- Phase 2 is the current target. No data layer code is committed yet.

## Detailed plan for Phase 2

1. Add `sqlmodel`, `sqlalchemy[asyncio]`, `psycopg[binary]>=3.2`, and `alembic` to the main dependencies in `apps/api/pyproject.toml`.
2. Update `outlay_api/config.py` to validate `database_url` and add `database_url_direct`.
3. Update `apps/api/.env.example` with both URL placeholders and explanatory comments.
4. Create `outlay_api/db.py` with the async engine, session factory, and a `get_db` dependency.
5. Create `outlay_api/models/__init__.py` and `outlay_api/models/tenants.py` with a SQLModel `Tenant`.
6. Create `outlay_api/models/customers.py` with a SQLModel `Customer` referencing `tenant_id`.
7. Initialize Alembic at `apps/api/alembic/` with the async template.
8. Configure `alembic/env.py` to read `DATABASE_URL_DIRECT` and import SQLModel metadata.
9. Generate the first revision containing both tables and their composite indexes.
10. Run `alembic upgrade head` against Neon.
11. Verify with a manual query that both tables exist.
12. Commit with a conventional message.

The `/health` endpoint stays simple. A readiness probe that pings the database will be added in Phase 6, when Railway healthchecks actually need it.

