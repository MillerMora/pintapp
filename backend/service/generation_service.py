"""Cola y ejecución de las generaciones de imagen.

Flujo: ``submit`` valida y encola -> un worker toma el trabajo -> llama al generador
con un tiempo máximo -> el trabajo termina como completed, failed o timed_out.
La cola vive en el proceso (asyncio); para varios procesos habría que moverla a
Redis/Celery/Arq. Ver README.
"""

import asyncio
import itertools
import logging
import secrets
import time
from collections.abc import Callable

from backend.model.enums import GenerationStatus
from backend.model.errors import (
    ConsentRequiredError,
    FittingEmptyError,
    GenerationFailedError,
    GenerationInProgressError,
    JobNotFoundError,
    JobNotReadyError,
    PhotoRequiredError,
    QueueFullError,
    RetryLimitReachedError,
    RetryNotAllowedError,
)
from backend.model.generation import (
    GeneratedImage,
    GenerationInput,
    GenerationJob,
    JobProgress,
)
from backend.model.session import ClientSession
from backend.port.image_generator import ImageGenerator
from backend.port.stores import JobStore
from backend.service.body_zones import RENDER_ORDER

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({GenerationStatus.QUEUED, GenerationStatus.PROCESSING})
_RETRYABLE = frozenset({GenerationStatus.FAILED, GenerationStatus.TIMED_OUT})
_KEEP_FINISHED_PER_SESSION = 5


