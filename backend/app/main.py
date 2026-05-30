"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory
from app.routers import providers, role_cards, rooms
from app.seed.loader import load_builtin_roles
from app.utils.logger import get_logger, setup_logging

setup_logging(debug=settings.debug)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Expert Room API",
        description="AI Expert Team Collaboration Workbench",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend
    # TODO: Tighten allow_methods and allow_headers before production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(providers.router)
    app.include_router(role_cards.router)
    app.include_router(rooms.router)

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting Expert Room API", version="0.1.0", debug=settings.debug)

        async with async_session_factory() as session:
            await load_builtin_roles(session)
            await session.commit()

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down Expert Room API")

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
