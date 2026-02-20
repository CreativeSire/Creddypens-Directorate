from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        error_id = str(uuid.uuid4())
        logger.exception("Unhandled error id=%s path=%s", error_id, request.url.path, exc_info=exc)
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error. Reference this error_id with support.",
                "error_id": error_id,
            },
        )

