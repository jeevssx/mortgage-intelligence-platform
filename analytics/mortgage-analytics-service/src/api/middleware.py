"""Correlation ID middleware and the standard error envelope handlers."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.utils.errors import AppError
from src.utils.logging_config import correlation_id_var, get_correlation_id
from src.utils.time import utc_now_iso

logger = logging.getLogger("src.api.access")

CORRELATION_HEADER = "X-Correlation-Id"
# Accept caller-supplied IDs only if they are short and log-safe; otherwise mint a UUID.
_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER, "")
        correlation_id = incoming if _SAFE_CORRELATION_ID.match(incoming) else str(uuid.uuid4())
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error", extra={"method": request.method, "path": request.url.path})
            response = error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers[CORRELATION_HEADER] = correlation_id
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "durationMs": duration_ms,
            },
        )
        correlation_id_var.reset(token)
        return response


def error_response(status: int, code: str, message: str, details: object = None) -> JSONResponse:
    body: dict[str, object] = {
        "code": code,
        "message": message,
        "correlationId": get_correlation_id(),
        "timestamp": utc_now_iso(),
    }
    if details:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        level = logging.ERROR if exc.status_code >= 500 else logging.INFO
        logger.log(level, "Request failed", extra={"code": exc.code, "status": exc.status_code})
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", ())), "error": err.get("msg", "")}
            for err in exc.errors()
        ]
        return error_response(400, "VALIDATION_ERROR", "Request validation failed", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
