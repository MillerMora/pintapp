from fastapi import APIRouter, Request, Response

from backend.controller.deps import ERR, SESSION_ERRORS, ContainerDep, CurrentSession
from backend.controller.schemas import (
    ConsentIn,
    PhotoOut,
    SessionCreatedOut,
    SessionStatusOut,
    TermsOut,
)
from backend.model.errors import PhotoTooLargeError

router = APIRouter(prefix="/api/v1", tags=["Sesión del cliente"])

_PHOTO_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            mime: {"schema": {"type": "string", "format": "binary"}}
            for mime in ("image/jpeg", "image/png", "image/webp")
        },
    }
}


@router.get("/terms", response_model=TermsOut)
async def get_terms(container: ContainerDep):
    """Aviso de términos y condiciones de uso de la imagen."""
    return TermsOut(version=container.settings.terms_version, text=container.settings.terms_text)


@router.post("/sessions", response_model=SessionCreatedOut, status_code=201, responses={503: ERR})
async def create_session(container: ContainerDep):
    """El cliente toca la pantalla: crea una sesión temporal y entrega el aviso de términos."""
    session = await container.sessions.create()
    return SessionCreatedOut(
        token=session.token,
        expires_in_seconds=container.sessions.remaining_seconds(session),
        terms=TermsOut(version=container.settings.terms_version, text=container.settings.terms_text),
    )


@router.get("/sessions/me", response_model=SessionStatusOut, responses=SESSION_ERRORS)
async def session_status(session: CurrentSession, container: ContainerDep):
    """Estado de la sesión (útil para que el frontend se resincronice)."""
    return SessionStatusOut(
        expires_in_seconds=container.sessions.remaining_seconds(session),
        consent_accepted=session.consent_accepted,
        has_photo=session.photo is not None,
        fitting_count=len(session.fitting),
        active_job_id=await container.generation.active_job_id(session),
    )


@router.put(
    "/sessions/me/consent",
    response_model=SessionStatusOut,
    responses={204: {"description": "El cliente no aceptó: la sesión se cerró sin guardar nada"}, **SESSION_ERRORS},
)
async def answer_consent(body: ConsentIn, session: CurrentSession, container: ContainerDep):
    """Respuesta del cliente al aviso. Si no acepta, se cierra la sesión sin guardar nada."""
    if not body.accepted:
        await container.sessions.close(session)
        return Response(status_code=204)
    await container.sessions.accept_consent(session)
    return await session_status(session, container)


@router.put(
    "/sessions/me/photo",
    response_model=PhotoOut,
    openapi_extra=_PHOTO_BODY,
    responses={403: ERR, 413: ERR, 422: ERR, **SESSION_ERRORS},
)
async def upload_photo(request: Request, session: CurrentSession, container: ContainerDep):
    """Recibe la foto como cuerpo crudo (JPEG, PNG o WebP). Reemplaza la anterior.

    Si la foto no es válida responde 422 con ``details.reason`` y el cliente puede
    volver a tomarla sin perder la sesión.
    """
    container.sessions.require_consent(session)  # no se lee el cuerpo si no hay consentimiento
    limit = container.settings.photo_max_bytes
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise PhotoTooLargeError(max_bytes=limit)
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > limit:
            raise PhotoTooLargeError(max_bytes=limit)
        chunks.append(chunk)

    photo = await container.photos.process(b"".join(chunks))
    await container.sessions.set_photo(session, photo)
    return PhotoOut(width=photo.width, height=photo.height, size_bytes=len(photo.data))


@router.delete("/sessions/me", status_code=204, responses=SESSION_ERRORS)
async def end_session(session: CurrentSession, container: ContainerDep):
    """Termina la sesión y borra la foto, las prendas y las imágenes generadas."""
    await container.sessions.close(session)
    return Response(status_code=204)
