"""Database models. Importing this module registers all tables with SQLModel.metadata."""

from outlay_api.models.customer import Customer
from outlay_api.models.tenant import Tenant

__all__ = ["Customer", "Tenant"]
