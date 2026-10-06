"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()

SERVICE_NAME = "computer-vision-api"


@router.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Real service status derived from the loaded configuration."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=settings.project.version,
        classes=settings.class_names,
    )
