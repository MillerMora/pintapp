"""Dependencias de FastAPI: acceso al contenedor y autenticación por token de sesión."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from backend.container import Container
from backend.controller.schemas import ErrorResponse
from backend.model.session import ClientSession

_token_header = APIKeyHeader(
    name="X-Session-Token",
    scheme_name="SessionToken",
    auto_error=False,  # el error lo genera el servicio con el formato común
    description="Token devuelto por POST /api/v1/sessions",
)


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


async def current_session(
    container: ContainerDep, token: Annotated[str | None, Depends(_token_header)]
) -> ClientSession:
    return await container.sessions.authenticate(token)


CurrentSession = Annotated[ClientSession, Depends(current_session)]

# Respuestas de error documentadas en /docs
ERR = {"model": ErrorResponse}
SESSION_ERRORS = {401: ERR}
