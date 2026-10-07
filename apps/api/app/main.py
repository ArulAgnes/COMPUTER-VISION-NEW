"""FastAPI application factory.

Run from the repository root:

    uvicorn app.main:app --reload --app-dir apps/api
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import config as config_routes
from app.api.routes import dataset as dataset_routes
from app.api.routes import health as health_routes
from app.api.routes import status as status_routes
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.paths import RawDataViolationError, ensure_generated_dirs, raw_data_dir
from app.schemas.common import ErrorDetail, ErrorResponse
from app.services.dataset_service import ImageNotFoundError, InvalidQueryError, NotScannedError

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

    # Local frontend origins from configs/project.yaml (api.cors_origins).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(config_routes.router)
    app.include_router(status_routes.router)
    app.include_router(dataset_routes.router)

    @app.exception_handler(RawDataViolationError)
    async def raw_data_violation_handler(
        request: Request, exc: RawDataViolationError
    ) -> JSONResponse:
        logger.error("raw data violation on %s: %s", request.url.path, exc)
        body = ErrorResponse(error=ErrorDetail(code="RAW_DATA_WRITE_VIOLATION", message=str(exc)))
        return JSONResponse(status_code=403, content=body.model_dump())

    @app.exception_handler(NotScannedError)
    async def not_scanned_handler(request: Request, exc: NotScannedError) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="DATASET_NOT_SCANNED", message=str(exc)))
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(ImageNotFoundError)
    async def image_not_found_handler(request: Request, exc: ImageNotFoundError) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="IMAGE_NOT_FOUND", message=str(exc)))
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(InvalidQueryError)
    async def invalid_query_handler(request: Request, exc: InvalidQueryError) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="INVALID_PARAMETER", message=str(exc)))
        return JSONResponse(status_code=400, content=body.model_dump())

    return app


app = create_app()
