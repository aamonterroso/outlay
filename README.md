# Outlay

AI-native billing infrastructure for modern B2B SaaS. Demo project.

## Status

Work in progress. Active build May 2026.

## Stack

- **Backend:** FastAPI, SQLModel, Alembic, Postgres (Neon)
- **Frontend:** Next.js 15, TypeScript, Tailwind, shadcn/ui
- **AI:** Anthropic SDK with tool use
- **Storage:** Cloudflare R2 (presigned URLs)
- **Deploy:** Vercel (web) + Railway (api) + Neon (db) + R2 (storage)

## Structure

```
outlay/
├── apps/
│   ├── web/        # Next.js 15
│   └── api/        # FastAPI
├── docs/
│   └── adr/        # Architecture Decision Records
└── README.md
```

## Scope

Three features, production-shaped:

1. Contract upload with AI parsing (PDF to structured line items)
2. Usage ingestion with idempotency
3. AI invoice assistant with tool calling

See `docs/adr/` for architectural decisions and trade-offs.

## License

MIT
