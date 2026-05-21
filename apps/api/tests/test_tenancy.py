"""Cross-tenant isolation contract for TenantRepository.

These tests are the runtime evidence that backs the `Any` cast inside
`outlay_api.repository.TenantRepository._scoped`: they confirm that
every read path is filtered by `tenant_id` against a real Postgres
engine, and that `add()` refuses to persist a row owned by a different
tenant.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from outlay_api.models.base import TenantScoped
from outlay_api.models.customer import Customer
from outlay_api.models.tenant import Tenant
from outlay_api.repository import TenantRepository


async def _make_tenant(session: AsyncSession, slug: str) -> Tenant:
    t = Tenant(slug=slug, name=slug.title())
    session.add(t)
    await session.flush()
    return t


async def _make_customer(
    session: AsyncSession,
    tenant: Tenant,
    name: str,
    email: str,
) -> Customer:
    c = Customer(tenant_id=tenant.id, name=name, email=email)
    session.add(c)
    await session.flush()
    return c


async def test_get_excludes_other_tenant(session: AsyncSession) -> None:
    """A repo for tenant A must return None for a row owned by tenant B."""
    tenant_a = await _make_tenant(session, "alpha")
    tenant_b = await _make_tenant(session, "beta")
    customer_b = await _make_customer(session, tenant_b, "B Co", "ops@b.example")

    repo: TenantRepository[Customer] = TenantRepository(session, tenant_a.id, Customer)
    assert await repo.get(customer_b.id) is None


async def test_list_only_returns_own_tenant(session: AsyncSession) -> None:
    tenant_a = await _make_tenant(session, "alpha")
    tenant_b = await _make_tenant(session, "beta")
    await _make_customer(session, tenant_a, "A1", "a1@a.example")
    await _make_customer(session, tenant_a, "A2", "a2@a.example")
    await _make_customer(session, tenant_b, "B1", "b1@b.example")

    repo: TenantRepository[Customer] = TenantRepository(session, tenant_a.id, Customer)
    rows = await repo.list()
    assert len(rows) == 2
    assert all(c.tenant_id == tenant_a.id for c in rows)


async def test_add_rejects_foreign_tenant(session: AsyncSession) -> None:
    tenant_a = await _make_tenant(session, "alpha")
    tenant_b = await _make_tenant(session, "beta")

    repo_a: TenantRepository[Customer] = TenantRepository(session, tenant_a.id, Customer)
    foreign = Customer(tenant_id=tenant_b.id, name="Foreign", email="f@b.example")
    with pytest.raises(ValueError, match="tenant mismatch"):
        await repo_a.add(foreign)

    # Confirm the row did NOT land in tenant B's view either.
    repo_b: TenantRepository[Customer] = TenantRepository(session, tenant_b.id, Customer)
    assert await repo_b.list() == []


async def test_get_returns_own_row(session: AsyncSession) -> None:
    tenant_a = await _make_tenant(session, "alpha")
    customer = await _make_customer(session, tenant_a, "A Co", "ops@a.example")

    repo: TenantRepository[Customer] = TenantRepository(session, tenant_a.id, Customer)
    found = await repo.get(customer.id)
    assert found is not None
    assert found.id == customer.id

    # Documents the runtime-checkable Protocol contract: a Customer
    # structurally satisfies TenantScoped at runtime.
    assert isinstance(customer, TenantScoped)
