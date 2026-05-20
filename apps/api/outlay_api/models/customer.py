"""Customer model. Belongs to a tenant."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    """A customer belonging to a tenant. Recipient of invoices."""

    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_tenant_id_id", "tenant_id", "id"),)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
    )
    email: str = Field(
        sa_column=Column(String(320), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
