"""Map typed service exceptions to stable HTTP responses."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..core.exceptions import (
    AuthorizationError,
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
    ZyPlatError,
)

_STATUS_BY_TYPE: dict[type[ZyPlatError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
    AuthorizationError: 403,
    InfrastructureError: 500,
}


def _request_id(request: Request) -> str:
    header = request.headers.get("x-request-id")
    if header:
        return header
    return str(uuid.uuid4())


def _error_body(exc: ZyPlatError, request_id: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
        "request_id": request_id,
    }
    if exc.details:
        body["details"] = exc.details
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach ZyPlat exception handlers to ``app``."""

    @app.exception_handler(ZyPlatError)
    async def handle_zyplat_error(request: Request, exc: ZyPlatError) -> JSONResponse:
        status = _STATUS_BY_TYPE.get(type(exc), 500)
        request_id = _request_id(request)
        return JSONResponse(status_code=status, content=_error_body(exc, request_id))
