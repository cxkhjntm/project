"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory, init_db, migrate_compat_schema
from app.middleware.error_handler import ErrorHandlerMiddleware, http_exception_handler
from app.models import *  # noqa: F401, F403 - ensure all models registered with Base
from app.routers import (
    artifacts,
    discussion,
    filesystem,
    providers,
    role_cards,
    rooms,
    settings as settings_router,
    sources,
)
from app.seed.loader import load_builtin_roles
from app.services.model_client import close_global_client
from app.utils.logger import get_logger, setup_logging

setup_logging(debug=settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Expert Room API", version="0.1.0", debug=settings.debug)
    await init_db()
    await migrate_compat_schema()

    async with async_session_factory() as session:
        await load_builtin_roles(session)
        await session.commit()

    yield

    logger.info("Shutting down Expert Room API")
    await close_global_client()


def create_app(lifespan_fn: AsyncIterator[None] | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if lifespan_fn is None:
        lifespan_fn = lifespan

    app = FastAPI(
        title="Expert Room API",
        description="AI Expert Team Collaboration Workbench",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan_fn,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(ErrorHandlerMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)

    app.include_router(providers.router)
    app.include_router(role_cards.router)
    app.include_router(rooms.router)
    app.include_router(sources.router)
    app.include_router(discussion.router)
    app.include_router(artifacts.router)
    app.include_router(filesystem.router)
    app.include_router(settings_router.router)

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
