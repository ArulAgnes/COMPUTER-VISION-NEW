"""Dashboard status endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.status import StatusResponse
from app.services.status_service import get_status

router = APIRouter()


@router.get("/api/status", response_model=StatusResponse, tags=["status"])
def get_status_endpoint() -> StatusResponse:
    """Real platform status; unavailable values are returned as null."""
    return get_status()
