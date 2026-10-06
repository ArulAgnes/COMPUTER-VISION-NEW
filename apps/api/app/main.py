"""FastAPI application factory.

Run from the repository root:

    uvicorn app.main:app --reload --app-dir apps/api
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import config as config_routes
from app.api.routes import health as health_routes
from app.api.routes import status as status_routes
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.paths import RawDataViolationError, ensure_generated_dirs, raw_data_dir
from app.schemas.common import ErrorDetail, ErrorResponse

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks: prepare generated dirs, log real context."""
    settings = get_settings()
    setup_logging()
    created = ensure_generated_dirs()
    logger.info(
        "API starting | project=%s v%s | classes=%s | raw_data_readonly=%s",
        settings.project.name,
        settings.project.version,
        settings.class_names,
        raw_data_dir(),
    )
    if created:
        logger.info("created generated directories: %s", [str(p) for p in created])
    yield
    logger.info("API shutting down")


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.project.name} API",
        version=settings.project.version,
        description=(
            "Data-centric closed-loop computer vision platform API. "
            "Metrics are only returned after they have actually been computed."
        ),
        lifespan=lifespan,
    )

    app.include_router(health_routes.router)
    app.include_router(config_routes.router)
    app.include_router(status_routes.router)

    @app.exception_handler(RawDataViolationError)
    async def raw_data_violation_handler(
        request: Request, exc: RawDataViolationError
    ) -> JSONResponse:
        logger.error("raw data violation on %s: %s", request.url.path, exc)
        body = ErrorResponse(error=ErrorDetail(code="RAW_DATA_WRITE_VIOLATION", message=str(exc)))
        return JSONResponse(status_code=403, content=body.model_dump())

    return app


app = create_app()
