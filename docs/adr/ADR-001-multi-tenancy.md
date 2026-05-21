# ADR-001: Multi-tenancy via shared schema with tenant_id

## Status

Accepted.

## Context

Outlay is a multi-tenant B2B billing service. One Postgres database holds data for many customer organizations.

The hard requirement is that one tenant can never read or write another tenant's rows. There is no acceptable failure mode where this constraint is partially honored.

Authentication in this iteration is a deliberate stub. Clients send their tenant identity in an `X-Tenant-Id` header. There is no JWT, no OAuth, no identity provider in front of the API. Isolation therefore cannot lean on "the identity layer keeps tenants separate," because there is no identity layer to lean on.

The boundary has to be structural. It must be enforced by data shape and query construction, not by trust in who the caller claims to be.

The cost of getting this wrong is the worst kind of bug in a billing system. A single cross-tenant read of invoices, contracts, or usage events is a breach. A cross-tenant write is data corruption that may not be recoverable. The mechanism therefore has to be simple enough to reason about per query, and hard enough to bypass that we do not depend on every author remembering the rule.

## Decision

One Postgres database. Shared schema. Every business table carries `tenant_id UUID NOT NULL`.

The `tenants` table itself is the isolation root and is deliberately not tenant-scoped. By construction, the tenant-scoped repository cannot be instantiated for it; the type bound rejects models without a `tenant_id`.

Isolation is enforced in depth across three layers, each with a narrow responsibility.

### Layer 1: middleware

The middleware parses `X-Tenant-Id` and writes the parsed UUID (or `None` for absent or malformed) onto `request.state.tenant_id`.

It does not reject the request, does not log the tenant value at INFO, and does not maintain a list of public paths. It is plumbing, not security.

Rejection lives in the next layer. Pushing it down means we never need to maintain "which routes are public" inside the middleware, and we never need a path allowlist that drifts as routes are added.

### Layer 2: route-level dependency

A FastAPI dependency, `get_current_tenant`, is the gate. Routes that need a tenant declare `Depends(get_current_tenant)` and receive a `uuid.UUID`. Routes that do not depend on it stay public by definition; `/health` is a public route because it has no such dependency, not because it appears on a list anywhere.

A missing header, a malformed header, and a middleware misconfiguration all surface as a single 400 with one error message. The response does not let a caller distinguish those cases. There is nothing to probe.

### Layer 3: tenant-scoped repository

A base repository scopes every read to the current tenant. The repository is generic over a `TenantScoped` protocol bound, and exposes only methods that originate from a private `_scoped()` query already filtered by `tenant_id`. There is no public path inside the class that constructs a bare `select(Model)`.

Writes assert that the row's `tenant_id` matches the repository's tenant and refuse mismatches with a `ValueError`. They do not silently correct the row. A repository for tenant A must never persist a row for tenant B, even by accident, because silent correction hides the bug that produced the mismatch.

Composite indexes lead with `tenant_id`. Most queries are tenant-scoped by definition, so leading-column index alignment is the natural shape and pays for itself the first time the planner picks an index.

### The JOIN invariant

When a query touches more than one table, `tenant_id` filtering must be applied to **every** participating table.

Do not rely on foreign-key transitivity. Filtering `customers` by `tenant_id` and then joining `invoices` on `customer_id` is not equivalent to filtering both tables explicitly.

Foreign-key transitivity protects correct queries over correct data. It does not protect against a row that was inserted with a mismatched `tenant_id` by an application bug, a backfill, or a future migration. The isolation rule has to hold even when the data is wrong, because that is the case where the rule matters most.

The single-table repository enforces this today. The first cross-table business JOIN arrives with the invoice assistant (Feature 3), and a typed JOIN helper will be added at that point, carrying per-table `tenant_id` filters by construction.

The helper is deferred deliberately. Designing it now, without a real query to validate against, is how the wrong abstraction gets baked in. The rule is documented now and materialized in code when the use case exists.

## Alternatives considered

**Postgres Row Level Security as the primary mechanism.**

RLS would push enforcement into the database itself, surviving an entire class of application bugs that bypass the repository.

The cost is operational. The pooler in front of the app runs in transaction mode, and setting a per-request `app.tenant_id` GUC through a pooler is delicate. Connection reuse can leave a query running against a connection whose session state belongs to a previous request unless the GUC is reset on every checkout, and getting that wrong fails closed only if the policy is carefully written.

This system also has no compliance driver that justifies paying that complexity now.

RLS is recorded as future hardening, not rejected on the merits. It is the right answer when the conditions change, not the right answer today.

**Schema-per-tenant.**

One Postgres schema per tenant gives physical isolation inside a single database. The operational cost scales with tenant count. Migrations fan out across schemas, observability has to aggregate across them, and the model fits products with a small number of large tenants better than products with many small ones.

Outlay's expected shape is many small tenants, not few large ones.

**Database-per-tenant.**

The strongest isolation available, appropriate when individual tenants are large or carry data-residency requirements that forbid co-tenancy. Disproportionate for this product.

The blast radius from a bug in the app layer is smaller. The steady-state cost of provisioning, migrating, monitoring, and backing up N databases is much larger, and there is no business requirement here that the model is paying for.

## Trade-offs

What this choice buys: one schema, one migration path, one connection pool, one set of indexes to reason about. The code stays portable; nothing about this design is Neon-specific or Postgres-extension-specific. A new contributor can hold the whole isolation story in their head after reading this ADR and one repository file.

What this choice costs: the app-layer guarantee is only as strong as the discipline that every query goes through the repository.

A raw SQL string in a route handler, a bare `select(Model)` in a script, a quick `psql` session that forgets the filter, any of these is a leak. Convention is doing real work here, and conventions degrade as teams grow. RLS would be the safety net under that human error. We have chosen not to add it yet because the conditions that make it worth its operational weight do not exist in this system today.

State it plainly: when regulated data enters the system, or when the team is large enough that "every query goes through the repository" can no longer be enforced by code review, RLS stops being optional.

The migration path is intentionally short. RLS policies key on `tenant_id`, which already exists on every business table and is already `NOT NULL` at the schema level. Adopting RLS later is additive, not a redesign.

The cross-tenant isolation invariant is covered by an integration test that runs against a real Postgres engine, not a mock or an in-memory substitute. The repository's tenant-filter behavior is exercised at runtime, not just asserted by code review. That test is what makes "every read goes through `_scoped()`" a verifiable claim instead of a comment in a header.

## References

- ADR-002: Idempotency via UNIQUE constraint (pending). Related defense-in-depth pattern at the write boundary.
