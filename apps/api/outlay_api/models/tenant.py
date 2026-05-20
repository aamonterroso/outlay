"""Tenant model. Top-level isolation boundary."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel


class Tenant(SQLModel, table=True):
    """An organization using Outlay. Root of multi-tenant isolation."""

    __tablename__ = "tenants"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    slug: str = Field(
        sa_column=Column(String(64), unique=True, nullable=False, index=True),
    )
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
