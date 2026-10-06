"""Health endpoint schema."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Real application status — no metrics are invented here."""

    status: str
    service: str
    version: str
    classes: list[str]
