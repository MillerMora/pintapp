"""Contratos JSON de la API (lo que ve el frontend)."""

from typing import Any

from pydantic import BaseModel, Field

from backend.model.catalog import Category, Garment
from backend.model.generation import JobProgress
from backend.model.session import FittingItem


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---- Sistema ----
class HealthOut(BaseModel):
    status: str
    version: str
    database: str  # not_configured | ok | unavailable


# ---- Sesión ----
class TermsOut(BaseModel):
    version: str
    text: str


class SessionCreatedOut(BaseModel):
    token: str = Field(description="Credencial secreta: enviar en el encabezado X-Session-Token")
    expires_in_seconds: int
    terms: TermsOut


class SessionStatusOut(BaseModel):
    expires_in_seconds: int
    consent_accepted: bool
    has_photo: bool
    fitting_count: int
    active_job_id: str | None


class ConsentIn(BaseModel):
    accepted: bool


class PhotoOut(BaseModel):
    width: int
    height: int
    size_bytes: int


# ---- Catálogo ----
class VariantOut(BaseModel):
    sku: str
    size: str
    in_stock: bool


class GarmentOut(BaseModel):
    id: str
    name: str
    category: str
    color: str
    color_hex: str
    image_url: str | None
    in_stock: bool = Field(description="True si al menos una talla tiene existencias")
    variants: list[VariantOut]

    @classmethod
    def from_domain(cls, garment: Garment) -> "GarmentOut":
        return cls(
            id=garment.id,
            name=garment.name,
            category=garment.category,
            color=garment.color,
            color_hex=garment.color_hex,
            image_url=garment.image_url,
            in_stock=garment.in_stock,
            variants=[VariantOut(sku=v.sku, size=v.size, in_stock=v.in_stock) for v in garment.variants],
        )


class GarmentListOut(BaseModel):
    items: list[GarmentOut]
    total: int
    limit: int
    offset: int


class CategoryOut(BaseModel):
    name: str
    garment_count: int

    @classmethod
    def from_domain(cls, category: Category) -> "CategoryOut":
        return cls(name=category.name, garment_count=category.garment_count)


# ---- Probador ----
class FittingAddIn(BaseModel):
    garment_id: str = Field(min_length=1, max_length=64)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    replace: bool = Field(default=False, description="Reemplazar la prenda que ya ocupa esa zona")


class FittingItemOut(BaseModel):
    garment_id: str
    name: str
    category: str
    zone: str
    sku: str | None
    size: str | None

    @classmethod
    def from_domain(cls, item: FittingItem) -> "FittingItemOut":
        return cls(
            garment_id=item.garment.id,
            name=item.garment.name,
            category=item.garment.category,
            zone=item.zone.value,
            sku=item.variant.sku if item.variant else None,
            size=item.variant.size if item.variant else None,
        )


class FittingListOut(BaseModel):
    items: list[FittingItemOut]


# ---- Generación ----
class JobErrorOut(BaseModel):
    code: str
    message: str


class GenerationOut(BaseModel):
    job_id: str
    status: str = Field(description="queued | processing | completed | failed | timed_out")
    attempt: int
    max_attempts: int
    queue_position: int | None = Field(description="1 = el siguiente; solo mientras está en cola")
    elapsed_seconds: float = Field(description="Segundos desde que se pidió la imagen")
    timeout_seconds: float = Field(description="Tiempo máximo de procesamiento")
    can_retry: bool
    error: JobErrorOut | None

    @classmethod
    def from_progress(
        cls, progress: JobProgress, *, max_attempts: int, timeout_seconds: float
    ) -> "GenerationOut":
        job = progress.job
        error = (
            JobErrorOut(code=job.error_code, message=job.error_message or "")
            if job.error_code
            else None
        )
        return cls(
            job_id=job.id,
            status=job.status.value,
            attempt=job.attempt,
            max_attempts=max_attempts,
            queue_position=progress.queue_position,
            elapsed_seconds=round(progress.elapsed_seconds, 1),
            timeout_seconds=timeout_seconds,
            can_retry=progress.can_retry,
            error=error,
        )
