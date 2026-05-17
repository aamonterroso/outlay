"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from outlay_api.config import get_settings
from outlay_api.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown hooks."""
    configure_logging()
    settings = get_settings()
    logger.info("api.startup", extra={"env": settings.app_env})
    yield
    logger.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Outlay API",
        version="0.1.0",
        description="AI-native billing infrastructure",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
