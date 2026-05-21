"""Tenant-scoped repository base.

`TenantRepository[ModelT]` keeps every query bound to a single tenant.
This is the third defense layer in the multi-tenancy story (see ADR-001):
middleware extracts the tenant, `get_current_tenant` gates routes, and
this class keeps reads and writes pinned to that tenant.

Design rule: every public read is built from `_scoped()`, which already
applies `WHERE tenant_id = ?`. No public method constructs a bare
`select(model)` without the filter. New methods MUST start from
`_scoped()`.
"""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from outlay_api.models.base import TenantScoped

ModelT = TypeVar("ModelT", bound=TenantScoped)


class TenantRepository(Generic[ModelT]):
    """Single-tenant, single-table read and insert helper.

    Bind one instance per `(tenant, model)` pair. Cross-table joins are
    intentionally not supported here yet — Feature 3 introduces the
    first real join and will own that addition.
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model: type[ModelT],
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.model = model

    def _scoped(self) -> SelectOfScalar[ModelT]:
        # At the class level, SQLAlchemy exposes InstrumentedAttribute
        # descriptors whose __eq__ produces SQL expressions. The TenantScoped
        # Protocol describes the instance contract (uuid.UUID), so mypy
        # doesn't see those descriptors. Cast at this single boundary
        # rather than plumbing SQLAlchemy column types through the protocol.
        cls: Any = self.model
        return select(self.model).where(cls.tenant_id == self.tenant_id)

    async def get(self, id: uuid.UUID) -> ModelT | None:
        cls: Any = self.model
        stmt = self._scoped().where(cls.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = self._scoped().limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, instance: ModelT) -> ModelT:
        if instance.tenant_id != self.tenant_id:
            raise ValueError(
                "TenantRepository tenant mismatch: refusing to write a row "
                "owned by a different tenant"
            )
        self.session.add(instance)
        await self.session.flush()
        return instance
