from fastapi import APIRouter, Response

from backend.controller.deps import ERR, SESSION_ERRORS, ContainerDep, CurrentSession
from backend.controller.schemas import GenerationOut
from backend.model.generation import JobProgress

router = APIRouter(
    prefix="/api/v1/sessions/me/generations",
    tags=["Generación de imagen"],
    responses=SESSION_ERRORS,
)


def _out(container, progress: JobProgress) -> GenerationOut:
    return GenerationOut.from_progress(
        progress,
        max_attempts=container.generation.max_attempts,
        timeout_seconds=container.generation.timeout_seconds,
    )


@router.post("", response_model=GenerationOut, status_code=202, responses={403: ERR, 409: ERR, 503: ERR})
async def finalize(session: CurrentSession, container: ContainerDep):
    """El cliente presiona "finalizar": identifica las zonas y encola la generación."""
    return _out(container, await container.generation.submit(session))


@router.get("/{job_id}", response_model=GenerationOut, responses={404: ERR})
async def get_generation(job_id: str, session: CurrentSession, container: ContainerDep):
    """Estado de la generación. El frontend consulta esto cada 1-2 segundos.

    El progreso es por estados (en cola, procesando, listo, fallido...), no un
    porcentaje real: los generadores de imágenes no lo informan.
    """
    return _out(container, await container.generation.progress(session, job_id))


@router.get(
    "/{job_id}/image",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}, 404: ERR, 409: ERR},
)
async def get_generation_image(job_id: str, session: CurrentSession, container: ContainerDep):
    """Imagen resultante (solo cuando el estado es completed)."""
    image = await container.generation.image(session, job_id)
    return Response(content=image.data, media_type=image.media_type)


@router.post(
    "/{job_id}/retry",
    response_model=GenerationOut,
    status_code=202,
    responses={404: ERR, 409: ERR, 503: ERR},
)
async def retry_generation(job_id: str, session: CurrentSession, container: ContainerDep):
    """Reintenta una generación fallida o que superó el tiempo máximo."""
    return _out(container, await container.generation.retry(session, job_id))
