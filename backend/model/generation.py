from dataclasses import dataclass

from backend.model.enums import GenerationStatus
from backend.model.session import FittingItem, ProcessedPhoto


@dataclass(frozen=True, slots=True)
class GenerationInput:
    """Foto de entrada y prendas (ya ordenadas por capa de dibujo)."""

    photo: ProcessedPhoto
    items: tuple[FittingItem, ...]


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    data: bytes
    media_type: str


@dataclass(slots=True)
class GenerationJob:
    id: str
    session_id: str
    sequence: int  # orden de llegada a la cola
    attempt: int
    input: GenerationInput
    created_at: float
    status: GenerationStatus = GenerationStatus.QUEUED
    started_at: float | None = None
    finished_at: float | None = None
    result: GeneratedImage | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class JobProgress:
    """Vista de un trabajo para el cliente: lo que se puede saber con honestidad."""

    job: GenerationJob
    queue_position: int | None  # 1 = el siguiente en procesarse; None si ya no está en cola
    elapsed_seconds: float
    can_retry: bool
