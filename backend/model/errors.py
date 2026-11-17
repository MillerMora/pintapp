"""Errores de negocio. Cada uno tiene un ``code`` estable que el frontend puede usar.

El dominio no conoce HTTP: la traducción a códigos de estado vive en
``controller/errors.py``.
"""


class PintappError(Exception):
    code: str = "internal_error"
    default_message: str = "Ocurrió un error inesperado."

    def __init__(self, message: str | None = None, **details: object) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


# --- Sesión ---
class SessionRequiredError(PintappError):
    code = "session_required"
    default_message = "Falta el encabezado X-Session-Token."


class SessionExpiredError(PintappError):
    code = "session_invalid"
    default_message = "La sesión no existe o ya expiró."


class TooManySessionsError(PintappError):
    code = "too_many_sessions"
    default_message = "Hay demasiadas sesiones activas. Intenta de nuevo en un momento."


class ConsentRequiredError(PintappError):
    code = "consent_required"
    default_message = "Primero debes aceptar los términos de uso de la imagen."


# --- Foto ---
class PhotoRequiredError(PintappError):
    code = "photo_required"
    default_message = "Primero debes tomar una foto válida."


class PhotoTooLargeError(PintappError):
    code = "photo_too_large"
    default_message = "La foto pesa demasiado."


class InvalidPhotoError(PintappError):
    code = "invalid_photo"
    default_message = "La foto no es válida. Vuelve a tomarla."


class RequestTooLargeError(PintappError):
    code = "request_too_large"
    default_message = "La solicitud es demasiado grande."


# --- Catálogo y probador ---
class GarmentNotFoundError(PintappError):
    code = "garment_not_found"
    default_message = "La prenda no existe."


class VariantNotFoundError(PintappError):
    code = "variant_not_found"
    default_message = "Esa talla no existe para la prenda."


class GarmentOutOfStockError(PintappError):
    code = "garment_out_of_stock"
    default_message = "La prenda no tiene existencias."


class UnsupportedCategoryError(PintappError):
    code = "unsupported_category"
    default_message = "No se puede probar esta categoría de prenda."


class ZoneOccupiedError(PintappError):
    code = "zone_occupied"
    default_message = "Ya hay una prenda en esa zona del cuerpo."


class FittingItemNotFoundError(PintappError):
    code = "fitting_item_not_found"
    default_message = "Esa prenda no está en el probador."


class FittingEmptyError(PintappError):
    code = "fitting_empty"
    default_message = "Agrega al menos una prenda al probador."


class InventoryUnavailableError(PintappError):
    """Para los adaptadores reales: el inventario (BD o e-commerce) no responde."""

    code = "inventory_unavailable"
    default_message = "El inventario no está disponible en este momento."


# --- Generación ---
class GenerationInProgressError(PintappError):
    code = "generation_in_progress"
    default_message = "Ya hay una imagen en proceso para esta sesión."


class QueueFullError(PintappError):
    code = "queue_full"
    default_message = "El sistema está ocupado. Intenta de nuevo en unos segundos."


class JobNotFoundError(PintappError):
    code = "job_not_found"
    default_message = "No existe esa generación."


class JobNotReadyError(PintappError):
    code = "job_not_ready"
    default_message = "La imagen todavía no está lista."


class RetryNotAllowedError(PintappError):
    code = "retry_not_allowed"
    default_message = "Solo se puede reintentar una generación fallida."


class RetryLimitReachedError(PintappError):
    code = "retry_limit_reached"
    default_message = "Se alcanzó el máximo de reintentos."


class GenerationFailedError(PintappError):
    """La lanzan los generadores cuando no logran producir la imagen."""

    code = "generation_failed"
    default_message = "No se pudo generar la imagen."