class GenerationService:
    def __init__(
        self,
        *,
        jobs: JobStore,
        generator: ImageGenerator,
        workers: int,
        queue_max: int,
        timeout_seconds: float,
        max_retries: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._jobs = jobs
        self._generator = generator
        self._worker_count = workers
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=queue_max)
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._clock = clock
        self._sequence = itertools.count(1)
        self._workers: list[asyncio.Task[None]] = []
        self._running: dict[str, asyncio.Task[None]] = {}

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    @property
    def max_attempts(self) -> int:
        return 1 + self._max_retries

    # ---------- ciclo de vida de los workers ----------
    def start(self) -> None:
        for number in range(self._worker_count):
            self._workers.append(asyncio.create_task(self._worker(), name=f"generation-worker-{number}"))

    async def stop(self) -> None:
        for task in [*self._workers, *self._running.values()]:
            task.cancel()
        await asyncio.gather(*self._workers, *self._running.values(), return_exceptions=True)
        self._workers.clear()
        self._running.clear()

    # ---------- casos de uso ----------
    async def submit(self, session: ClientSession) -> JobProgress:
        if not session.consent_accepted:
            raise ConsentRequiredError()
        if session.photo is None:
            raise PhotoRequiredError()
        if not session.fitting:
            raise FittingEmptyError()
        await self._ensure_no_active_job(session.id)

        items = tuple(session.fitting[zone] for zone in RENDER_ORDER if zone in session.fitting)
        job = self._new_job(session.id, attempt=1, data=GenerationInput(session.photo, items))
        await self._enqueue(job)
        await self._prune_finished(session.id)
        return await self._progress(job)

    async def retry(self, session: ClientSession, job_id: str) -> JobProgress:
        previous = await self._owned_job(session, job_id)
        if previous.status not in _RETRYABLE:
            raise RetryNotAllowedError(status=previous.status.value)
        if previous.attempt >= self.max_attempts:
            raise RetryLimitReachedError(max_attempts=self.max_attempts)
        await self._ensure_no_active_job(session.id)

        job = self._new_job(session.id, attempt=previous.attempt + 1, data=previous.input)
        await self._enqueue(job)
        return await self._progress(job)

    async def progress(self, session: ClientSession, job_id: str) -> JobProgress:
        return await self._progress(await self._owned_job(session, job_id))

    async def image(self, session: ClientSession, job_id: str) -> GeneratedImage:
        job = await self._owned_job(session, job_id)
        if job.status is not GenerationStatus.COMPLETED or job.result is None:
            raise JobNotReadyError(status=job.status.value)
        return job.result

    async def active_job_id(self, session: ClientSession) -> str | None:
        for job in await self._jobs.list_by_session(session.id):
            if job.status in _ACTIVE:
                return job.id
        return None

    async def purge_session(self, session: ClientSession) -> None:
        """Borra los trabajos de la sesión y cancela el que esté en ejecución."""
        for job in await self._jobs.delete_by_session(session.id):
            task = self._running.get(job.id)
            if task is not None:
                task.cancel()

    # ---------- internos ----------
    def _new_job(self, session_id: str, *, attempt: int, data: GenerationInput) -> GenerationJob:
        return GenerationJob(
            id=secrets.token_urlsafe(12),
            session_id=session_id,
            sequence=next(self._sequence),
            attempt=attempt,
            input=data,
            created_at=self._clock(),
        )

    async def _enqueue(self, job: GenerationJob) -> None:
        await self._jobs.add(job)
        try:
            self._queue.put_nowait(job.id)
        except asyncio.QueueFull:
            await self._jobs.delete(job.id)
            raise QueueFullError() from None

    async def _ensure_no_active_job(self, session_id: str) -> None:
        for job in await self._jobs.list_by_session(session_id):
            if job.status in _ACTIVE:
                raise GenerationInProgressError(job_id=job.id)

    async def _owned_job(self, session: ClientSession, job_id: str) -> GenerationJob:
        job = await self._jobs.get(job_id)
        if job is None or job.session_id != session.id:  # no revelar trabajos ajenos
            raise JobNotFoundError()
        return job

    async def _progress(self, job: GenerationJob) -> JobProgress:
        position = None
        if job.status is GenerationStatus.QUEUED:
            position = 1 + await self._jobs.count_queued_before(job.sequence)
        end = job.finished_at if job.finished_at is not None else self._clock()
        return JobProgress(
            job=job,
            queue_position=position,
            elapsed_seconds=max(0.0, end - job.created_at),
            can_retry=job.status in _RETRYABLE and job.attempt < self.max_attempts,
        )

    async def _prune_finished(self, session_id: str) -> None:
        finished = [
            j for j in await self._jobs.list_by_session(session_id) if j.status not in _ACTIVE
        ]
        for job in finished[:-_KEEP_FINISHED_PER_SESSION]:
            await self._jobs.delete(job.id)

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            task = asyncio.create_task(self._execute(job_id))
            self._running[job_id] = task
            try:
                # asyncio.wait no propaga la cancelación del trabajo (cierre de sesión);
                # si se cancela el worker (apagado) sí cancelamos el trabajo.
                await asyncio.wait({task})
            except asyncio.CancelledError:
                task.cancel()
                raise
            finally:
                self._running.pop(job_id, None)
                self._queue.task_done()

    async def _execute(self, job_id: str) -> None:
        job = await self._jobs.get(job_id)
        if job is None or job.status is not GenerationStatus.QUEUED:
            return  # la sesión se cerró mientras esperaba en la cola
        job.status = GenerationStatus.PROCESSING
        job.started_at = self._clock()
        await self._jobs.save(job)

        timeout = asyncio.timeout(self._timeout)
        try:
            async with timeout:
                image = await self._generator.generate(job.input)
        except TimeoutError:
            if timeout.expired():
                self._finish(job, GenerationStatus.TIMED_OUT, "generation_timeout",
                             "La generación tardó demasiado.")
            else:
                logger.exception("Tiempo agotado interno del generador (trabajo %s)", job.id)
                self._finish(job, GenerationStatus.FAILED, "generation_failed",
                             "No se pudo generar la imagen.")
        except GenerationFailedError as exc:
            logger.warning("Generación fallida (trabajo %s): %s", job.id, exc.message)
            self._finish(job, GenerationStatus.FAILED, exc.code, "No se pudo generar la imagen.")
        except Exception:
            logger.exception("Error inesperado generando la imagen (trabajo %s)", job.id)
            self._finish(job, GenerationStatus.FAILED, "generation_failed",
                         "No se pudo generar la imagen.")
        else:
            job.result = image
            self._finish(job, GenerationStatus.COMPLETED)
        # Si la sesión se cerró mientras se generaba, no se guarda nada.
        if await self._jobs.get(job.id) is not None:
            await self._jobs.save(job)

    def _finish(
        self,
        job: GenerationJob,
        status: GenerationStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        job.status = status
        job.finished_at = self._clock()
        job.error_code = error_code
        job.error_message = error_message
