"""Pytest fixtures backing the tenancy integration tests.

Tests run against an ephemeral Postgres 17 container (matching Neon's
managed version) via testcontainers. The schema is created with
`SQLModel.metadata.create_all`, not Alembic: Alembic correctness is
exercised every time we run migrations against Neon, and `create_all`
is faster and equivalent for the slice this suite cares about — repository
behavior against a real Postgres engine, not migration logic.

Fixture and test loops both run on the session-scoped event loop
(see `asyncio_default_*_loop_scope` in pyproject.toml) so the
session-scoped engine's connections remain valid across function-scoped
session fixtures and tests.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

# Importing the models package registers Tenant and Customer with
# SQLModel.metadata so create_all knows about them.
from outlay_api import models  # noqa: F401


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    # testcontainers returns a sync URL (psycopg2). Rewrite to the
    # psycopg3 async driver the app uses everywhere else.
    raw_url = postgres_container.get_connection_url()
    _, rest = raw_url.split("://", 1)
    url = f"postgresql+psycopg://{rest}"

    eng = create_async_engine(url, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    # Truncate between tests so cases don't leak. CASCADE handles the
    # customers -> tenants FK ordering for us.
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE customers, tenants RESTART IDENTITY CASCADE"))
