"""Tenant-context helpers consumed by routes and the repository layer.

`get_current_tenant` is the enforcement point: routes that depend on it
require a valid tenant. Public routes (e.g. `/health`) simply do not
depend on it, which avoids maintaining a path allowlist anywhere.

The middleware (`outlay_api.middleware.TenantContextMiddleware`) resolves
`X-Tenant-Id` onto `request.state.tenant_id` as `uuid.UUID | None`. This
module turns the `None` case into a 400.
"""

import uuid

from fastapi import HTTPException, Request, status


def get_current_tenant(request: Request) -> uuid.UUID:
    """Return the tenant for the current request or raise 400.

    Reads `request.state.tenant_id` defensively via `getattr` so a
    missing middleware registration surfaces as the same 400 a client
    sees for a missing/malformed header, not an AttributeError 500.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if isinstance(tenant_id, uuid.UUID):
        return tenant_id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing or invalid X-Tenant-Id header",
    )
