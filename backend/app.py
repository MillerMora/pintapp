"""Fábrica de la aplicación FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend import __version__
from backend.config import Settings
from backend.container import Container
from backend.controller import catalog, fitting, generations, health, sessions
from backend.controller.errors import error_response, register_error_handlers
from backend.model.errors import RequestTooLargeError
from backend.port.image_generator import ImageGenerator
from backend.port.inventory import InventoryRepository

_ENVELOPE_BYTES = 64 * 1024  # margen sobre la foto para cabeceras y cuerpos JSON


class BodySizeLimitMiddleware:
    """Rechaza cuerpos enormes (por Content-Length o contando bytes al vuelo)."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            response = error_response(413, RequestTooLargeError.code, RequestTooLargeError.default_message)
            await response(scope, receive, send)
            return

        received = 0
        too_large = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            if too_large:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # Se le avisa a la app que "se cortó la conexión" para que deje de leer;
                    # la respuesta 413 la envía este middleware (la app solo vería un 400).
                    too_large = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not too_large:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not too_large:
                raise
        if too_large:
            response = error_response(413, RequestTooLargeError.code, RequestTooLargeError.default_message)
            await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """Las respuestas contienen fotos de personas: nunca deben quedar en cachés."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app(
    settings: Settings | None = None,
    *,
    inventory: InventoryRepository | None = None,
    generator: ImageGenerator | None = None,
) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    container = Container(settings, inventory=inventory, generator=generator)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await container.start()
        try:
            yield
        finally:
            await container.stop()

    app = FastAPI(
        title="PintApp - Backend",
        version=__version__,
        description="API del probador virtual de ropa. Fase 1: inventario e IA simulados.",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.container = container
    register_error_handlers(app)

    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.photo_max_bytes + _ENVELOPE_BYTES)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["X-Session-Token", "Content-Type"],
        )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(catalog.router)
    app.include_router(fitting.router)
    app.include_router(generations.router)
    return app
