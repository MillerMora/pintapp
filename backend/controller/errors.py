"""Traduce los errores de negocio a respuestas HTTP con un formato único:

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.model import errors as e

logger = logging.getLogger(__name__)

_STATUS: dict[type[e.PintappError], int] = {
    e.SessionRequiredError: 401,
    e.SessionExpiredError: 401,
    e.ConsentRequiredError: 403,
    e.GarmentNotFoundError: 404,
    e.VariantNotFoundError: 404,
    e.FittingItemNotFoundError: 404,
    e.JobNotFoundError: 404,
    e.PhotoRequiredError: 409,
    e.GarmentOutOfStockError: 409,
    e.ZoneOccupiedError: 409,
    e.FittingEmptyError: 409,
    e.GenerationInProgressError: 409,
    e.JobNotReadyError: 409,
    e.RetryNotAllowedError: 409,
    e.RetryLimitReachedError: 409,
    e.PhotoTooLargeError: 413,
    e.RequestTooLargeError: 413,
    e.InvalidPhotoError: 422,
    e.UnsupportedCategoryError: 422,
    e.TooManySessionsError: 503,
    e.QueueFullError: 503,
    e.InventoryUnavailableError: 503,
}

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status, content={"error": body})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(e.PintappError)
    async def _domain_error(_: Request, exc: e.PintappError) -> JSONResponse:
        status = next((s for cls, s in _STATUS.items() if isinstance(exc, cls)), 500)
        return error_response(status, exc.code, exc.message, exc.details or None)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # No se devuelve "input" para no reflejar datos enviados por el cliente.
        fields = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return error_response(422, "validation_error", "Hay datos inválidos en la solicitud.", {"fields": fields})

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado", exc_info=exc)
        return error_response(500, "internal_error", "Ocurrió un error interno.")
