"""Typing primitives for tenant-scoped models.

`TenantScoped` marks a model as owned by a tenant. It is the generic bound
for `TenantRepository`, which injects `WHERE tenant_id = ?` into every query.
This is a structural Protocol, not a SQLModel base class: models conform by
declaring a `tenant_id: uuid.UUID` attribute, no inheritance required.
"""

import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class TenantScoped(Protocol):
    """Structural marker for models owned by a tenant."""

    tenant_id: uuid.UUID
