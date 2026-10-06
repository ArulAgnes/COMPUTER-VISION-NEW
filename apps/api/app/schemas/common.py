"""Shared error response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Machine-readable error information."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard failure envelope returned by every failing endpoint."""

    success: bool = False
    error: ErrorDetail
