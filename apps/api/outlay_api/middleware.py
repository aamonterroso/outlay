"""HTTP middleware.

`TenantContextMiddleware` parses the `X-Tenant-Id` header and stashes the
result on `request.state.tenant_id` as `uuid.UUID | None`. It does not
reject requests; enforcement is the job of the `get_current_tenant`
dependency, so public routes (e.g. `/health`) opt out by not depending on
it and we avoid maintaining a path allowlist here.
"""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resolve X-Tenant-Id into `request.state.tenant_id`."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        raw = request.headers.get("X-Tenant-Id")
        tenant_id: uuid.UUID | None = None
        if raw is not None:
            try:
                tenant_id = uuid.UUID(raw)
            except ValueError:
                tenant_id = None
        request.state.tenant_id = tenant_id
        logger.debug(
            "tenancy.context",
            extra={"tenant_resolved": tenant_id is not None},
        )
        return await call_next(request)
