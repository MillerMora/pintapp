from enum import StrEnum


class BodyZone(StrEnum):
    """Zona del cuerpo sobre la que va una prenda (una prenda por zona)."""

    HEAD = "head"
    UPPER_INNER = "upper_inner"  # camisas, camisetas, buzos
    UPPER_OUTER = "upper_outer"  # chaquetas, abrigos
    LOWER = "lower"  # pantalones, shorts, faldas
    FEET = "feet"  # zapatos, tenis, botas


class GenerationStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
